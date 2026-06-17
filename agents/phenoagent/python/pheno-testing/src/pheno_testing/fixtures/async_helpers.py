"""Async helper fixtures for testing.

Provides utilities for async testing including event loops, timeouts, and contexts.
"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import pytest

# ============================================================================
# Event Loop Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session.

    This fixture provides a single event loop for all async tests in the session.

    Example:
        def test_async_function(event_loop):
            result = event_loop.run_until_complete(async_function())
            assert result == expected
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


# ============================================================================
# Async Timeout Fixture
# ============================================================================


@pytest.fixture
def async_timeout():
    """Factory fixture for creating async timeouts.

    Example:
        async def test_with_timeout(async_timeout):
            async with async_timeout(5.0):
                # This will timeout after 5 seconds
                await slow_operation()
    """

    @asynccontextmanager
    async def _timeout(seconds: float):
        """Create an async timeout context.

        Args:
            seconds: Timeout in seconds
        """
        try:
            async with asyncio.timeout(seconds):
                yield
        except TimeoutError:
            pytest.fail(f"Operation timed out after {seconds} seconds")

    return _timeout


# ============================================================================
# Async Context Fixture
# ============================================================================


class AsyncContext:
    """Async context manager for testing.

    Provides utilities for managing async resources in tests.
    """

    def __init__(self):
        self.resources = []
        self.cleanup_callbacks = []

    async def add_resource(self, resource: Any) -> Any:
        """Add a resource to be cleaned up.

        Args:
            resource: Resource to track

        Returns:
            The resource
        """
        self.resources.append(resource)
        return resource

    def add_cleanup(self, callback, *args, **kwargs):
        """Add a cleanup callback.

        Args:
            callback: Cleanup function
            *args: Positional arguments for callback
            **kwargs: Keyword arguments for callback
        """
        self.cleanup_callbacks.append((callback, args, kwargs))

    async def cleanup(self):
        """
        Clean up all resources and run cleanup callbacks.
        """
        # Run cleanup callbacks in reverse order
        for callback, args, kwargs in reversed(self.cleanup_callbacks):
            if asyncio.iscoroutinefunction(callback):
                await callback(*args, **kwargs)
            else:
                callback(*args, **kwargs)

        # Close resources
        for resource in reversed(self.resources):
            if hasattr(resource, "close"):
                if asyncio.iscoroutinefunction(resource.close):
                    await resource.close()
                else:
                    resource.close()
            elif hasattr(resource, "aclose"):
                await resource.aclose()

        self.resources.clear()
        self.cleanup_callbacks.clear()


@pytest.fixture
async def async_context() -> AsyncGenerator[AsyncContext, None]:
    """Create an async context for managing test resources.

    Example:
        async def test_with_context(async_context):
            # Add resources
            client = await async_context.add_resource(AsyncClient())

            # Add cleanup callback
            async_context.add_cleanup(cleanup_function, arg1, arg2)

            # Use resources
            await client.get("/api")

            # Cleanup happens automatically
    """
    context = AsyncContext()
    yield context
    await context.cleanup()


# ============================================================================
# Async Utilities
# ============================================================================


async def wait_for_condition(
    condition_func,
    timeout: float = 5.0,
    interval: float = 0.1,
    error_message: str = "Condition not met within timeout",
):
    """Wait for a condition to become true.

    Args:
        condition_func: Function that returns True when condition is met
        timeout: Maximum time to wait in seconds
        interval: Time between checks in seconds
        error_message: Error message if timeout occurs

    Example:
        async def test_eventual_consistency(async_db_session):
            # Create user
            user = User(name="Test")
            async_db_session.add(user)
            await async_db_session.commit()

            # Wait for user to appear in cache
            await wait_for_condition(
                lambda: cache.get("user:1") is not None,
                timeout=5.0
            )
    """
    start_time = asyncio.get_event_loop().time()

    while True:
        if asyncio.iscoroutinefunction(condition_func):
            result = await condition_func()
        else:
            result = condition_func()

        if result:
            return

        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed >= timeout:
            raise TimeoutError(error_message)

        await asyncio.sleep(interval)


async def run_with_timeout(coro, timeout: float = 5.0):
    """Run a coroutine with a timeout.

    Args:
        coro: Coroutine to run
        timeout: Timeout in seconds

    Returns:
        Result of the coroutine

    Raises:
        asyncio.TimeoutError: If timeout occurs

    Example:
        async def test_with_timeout():
            result = await run_with_timeout(
                slow_operation(),
                timeout=5.0
            )
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except TimeoutError:
        raise TimeoutError(f"Operation timed out after {timeout} seconds")


@asynccontextmanager
async def async_nullcontext(value=None):
    """Async version of contextlib.nullcontext.

    Useful for conditional context managers in tests.

    Example:
        async def test_conditional_context(use_context):
            ctx = async_timeout(5.0) if use_context else async_nullcontext()
            async with ctx:
                await operation()
    """
    yield value


__all__ = [
    "AsyncContext",
    "async_context",
    "async_nullcontext",
    "async_timeout",
    "event_loop",
    "run_with_timeout",
    "wait_for_condition",
]
