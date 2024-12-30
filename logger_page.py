import os
import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
import datetime

class LogViewerPage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.log_folder = "logs"  # Adjust this path as needed
        
        # Create GUI elements
        self.create_widgets()
        
    def create_widgets(self):
        # Create top frame for controls
        control_frame = ttk.Frame(self)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Add refresh button
        refresh_btn = ttk.Button(control_frame, text="Refresh Logs", command=self.refresh_logs)
        refresh_btn.pack(side=tk.LEFT, padx=5)
        
        # Add log file selector
        self.log_selector = ttk.Combobox(control_frame, state="readonly")
        self.log_selector.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.log_selector.bind('<<ComboboxSelected>>', self.on_log_selected)
        
        # Add text area for log content
        self.log_text = scrolledtext.ScrolledText(self, wrap=tk.WORD, height=30)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Initial load of logs
        self.refresh_logs()
        
    def refresh_logs(self):
        """Refresh the list of available log files"""
        self.log_files = []
        if os.path.exists(self.log_folder):
            self.log_files = [f for f in os.listdir(self.log_folder) 
                            if f.endswith('.log')]
            self.log_files.sort(reverse=True)
            
        self.log_selector['values'] = self.log_files
        if self.log_files:
            self.log_selector.set(self.log_files[0])
            self.display_log(self.log_files[0])
            
    def on_log_selected(self, event):
        """Handle log file selection"""
        selected_log = self.log_selector.get()
        self.display_log(selected_log)
        
    def display_log(self, log_filename):
        """Display the contents of the selected log file"""
        self.log_text.delete(1.0, tk.END)
        if log_filename:
            try:
                with open(os.path.join(self.log_folder, log_filename), 'r') as f:
                    content = f.read()
                    self.log_text.insert(tk.END, content)
                self.log_text.see(tk.END)  # Scroll to bottom
            except Exception as e:
                self.log_text.insert(tk.END, f"Error reading log file: {str(e)}")

if __name__ == "__main__":
    # Test the log viewer
    root = tk.Tk()
    root.title("Log Viewer")
    app = LogViewerPage(root)
    app.pack(fill=tk.BOTH, expand=True)
    root.geometry("800x600")
    root.mainloop()