import streamlit as st
import os
from datetime import datetime
import glob


def get_log_files():
    """Get all .log files from the logs directory"""
    log_dir = "./logs"
    if not os.path.exists(log_dir):
        return []
    return sorted(
        glob.glob(os.path.join(log_dir, "*.log")), key=os.path.getmtime, reverse=True
    )


def read_log_file(file_path):
    """Read and parse log file content"""
    try:
        with open(file_path, "r") as f:
            return f.readlines()
    except Exception as e:
        st.error(f"Error reading log file: {str(e)}")
        return []


def parse_log_line(line):
    """Parse a log line into its components"""
    try:
        # Expected format: "YYYY-MM-DD HH:MM:SS - name - LEVEL - message"
        parts = line.strip().split(" - ", 3)
        if len(parts) == 4:
            timestamp, name, level, message = parts
            return {
                "timestamp": datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S"),
                "name": name,
                "level": level,
                "message": message,
            }
        return None
    except Exception:
        return None


def main():
    st.title("Log Viewer")

    # Get list of log files
    log_files = get_log_files()

    if not log_files:
        st.warning("No log files found in the logs directory")
        return

    if selected_file := st.selectbox(
        "Select log file",
        options=log_files,
        format_func=lambda x: os.path.basename(x),
    ):
        _extracted_from_main_16(selected_file)


# TODO Rename this here and in `main`
def _extracted_from_main_16(selected_file):
    file_info = os.stat(selected_file)
    st.info(
        f"""
        File: {os.path.basename(selected_file)}
        Size: {file_info.st_size/1024:.2f} KB
        Last modified: {datetime.fromtimestamp(file_info.st_mtime)}
        """
    )

    # Log level filter
    log_levels = ["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    selected_level = st.selectbox("Filter by log level", log_levels)

    # Search box
    search_term = st.text_input("Search logs", "")

    # Read log content
    log_lines = read_log_file(selected_file)

    # Create a container for log display
    log_container = st.container()

    with log_container:
        for line in log_lines:
            if log_entry := parse_log_line(line):
                # Apply filters
                level_match = (
                    selected_level == "ALL" or log_entry["level"] == selected_level
                )
                search_match = not search_term or search_term.lower() in line.lower()

                if level_match and search_match:
                    # Color coding based on log level
                    color = {
                        "DEBUG": "gray",
                        "INFO": "blue",
                        "WARNING": "orange",
                        "ERROR": "red",
                        "CRITICAL": "purple",
                    }.get(log_entry["level"], "black")

                    st.markdown(
                        f"""
                            <div style='color:{color}; font-family:monospace;'>
                            {line}
                            </div>
                            """,
                        unsafe_allow_html=True,
                    )
            elif not search_term or search_term.lower() in line.lower():
                st.markdown(
                    f"""
                            <div style='color:gray; font-family:monospace;'>
                            {line}
                            </div>
                            """,
                    unsafe_allow_html=True,
                )

    # Add download button
    st.download_button(
        "Download log file",
        "\n".join(log_lines),
        file_name=os.path.basename(selected_file),
        mime="text/plain",
    )


main()
