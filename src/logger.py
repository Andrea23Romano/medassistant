import logging
from logging.handlers import RotatingFileHandler
import os
import sys
from datetime import datetime


class ConfigurableLogger:
    """
    Configurable logger with support for file and console logging
    """

    def __init__(
        self, name: str = "health_agent", log_dir: str = "logs", log_level: str = "INFO"
    ):
        """
        Initialize a configurable logger with file and console logging

        :param name: Logger name
        :param log_dir: Directory for log files
        :param log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        # Create log directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)

        # Set up logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        self.logger.propagate = False

        # Check if handlers already exist
        if not self.logger.handlers:
            # Log formatting
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

            # Console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

            # Rotating file handler
            log_file_path = os.path.join(
                log_dir, f'{name}_{datetime.now().strftime("%Y%m%d")}.log'
            )
            file_handler = RotatingFileHandler(
                log_file_path,
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=5,  # Keep 5 old log files
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def debug(self, message: str, *args, **kwargs):
        """Log a debug message"""
        self.logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs):
        """Log an info message"""
        self.logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        """Log a warning message"""
        self.logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        """Log an error message"""
        self.logger.error(message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs):
        """Log a critical message"""
        self.logger.critical(message, *args, **kwargs)

    def exception(self, message: str, *args, **kwargs):
        """Log an exception with traceback"""
        self.logger.exception(message, *args, **kwargs)


def get_logger(
    name: str = "health_agent", log_level: str = "INFO"
) -> ConfigurableLogger:
    """
    Utility function to get a configured logger

    :param name: Logger name
    :param log_level: Logging level
    :return: ConfigurableLogger instance
    """
    return ConfigurableLogger(name=name, log_level=log_level)
