"""
Logging Utility Module

This file sets up logging for the entire application.
Logging helps us track what the application is doing and debug issues.

Why this file exists:
- Creates consistent log format across the application
- Saves logs to file for later review
- Shows logs in console during development
- Makes debugging much easier

How to use in other files:
    from utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("This is an info message")
    logger.error("This is an error message")
"""

import logging
import sys
from pathlib import Path
from config import config


def setup_logger() -> logging.Logger:
    """
    Configure and return the application logger.

    This creates a logger that:
    - Writes to a file (for production/debugging)
    - Writes to console (for development)
    - Includes timestamps, log levels, and module names

    Returns:
        Configured logger instance
    """
    # Ensure log directory exists
    config.ensure_directories()

    # Create logger
    logger = logging.getLogger("ai_news_agent")
    logger.setLevel(getattr(logging, config.LOG_LEVEL))

    # Prevent duplicate handlers if logger already configured
    if logger.handlers:
        return logger

    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # File handler (writes to log file)
    file_handler = logging.FileHandler(config.LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)

    # Console handler (writes to terminal)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(detailed_formatter)
    logger.addHandler(console_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Usually __name__ from the calling module

    Returns:
        Logger instance for that module

    Example:
        logger = get_logger(__name__)
    """
    return logging.getLogger(f"ai_news_agent.{name}")


# Initialize the main logger when this module is imported
main_logger = setup_logger()
