"""
Error types and handling for cloud provider operations.
"""

import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum


class ErrorCategory(StrEnum):
    """
    Error categories for consistent handling.
    """

    AUTHENTICATION = "AUTHENTICATION"
    QUOTA = "QUOTA"
    VALIDATION = "VALIDATION"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    PROVISIONING = "PROVISIONING"
    NETWORK = "NETWORK"
    INTERNAL = "INTERNAL"
    NOT_SUPPORTED = "NOT_SUPPORTED"


class CloudError(Exception):
    """
    Base error type for all cloud provider errors.
    """

    def __init__(
        self,
        category: ErrorCategory,
        code: str,
        message: str,
        provider: str | None = None,
        resource_id: str | None = None,
        retryable: bool = False,
        status_code: int | None = None,
        metadata: dict[str, str] | None = None,
        cause: Exception | None = None,
    ):
        self.category = category
        self.code = code
        self.message = message
        self.provider = provider
        self.resource_id = resource_id
        self.retryable = retryable
        self.status_code = status_code
        self.metadata = metadata or {}
        self.cause = cause
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        if self.provider:
            return f"[{self.provider}/{self.category.value}] {self.code}: {self.message}"
        return f"[{self.category.value}] {self.code}: {self.message}"

    def __str__(self) -> str:
        return self._format_message()


class AuthenticationError(CloudError):
    """
    Credential or permission issues.
    """

    def __init__(self, provider: str, message: str, cause: Exception | None = None):
        super().__init__(
            category=ErrorCategory.AUTHENTICATION,
            code="AUTH_FAILED",
            message=message,
            provider=provider,
            retryable=False,
            cause=cause,
        )


class QuotaError(CloudError):
    """
    Resource or rate limits exceeded.
    """

    def __init__(
        self,
        provider: str,
        message: str,
        limit: int,
        current: int,
        reset_time: datetime | None = None,
    ):
        super().__init__(
            category=ErrorCategory.QUOTA,
            code="QUOTA_EXCEEDED",
            message=message,
            provider=provider,
            retryable=True,
        )
        self.limit = limit
        self.current = current
        self.reset_time = reset_time


class ValidationError(CloudError):
    """
    Invalid configuration or input.
    """

    def __init__(
        self,
        provider: str,
        field: str,
        message: str,
    ):
        super().__init__(
            category=ErrorCategory.VALIDATION,
            code="INVALID_CONFIG",
            message=message,
            provider=provider,
            retryable=False,
        )
        self.field = field


class ResourceNotFoundError(CloudError):
    """
    Resource doesn't exist.
    """

    def __init__(self, provider: str, resource_id: str):
        super().__init__(
            category=ErrorCategory.NOT_FOUND,
            code="RESOURCE_NOT_FOUND",
            message=f"Resource '{resource_id}' not found",
            provider=provider,
            resource_id=resource_id,
            retryable=False,
        )


class ConflictError(CloudError):
    """
    Resource conflict (e.g., already exists).
    """

    def __init__(
        self,
        provider: str,
        message: str,
        conflicting_resource: str | None = None,
    ):
        super().__init__(
            category=ErrorCategory.CONFLICT,
            code="RESOURCE_CONFLICT",
            message=message,
            provider=provider,
            retryable=False,
        )
        self.conflicting_resource = conflicting_resource


class ProvisioningError(CloudError):
    """
    Resource creation/modification failed.
    """

    def __init__(
        self,
        provider: str,
        phase: str,
        message: str,
        cause: Exception | None = None,
    ):
        super().__init__(
            category=ErrorCategory.PROVISIONING,
            code="PROVISIONING_FAILED",
            message=message,
            provider=provider,
            retryable=True,
            cause=cause,
        )
        self.phase = phase


class NetworkError(CloudError):
    """
    Connection or network issues.
    """

    def __init__(
        self,
        provider: str,
        endpoint: str,
        message: str,
        cause: Exception | None = None,
    ):
        super().__init__(
            category=ErrorCategory.NETWORK,
            code="NETWORK_ERROR",
            message=message,
            provider=provider,
            retryable=True,
            cause=cause,
        )
        self.endpoint = endpoint


