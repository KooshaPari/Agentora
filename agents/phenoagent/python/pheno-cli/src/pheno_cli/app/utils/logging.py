"""
Logging utilities for Pheno-CLI.
"""

import logging
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

console = Console()


def setup_logging(
    verbose: bool = False,
    debug: bool = False,
    log_file: Path | None = None,
) -> None:
    """
    Setup logging for the CLI.
    """

    # Determine log level
    if debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO
    else:
        level = logging.WARNING

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(level)

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Console handler with rich formatting
    console_handler = RichHandler(
        console=console,
        show_path=debug,
        show_time=debug,
        markup=True,
        rich_tracebacks=True,
    )
    console_handler.setLevel(level)

    # Format for console
    console_format = "%(message)s" if not debug else "%(name)s: %(message)s"
    console_handler.setFormatter(logging.Formatter(console_format))

    logger.addHandler(console_handler)

    # File handler if log file specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # Always debug level for files

        # More detailed format for file
        file_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        file_handler.setFormatter(logging.Formatter(file_format))

        logger.addHandler(file_handler)

        console.print(f"[dim]Logging to file: {log_file}[/dim]")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.
    """
    return logging.getLogger(name)
