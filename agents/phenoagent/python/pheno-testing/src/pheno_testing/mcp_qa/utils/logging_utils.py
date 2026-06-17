"""Unified Logging Utilities for MCP Projects.

Provides consistent logging setup and utilities across all MCP projects.
Consolidates logging_setup patterns from atoms and zen.

Usage:
    from pheno.testing.mcp_qa.utils.logging_utils import get_logger, configure_logging

    logger = get_logger(__name__)
    logger.info("Starting application")
"""

import logging
import sys
from pathlib import Path
from typing import Optional

# Global logging configuration
_LOGGING_CONFIGURED = False
_DEFAULT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(
    level: int = logging.INFO,
    format_string: Optional[str] = None,
    date_format: Optional[str] = None,
    log_file: Optional[Path] = None,
    quiet_libraries: bool = True,
):
    """Configure logging for the application.

    Args:
        level: Logging level (default: INFO)
        format_string: Custom format string (default: standardized format)
        date_format: Custom date format (default: YYYY-MM-DD HH:MM:SS)
        log_file: Optional file to log to
        quiet_libraries: Suppress noisy third-party library logs
    """
    global _LOGGING_CONFIGURED

    if _LOGGING_CONFIGURED:
        return  # Already configured

    # Use defaults if not provided
    format_string = format_string or _DEFAULT_FORMAT
    date_format = date_format or _DEFAULT_DATE_FORMAT

    # Configure root logger
    logging.basicConfig(
        level=level,
        format=format_string,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            *([logging.FileHandler(log_file)] if log_file else []),
        ],
    )

    # Quiet noisy libraries
    if quiet_libraries:
        quiet_library_loggers(
            [
                "httpx",
                "httpcore",
                "urllib3",
                "requests",
                "fastmcp",
                "mcp",
                "playwright",
                "asyncio",
                "concurrent",
            ]
        )

    _LOGGING_CONFIGURED = True


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """Get a logger instance with consistent configuration.

    Args:
        name: Logger name (typically __name__)
        level: Optional custom level for this logger

    Returns:
        Configured logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("Application started")
    """
    # Ensure logging is configured
    if not _LOGGING_CONFIGURED:
        configure_logging()

    logger = logging.getLogger(name)

    if level is not None:
        logger.setLevel(level)

    return logger


def quiet_library_loggers(libraries: list[str], level: int = logging.WARNING):
    """Suppress logging from noisy libraries.

    Args:
        libraries: List of library names to quiet
        level: Level to set (default: WARNING)
    """
    for library in libraries:
        logging.getLogger(library).setLevel(level)


def set_verbose_mode(enabled: bool = True):
    """Enable or disable verbose logging (DEBUG level).

    Args:
        enabled: True to enable verbose mode, False to disable
    """
    level = logging.DEBUG if enabled else logging.INFO
    logging.getLogger().setLevel(level)


def create_file_handler(
    log_file: Path,
    level: int = logging.INFO,
    format_string: Optional[str] = None,
) -> logging.FileHandler:
    """Create a file handler for logging.

    Args:
        log_file: Path to log file
        level: Logging level for this handler
        format_string: Custom format (default: standardized format)

    Returns:
        Configured FileHandler
    """
    handler = logging.FileHandler(log_file)
    handler.setLevel(level)

    format_string = format_string or _DEFAULT_FORMAT
    formatter = logging.Formatter(format_string, datefmt=_DEFAULT_DATE_FORMAT)
    handler.setFormatter(formatter)

    return handler


def add_file_logging(log_file: Path, level: int = logging.INFO):
    """Add file logging to the root logger.

    Args:
        log_file: Path to log file
        level: Logging level for file output
    """
    handler = create_file_handler(log_file, level)
    logging.getLogger().addHandler(handler)


def log_exception(logger: logging.Logger, message: str, exc_info: bool = True):
    """Log an exception with consistent formatting.

    Args:
        logger: Logger instance
        message: Error message
        exc_info: Include exception traceback (default: True)
    """
    logger.error(message, exc_info=exc_info)


class LoggerContext:
    """Context manager for temporary logger configuration.

    Example:
        with LoggerContext("mymodule", logging.DEBUG):
            # Code here logs at DEBUG level
            pass
        # Back to original level
    """

    def __init__(self, logger_name: str, level: int):
        """Initialize context manager.

        Args:
            logger_name: Name of logger to modify
            level: Temporary log level
        """
        self.logger = logging.getLogger(logger_name)
        self.original_level = self.logger.level
        self.temp_level = level

    def __enter__(self):
        """Enter context - set temporary level."""
        self.logger.setLevel(self.temp_level)
        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - restore original level."""
        self.logger.setLevel(self.original_level)


class QuietLogger:
    """Context manager to temporarily suppress logging.

    Example:
        with QuietLogger():
            # No logs will be shown here
            noisy_function()
    """

    def __init__(self, logger_names: Optional[list[str]] = None):
        """Initialize context manager.

        Args:
            logger_names: Specific loggers to quiet (None = all)
        """
        self.logger_names = logger_names
        self.original_levels = {}

    def __enter__(self):
        """Enter context - suppress logging."""
        if self.logger_names:
            for name in self.logger_names:
                logger = logging.getLogger(name)
                self.original_levels[name] = logger.level
                logger.setLevel(logging.CRITICAL)
        else:
            # Suppress root logger
            root = logging.getLogger()
            self.original_levels["root"] = root.level
            root.setLevel(logging.CRITICAL)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - restore logging."""
        for name, level in self.original_levels.items():
            if name == "root":
                logging.getLogger().setLevel(level)
            else:
                logging.getLogger(name).setLevel(level)


# Convenience functions for common patterns


def debug(message: str, logger_name: str = "root"):
    """
    Log debug message.
    """
    logging.getLogger(logger_name).debug(message)


def info(message: str, logger_name: str = "root"):
    """
    Log info message.
    """
    logging.getLogger(logger_name).info(message)


def warning(message: str, logger_name: str = "root"):
    """
    Log warning message.
    """
    logging.getLogger(logger_name).warning(message)


def error(message: str, logger_name: str = "root", exc_info: bool = False):
    """
    Log error message.
    """
    logging.getLogger(logger_name).error(message, exc_info=exc_info)


def critical(message: str, logger_name: str = "root"):
    """
    Log critical message.
    """
    logging.getLogger(logger_name).critical(message)


__all__ = [
    "configure_logging",
    "get_logger",
    "quiet_library_loggers",
    "set_verbose_mode",
    "create_file_handler",
    "add_file_logging",
    "log_exception",
    "LoggerContext",
    "QuietLogger",
    "debug",
    "info",
    "warning",
    "error",
    "critical",
]