class InternalProviderError(CloudError):
    """
    Provider-side error.
    """

    def __init__(
        self,
        provider: str,
        message: str,
        status_code: int | None = None,
        cause: Exception | None = None,
    ):
        super().__init__(
            category=ErrorCategory.INTERNAL,
            code="PROVIDER_ERROR",
            message=message,
            provider=provider,
            retryable=True,
            status_code=status_code,
            cause=cause,
        )


class NotSupportedError(CloudError):
    """
    Operation not supported by provider.
    """

    def __init__(self, provider: str, operation: str):
        super().__init__(
            category=ErrorCategory.NOT_SUPPORTED,
            code="NOT_SUPPORTED",
            message=f"Operation '{operation}' not supported by provider",
            provider=provider,
            retryable=False,
        )
        self.operation = operation


@dataclass
class RetryConfig:
    """
    Retry behavior configuration.
    """

    max_retries: int = 5
    initial_delay: timedelta = field(default_factory=lambda: timedelta(seconds=1))
    max_delay: timedelta = field(default_factory=lambda: timedelta(seconds=16))
    multiplier: float = 2.0
    jitter: bool = True
    retryable_errors: list[ErrorCategory] = field(
        default_factory=lambda: [
            ErrorCategory.QUOTA,
            ErrorCategory.PROVISIONING,
            ErrorCategory.NETWORK,
            ErrorCategory.INTERNAL,
        ],
    )


# Default retry configuration
DefaultRetryConfig = RetryConfig()


def should_retry(error: Exception, config: RetryConfig = DefaultRetryConfig) -> bool:
    """
    Determine if an error should be retried.
    """
    if not isinstance(error, CloudError):
        # Network errors and timeouts are generally retryable
        return bool(isinstance(error, (ConnectionError, TimeoutError)))

    if not error.retryable:
        return False

    return error.category in config.retryable_errors


def calculate_backoff(
    attempt: int,
    config: RetryConfig = DefaultRetryConfig,
) -> timedelta:
    """
    Calculate next retry delay with exponential backoff.
    """
    if attempt >= config.max_retries:
        return timedelta(0)

    delay = config.initial_delay
    for _ in range(attempt):
        delay = timedelta(seconds=delay.total_seconds() * config.multiplier)
        if delay > config.max_delay:
            delay = config.max_delay
            break

    if config.jitter:
        # Add up to 25% jitter
        jitter_factor = 0.25 * (0.5 - random.random())
        delay = timedelta(seconds=delay.total_seconds() * (1 + jitter_factor))

    return delay


async def retry_async(
    func: callable,
    *args,
    config: RetryConfig = DefaultRetryConfig,
    **kwargs,
):
    """
    Retry an async function with exponential backoff.
    """
    last_error = None

    for attempt in range(config.max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_error = e
            if attempt >= config.max_retries or not should_retry(e, config):
                raise

            delay = calculate_backoff(attempt, config)
            if delay.total_seconds() > 0:
                time.sleep(delay.total_seconds())

    if last_error:
        raise last_error
    return None


def retry_sync(
    func: callable,
    *args,
    config: RetryConfig = DefaultRetryConfig,
    **kwargs,
):
    """
    Retry a sync function with exponential backoff.
    """
    last_error = None

    for attempt in range(config.max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            if attempt >= config.max_retries or not should_retry(e, config):
                raise

            delay = calculate_backoff(attempt, config)
            if delay.total_seconds() > 0:
                time.sleep(delay.total_seconds())

    if last_error:
        raise last_error
    return None


def wrap_error(
    provider: str,
    category: ErrorCategory,
    message: str,
    error: Exception,
) -> CloudError:
    """
    Wrap a generic error as a CloudError.
    """
    retryable = category in [
        ErrorCategory.NETWORK,
        ErrorCategory.PROVISIONING,
        ErrorCategory.INTERNAL,
        ErrorCategory.QUOTA,
    ]

    return CloudError(
        category=category,
        code=category.value,
        message=message,
        provider=provider,
        retryable=retryable,
        cause=error,
    )
