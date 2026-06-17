"""HTTP retry utilities with CloudFlare 530 error handling.

Provides reusable retry logic with exponential backoff for HTTP requests,
with special handling for CloudFlare tunnel errors (530).

Features:
- Automatic retry on 5xx errors (especially 530)
- Exponential backoff (1s, 2s, 4s, 8s, 16s)
- Configurable max retries (default 5)
- Detailed logging of retry attempts
- Special messaging for CloudFlare tunnel issues (530)
- Compatible with both httpx and requests libraries
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from functools import wraps
from typing import Callable, Optional, Set, TypeVar

import httpx

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class HTTPRetryConfig:
    """Configuration for HTTP retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts (default: 5)
        backoff_factor: Exponential backoff multiplier (default: 2)
        initial_backoff: Initial backoff delay in seconds (default: 1.0)
        max_backoff: Maximum backoff delay in seconds (default: 60.0)
        retryable_status_codes: HTTP status codes to retry on
        retry_on_timeout: Whether to retry on timeout errors
        retry_on_connection_error: Whether to retry on connection errors
    """

    max_retries: int = 5
    backoff_factor: float = 2.0
    initial_backoff: float = 1.0
    max_backoff: float = 60.0
    retryable_status_codes: Set[int] = None
    retry_on_timeout: bool = True
    retry_on_connection_error: bool = True

    def __post_init__(self):
        """
        Set default retryable status codes if not provided.
        """
        if self.retryable_status_codes is None:
            # CloudFlare 530 + common 5xx errors
            self.retryable_status_codes = {500, 502, 503, 504, 530}


class HTTPRetryError(Exception):
    """
    Raised when all retry attempts are exhausted.
    """

    def __init__(self, message: str, last_error: Exception, attempts: int):
        super().__init__(message)
        self.last_error = last_error
        self.attempts = attempts


def get_backoff_delay(attempt: int, config: HTTPRetryConfig) -> float:
    """Calculate exponential backoff delay for retry attempt.

    Args:
        attempt: Current attempt number (1-based)
        config: Retry configuration

    Returns:
        Delay in seconds (capped at max_backoff)
    """
    delay = config.initial_backoff * (config.backoff_factor ** (attempt - 1))
    return min(delay, config.max_backoff)


def is_retryable_error(error: Exception, config: HTTPRetryConfig) -> tuple[bool, str]:
    """Check if an error is retryable based on configuration.

    Args:
        error: Exception to check
        config: Retry configuration

    Returns:
        Tuple of (is_retryable, error_description)
    """
    # HTTP status errors
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code

        # Special handling for CloudFlare 530 error
        if status == 530:
            return True, "CloudFlare tunnel unreachable (530)"

        # Check if status code is in retryable set
        if status in config.retryable_status_codes:
            return True, f"HTTP {status} error"

        return False, f"Non-retryable HTTP {status} error"

    # Timeout errors
    if config.retry_on_timeout and isinstance(
        error, (httpx.TimeoutException, httpx.ReadTimeout, httpx.ConnectTimeout)
    ):
        return True, "Request timeout"

    # Connection errors
    if config.retry_on_connection_error and isinstance(
        error, (httpx.ConnectError, httpx.RemoteProtocolError, httpx.NetworkError)
    ):
        return True, "Connection error"

    # Non-retryable error
    return False, str(error)


async def retry_async(
    func: Callable[..., T],
    *args,
    config: Optional[HTTPRetryConfig] = None,
    operation_name: str = "HTTP request",
    **kwargs,
) -> T:
    """Retry an async function with exponential backoff.

    Args:
        func: Async function to retry
        *args: Positional arguments for func
        config: Retry configuration (uses defaults if None)
        operation_name: Human-readable operation name for logging
        **kwargs: Keyword arguments for func

    Returns:
        Result from successful function call

    Raises:
        HTTPRetryError: If all retry attempts are exhausted

    Example:
        >>> async def fetch_data():
        ...     async with httpx.AsyncClient() as client:
        ...         response = await client.get("https://api.example.com/data")
        ...         response.raise_for_status()
        ...         return response.json()
        ...
        >>> result = await retry_async(fetch_data, operation_name="fetch data")
    """
    if config is None:
        config = HTTPRetryConfig()

    last_error: Optional[Exception] = None

    for attempt in range(1, config.max_retries + 1):
        try:
            result = await func(*args, **kwargs)

            # Log success if we had previous failures
            if attempt > 1:
                logger.info(
                    f"✓ {operation_name} succeeded on attempt {attempt}/{config.max_retries}"
                )

            return result

        except Exception as error:
            last_error = error
            is_retryable, error_desc = is_retryable_error(error, config)

            # If not retryable or last attempt, raise immediately
            if not is_retryable or attempt >= config.max_retries:
                if attempt >= config.max_retries:
                    logger.error(
                        f"❌ {operation_name} failed after {config.max_retries} attempts. "
                        f"Last error: {error_desc}"
                    )
                else:
                    logger.error(f"❌ {operation_name} failed: {error_desc}")

                raise HTTPRetryError(
                    f"{operation_name} failed after {attempt} attempt(s): {error_desc}",
                    last_error=error,
                    attempts=attempt,
                ) from error

            # Calculate backoff delay
            delay = get_backoff_delay(attempt, config)

            # Log retry with special message for CloudFlare 530
            if isinstance(error, httpx.HTTPStatusError) and error.response.status_code == 530:
                logger.warning(
                    f"⚠️  CloudFlare tunnel unreachable (530), retrying in {delay:.1f}s "
                    f"(attempt {attempt}/{config.max_retries})..."
                )
            else:
                logger.warning(
                    f"⏱️  {operation_name} failed ({error_desc}), "
                    f"retrying in {delay:.1f}s (attempt {attempt}/{config.max_retries})..."
                )

            # Wait before retry
            await asyncio.sleep(delay)

    # Should never reach here, but just in case
    raise HTTPRetryError(
        f"{operation_name} failed after {config.max_retries} attempts",
        last_error=last_error or Exception("Unknown error"),
        attempts=config.max_retries,
    )


def retry_sync(
    func: Callable[..., T],
    *args,
    config: Optional[HTTPRetryConfig] = None,
    operation_name: str = "HTTP request",
    **kwargs,
) -> T:
    """Retry a synchronous function with exponential backoff.

    Same as retry_async but for synchronous functions.

    Args:
        func: Synchronous function to retry
        *args: Positional arguments for func
        config: Retry configuration (uses defaults if None)
        operation_name: Human-readable operation name for logging
        **kwargs: Keyword arguments for func

    Returns:
        Result from successful function call

    Raises:
        HTTPRetryError: If all retry attempts are exhausted
    """
    if config is None:
        config = HTTPRetryConfig()

    last_error: Optional[Exception] = None

    for attempt in range(1, config.max_retries + 1):
        try:
            result = func(*args, **kwargs)

            # Log success if we had previous failures
            if attempt > 1:
                logger.info(
                    f"✓ {operation_name} succeeded on attempt {attempt}/{config.max_retries}"
                )

            return result

        except Exception as error:
            last_error = error
            is_retryable, error_desc = is_retryable_error(error, config)

            # If not retryable or last attempt, raise immediately
            if not is_retryable or attempt >= config.max_retries:
                if attempt >= config.max_retries:
                    logger.error(
                        f"❌ {operation_name} failed after {config.max_retries} attempts. "
                        f"Last error: {error_desc}"
                    )
                else:
                    logger.error(f"❌ {operation_name} failed: {error_desc}")

                raise HTTPRetryError(
                    f"{operation_name} failed after {attempt} attempt(s): {error_desc}",
                    last_error=error,
                    attempts=attempt,
                ) from error

            # Calculate backoff delay
            delay = get_backoff_delay(attempt, config)

            # Log retry with special message for CloudFlare 530
            if isinstance(error, httpx.HTTPStatusError) and error.response.status_code == 530:
                logger.warning(
                    f"⚠️  CloudFlare tunnel unreachable (530), retrying in {delay:.1f}s "
                    f"(attempt {attempt}/{config.max_retries})..."
                )
            else:
                logger.warning(
                    f"⏱️  {operation_name} failed ({error_desc}), "
                    f"retrying in {delay:.1f}s (attempt {attempt}/{config.max_retries})..."
                )

            # Wait before retry
            time.sleep(delay)

    # Should never reach here, but just in case
    raise HTTPRetryError(
        f"{operation_name} failed after {config.max_retries} attempts",
        last_error=last_error or Exception("Unknown error"),
        attempts=config.max_retries,
    )


def with_retry(config: Optional[HTTPRetryConfig] = None, operation_name: Optional[str] = None):
    """Decorator to add retry logic to async functions.

    Args:
        config: Retry configuration (uses defaults if None)
        operation_name: Human-readable operation name (uses func name if None)

    Example:
        >>> @with_retry(operation_name="fetch user data")
        ... async def fetch_user(user_id: str):
        ...     async with httpx.AsyncClient() as client:
        ...         response = await client.get(f"https://api.example.com/users/{user_id}")
        ...         response.raise_for_status()
        ...         return response.json()
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            op_name = operation_name or func.__name__
            return await retry_async(func, *args, config=config, operation_name=op_name, **kwargs)

        return wrapper

    return decorator


def with_retry_sync(config: Optional[HTTPRetryConfig] = None, operation_name: Optional[str] = None):
    """Decorator to add retry logic to synchronous functions.

    Same as with_retry but for synchronous functions.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation_name or func.__name__
            return retry_sync(func, *args, config=config, operation_name=op_name, **kwargs)

        return wrapper

    return decorator


__all__ = [
    "HTTPRetryConfig",
    "HTTPRetryError",
    "retry_async",
    "retry_sync",
    "with_retry",
    "with_retry_sync",
    "get_backoff_delay",
    "is_retryable_error",
]
