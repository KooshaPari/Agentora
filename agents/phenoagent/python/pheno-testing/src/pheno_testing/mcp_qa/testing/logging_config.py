"""
Test Logging Setup - Minimal, intuitive logging for test suites

Provides clean, progress-bar-based output with verbose logging only on errors.
This is used across all test suites (atoms_mcp, zen-mcp-server, etc.) to reduce
log spam and provide a better user experience.

Usage:
    from tests.framework.test_logging_setup import configure_test_logging

    # At the start of your test suite
    configure_test_logging(verbose=False)  # Quiet mode - only errors
    configure_test_logging(verbose=True)   # Verbose mode - all logs
"""

import logging
import sys
from typing import Optional


def configure_test_logging(
    verbose: bool = False, show_progress: bool = True, capture_warnings: bool = True
) -> None:
    """Configure logging for test suites with minimal output.

    In quiet mode (verbose=False):
    - Only ERROR and CRITICAL logs are shown
    - Progress bars and visual indicators are used instead
    - Natural language output for test results

    In verbose mode (verbose=True):
    - All logs (INFO, DEBUG, etc.) are shown
    - Useful for debugging test failures

    Args:
        verbose: Enable verbose logging (default: False)
        show_progress: Show progress bars (default: True)
        capture_warnings: Capture Python warnings (default: True)
    """
    # Determine log level
    if verbose:
        level = logging.DEBUG
        format_str = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    else:
        level = logging.ERROR  # Only show errors in quiet mode
        format_str = "%(levelname)s | %(message)s"

    # Configure root logger
    logging.basicConfig(
        level=level,
        format=format_str,
        stream=sys.stderr,
        force=True,  # Override any existing configuration
    )

    # Suppress noisy third-party libraries unless verbose
    if not verbose:
        # MCP-related loggers
        logging.getLogger("mcp").setLevel(logging.ERROR)
        logging.getLogger("fastmcp").setLevel(logging.ERROR)
        logging.getLogger("mcp.client").setLevel(logging.ERROR)
        logging.getLogger("mcp.server").setLevel(logging.ERROR)

        # HTTP clients
        logging.getLogger("httpx").setLevel(logging.ERROR)
        logging.getLogger("httpcore").setLevel(logging.ERROR)
        logging.getLogger("urllib3").setLevel(logging.ERROR)

        # OAuth and auth
        logging.getLogger("mcp_qa.oauth").setLevel(logging.ERROR)
        logging.getLogger("mcp_qa.auth").setLevel(logging.ERROR)

        # Playwright (very noisy)
        logging.getLogger("playwright").setLevel(logging.ERROR)

        # Websockets
        logging.getLogger("websockets").setLevel(logging.ERROR)
        logging.getLogger("uvicorn").setLevel(logging.ERROR)

        # Asyncio
        logging.getLogger("asyncio").setLevel(logging.ERROR)

    # Capture warnings if requested
    if capture_warnings:
        logging.captureWarnings(True)
        if not verbose:
            logging.getLogger("py.warnings").setLevel(logging.ERROR)


def get_test_logger(name: str, verbose: bool = False) -> logging.Logger:
    """Get a logger for test modules.

    Args:
        name: Logger name (usually __name__)
        verbose: Enable verbose logging for this logger

    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    if not verbose:
        logger.setLevel(logging.ERROR)
    return logger


def suppress_deprecation_warnings() -> None:
    """Suppress common deprecation warnings that clutter test output.

    Call this at the start of your test suite to hide warnings like:
    - websockets.legacy deprecation
    - WebSocketServerProtocol deprecation
    """
    import warnings

    # Suppress websockets deprecation warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="websockets.*")

    # Suppress uvicorn websockets deprecation
    warnings.filterwarnings(
        "ignore", category=DeprecationWarning, message=".*WebSocketServerProtocol.*"
    )

    # Suppress other common test-related warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*legacy.*")


class QuietLogger:
    """Context manager for temporarily suppressing logs.

    Usage:
        with QuietLogger():
            # Code that produces noisy logs
            await oauth_flow()
    """

    def __init__(self, level: int = logging.ERROR):
        self.level = level
        self.previous_levels = {}

    def __enter__(self):
        # Save current levels and set to ERROR
        for logger_name in ["mcp", "httpx", "playwright", "websockets", "uvicorn"]:
            logger = logging.getLogger(logger_name)
            self.previous_levels[logger_name] = logger.level
            logger.setLevel(self.level)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore previous levels
        for logger_name, previous_level in self.previous_levels.items():
            logging.getLogger(logger_name).setLevel(previous_level)


def print_test_header(title: str, emoji: str = "🧪") -> None:
    """Print a clean test header.

    Args:
        title: Test suite title
        emoji: Emoji to display (default: 🧪)
    """
    print(f"\n{emoji} {title}")
    print("=" * 80)


def print_test_summary(
    total: int, passed: int, failed: int, skipped: int = 0, duration_seconds: Optional[float] = None
) -> None:
    """Print a clean test summary.

    Args:
        total: Total number of tests
        passed: Number of passed tests
        failed: Number of failed tests
        skipped: Number of skipped tests
        duration_seconds: Total duration in seconds
    """
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    print(f"Total:   {total}")
    print(f"✅ Passed:  {passed}")
    print(f"❌ Failed:  {failed}")
    if skipped > 0:
        print(f"⏭️  Skipped: {skipped}")

    if total > 0:
        pass_rate = (passed / total) * 100
        print(f"Pass Rate: {pass_rate:.1f}%")

    if duration_seconds is not None:
        print(f"Duration:  {duration_seconds:.2f}s")
    print("=" * 80 + "\n")


# Auto-configure on import if not already configured
_configured = False


def auto_configure(verbose: bool = False) -> None:
    """Auto-configure logging on first import.

    Args:
        verbose: Enable verbose logging
    """
    global _configured
    if not _configured:
        configure_test_logging(verbose=verbose)
        suppress_deprecation_warnings()
        _configured = True
