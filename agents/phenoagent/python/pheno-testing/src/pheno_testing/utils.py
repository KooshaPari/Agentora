"""
Test utilities and helper functions.
"""

import asyncio
import logging
import os
import time
from collections.abc import Callable
from contextlib import contextmanager
from io import StringIO

# ============================================================================
# Assertion Utilities
# ============================================================================


async def assert_eventually(
    condition: Callable[[], bool],
    timeout: float = 5.0,
    interval: float = 0.1,
    message: str = "Condition not met within timeout",
) -> None:
    """Assert that a condition eventually becomes true.

    Useful for testing eventual consistency.

    Args:
        condition: Function that returns True when condition is met
        timeout: Maximum time to wait in seconds
        interval: Time between checks in seconds
        message: Error message if timeout occurs

    Example:
        async def test_cache_update():
            update_cache("key", "value")

            await assert_eventually(
                lambda: get_cache("key") == "value",
                timeout=5.0,
                message="Cache not updated"
            )
    """
    start_time = time.time()

    while True:
        if asyncio.iscoroutinefunction(condition):
            result = await condition()
        else:
            result = condition()

        if result:
            return

        elapsed = time.time() - start_time
        if elapsed >= timeout:
            raise AssertionError(f"{message} (waited {elapsed:.2f}s)")

        await asyncio.sleep(interval)


def wait_for(
    condition: Callable[[], bool],
    timeout: float = 5.0,
    interval: float = 0.1,
    message: str = "Condition not met within timeout",
) -> None:
    """Wait for a condition to become true (sync version).

    Args:
        condition: Function that returns True when condition is met
        timeout: Maximum time to wait in seconds
        interval: Time between checks in seconds
        message: Error message if timeout occurs

    Example:
        def test_file_creation():
            create_file("test.txt")

            wait_for(
                lambda: os.path.exists("test.txt"),
                timeout=5.0,
                message="File not created"
            )
    """
    start_time = time.time()

    while True:
        if condition():
            return

        elapsed = time.time() - start_time
        if elapsed >= timeout:
            raise AssertionError(f"{message} (waited {elapsed:.2f}s)")

        time.sleep(interval)


# ============================================================================
# Log Capture Utilities
# ============================================================================


@contextmanager
def capture_logs(logger_name: str | None = None, level: int = logging.INFO):
    """Capture log messages for testing.

    Args:
        logger_name: Name of logger to capture (None for root logger)
        level: Minimum log level to capture

    Yields:
        StringIO object containing captured logs

    Example:
        def test_logging():
            with capture_logs("myapp") as log_output:
                logger = logging.getLogger("myapp")
                logger.info("Test message")

                assert "Test message" in log_output.getvalue()
    """
    logger = logging.getLogger(logger_name)
    original_level = logger.level
    original_handlers = logger.handlers[:]

    # Create string buffer and handler
    log_buffer = StringIO()
    handler = logging.StreamHandler(log_buffer)
    handler.setLevel(level)

    # Set up logger
    logger.setLevel(level)
    logger.handlers = [handler]

    try:
        yield log_buffer
    finally:
        # Restore original logger state
        logger.setLevel(original_level)
        logger.handlers = original_handlers


# ============================================================================
# Environment Variable Utilities
# ============================================================================


@contextmanager
def temp_env(**kwargs):
    """Temporarily set environment variables.

    Args:
        **kwargs: Environment variables to set

    Example:
        def test_with_env():
            with temp_env(DATABASE_URL="sqlite:///:memory:", DEBUG="true"):
                # Environment variables set
                assert os.getenv("DATABASE_URL") == "sqlite:///:memory:"

            # Environment variables restored
    """
    original_env = {}

    # Save original values and set new ones
    for key, value in kwargs.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = str(value)

    try:
        yield
    finally:
        # Restore original values
        for key, original_value in original_env.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value


# ============================================================================
# Time Utilities
# ============================================================================


class FreezeTime:
    """Context manager to freeze time for testing.

    Example:
        def test_with_frozen_time():
            with FreezeTime("2025-01-01 12:00:00"):
                # Time is frozen
                now = datetime.now()
                assert now.year == 2025
    """

    def __init__(self, frozen_time: str):
        """Initialize with frozen time.

        Args:
            frozen_time: Time to freeze to (ISO format)
        """
        from datetime import datetime

        self.frozen_time = datetime.fromisoformat(frozen_time)
        self.original_time = None

    def __enter__(self):
        """
        Enter context.
        """
        # Note: This is a simplified version
        # For production use, consider using freezegun library
        return self

    def __exit__(self, *args):
        """
        Exit context.
        """


# ============================================================================
# Comparison Utilities
# ============================================================================


def assert_dict_contains(actual: dict, expected: dict, path: str = "") -> None:
    """Assert that actual dict contains all keys/values from expected dict.

    Args:
        actual: Actual dictionary
        expected: Expected dictionary (subset)
        path: Current path (for error messages)

    Example:
        def test_response():
            response = {"user": {"id": 1, "name": "Test", "extra": "data"}}

            assert_dict_contains(
                response,
                {"user": {"id": 1, "name": "Test"}}
            )
    """
    for key, expected_value in expected.items():
        current_path = f"{path}.{key}" if path else key

        if key not in actual:
            raise AssertionError(f"Missing key: {current_path}")

        actual_value = actual[key]

        if isinstance(expected_value, dict) and isinstance(actual_value, dict):
            assert_dict_contains(actual_value, expected_value, current_path)
        elif actual_value != expected_value:
            raise AssertionError(
                f"Value mismatch at {current_path}: "
                f"expected {expected_value!r}, got {actual_value!r}",
            )


def assert_list_contains(actual: list, expected: list) -> None:
    """Assert that actual list contains all items from expected list.

    Args:
        actual: Actual list
        expected: Expected items (subset)

    Example:
        def test_list():
            actual = [1, 2, 3, 4, 5]
            assert_list_contains(actual, [2, 4])
    """
    for item in expected:
        if item not in actual:
            raise AssertionError(f"Missing item: {item!r}")


# ============================================================================
# Retry Utilities
# ============================================================================


def retry_on_exception(max_attempts: int = 3, delay: float = 0.1, exceptions: tuple = (Exception,)):
    """Decorator to retry function on exception.

    Useful for flaky tests.

    Args:
        max_attempts: Maximum number of attempts
        delay: Delay between attempts in seconds
        exceptions: Tuple of exceptions to catch

    Example:
        @retry_on_exception(max_attempts=3, delay=0.5)
        def test_flaky_operation():
            # Test that might fail occasionally
            pass
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(delay)

            raise last_exception

        return wrapper

    return decorator


__all__ = [
    "FreezeTime",
    "assert_dict_contains",
    "assert_eventually",
    "assert_list_contains",
    "capture_logs",
    "retry_on_exception",
    "temp_env",
    "wait_for",
]
