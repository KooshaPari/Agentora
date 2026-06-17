"""Test Decorators for MCP-QA Framework.

Provides decorators for:
- Test registration and discovery (@mcp_test)
- Authentication requirements (@require_auth)
- Conditional skipping (@skip_if)
- Timeout enforcement (@timeout)
- Retry logic (@retry)
- Result caching (@cache_result)
"""

import asyncio
import functools
import time
from typing import Any, Callable, Dict, Optional

from pheno.testing.mcp_qa.framework.cache import TestCache


class TestRegistry:
    """
    Registry for test discovery via decorators.
    """

    def __init__(self):
        self.tests: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        name: str,
        func: Callable,
        tool_name: str,
        category: str = "functional",
        priority: int = 5,
        requires_auth: bool = False,
        timeout_seconds: int = 30,
        tags: Optional[list] = None,
    ):
        """
        Register a test function with metadata.
        """
        self.tests[name] = {
            "func": func,
            "tool_name": tool_name,
            "category": category,
            "priority": priority,
            "requires_auth": requires_auth,
            "timeout_seconds": timeout_seconds,
            "tags": tags or [],
        }

    def get_tests(
        self,
        category: Optional[str] = None,
        tool_name: Optional[str] = None,
        tags: Optional[list] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get tests filtered by criteria.
        """
        tests = self.tests.copy()

        if category:
            tests = {k: v for k, v in tests.items() if v["category"] == category}

        if tool_name:
            tests = {k: v for k, v in tests.items() if v["tool_name"] == tool_name}

        if tags:
            tests = {k: v for k, v in tests.items() if any(tag in v["tags"] for tag in tags)}

        return tests

    def clear(self):
        """
        Clear all registered tests.
        """
        self.tests.clear()


# Global test registry
_test_registry = TestRegistry()


def mcp_test(
    tool_name: str,
    category: str = "functional",
    priority: int = 5,
    timeout_seconds: int = 30,
    tags: Optional[list] = None,
):
    """Decorator to register an MCP test.

    Args:
        tool_name: Name of the MCP tool being tested
        category: Test category (functional, integration, performance, etc.)
        priority: Test priority (1-10, higher = more important)
        timeout_seconds: Maximum execution time
        tags: Optional list of tags for test filtering

    Usage:
        @mcp_test(tool_name="chat", category="core", priority=10, tags=["fast"])
        async def test_chat_basic(mcp_client):
            result = await mcp_client.call_tool("chat", {"prompt": "test"})
            assert result["success"]
    """

    def decorator(func: Callable):
        test_name = func.__name__
        _test_registry.register(
            name=test_name,
            func=func,
            tool_name=tool_name,
            category=category,
            priority=priority,
            timeout_seconds=timeout_seconds,
            tags=tags,
        )

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_auth(func: Callable):
    """Decorator to mark test as requiring authentication.

    Usage:
        @require_auth
        @mcp_test(tool_name="entity")
        async def test_create_organization(mcp_client):
            result = await mcp_client.call_tool("entity", {
                "operation": "create",
                "type": "organization",
                "data": {"name": "Test"}
            })
            assert result["success"]
    """
    test_name = func.__name__
    if test_name in _test_registry.tests:
        _test_registry.tests[test_name]["requires_auth"] = True

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)

    return wrapper


def skip_if(condition: Callable[[], bool], reason: str):
    """Decorator to conditionally skip a test.

    Args:
        condition: Callable that returns True to skip test
        reason: Human-readable reason for skipping

    Usage:
        @skip_if(lambda: not HAS_DATABASE, reason="Database not available")
        @mcp_test(tool_name="entity")
        async def test_entity_persistence(mcp_client):
            ...
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if condition():
                return {
                    "success": False,
                    "skipped": True,
                    "skip_reason": reason,
                }
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def timeout(seconds: int):
    """Decorator to enforce timeout on test execution.

    Args:
        seconds: Maximum execution time in seconds

    Usage:
        @timeout(30)
        @mcp_test(tool_name="query")
        async def test_large_query(mcp_client):
            result = await mcp_client.call_tool("query", {
                "query": "complex search"
            })
            assert result["success"]
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                return {"success": False, "error": f"Test timed out after {seconds}s"}

        return wrapper

    return decorator


def retry(max_attempts: int = 3, delay_seconds: float = 1.0, backoff: float = 2.0):
    """Decorator to retry test on failure with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        delay_seconds: Initial delay between retries
        backoff: Backoff multiplier for delay

    Usage:
        @retry(max_attempts=3, delay_seconds=1.0, backoff=2.0)
        @mcp_test(tool_name="external_api")
        async def test_external_service(mcp_client):
            # May fail due to network issues, will retry
            result = await mcp_client.call_tool("external_api", {})
            assert result["success"]
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            current_delay = delay_seconds

            for attempt in range(max_attempts):
                try:
                    result = await func(*args, **kwargs)
                    if result.get("success", False):
                        if attempt > 0:
                            # Add retry metadata
                            result["_retried"] = True
                            result["_attempts"] = attempt + 1
                        return result
                    last_error = result.get("error", "Unknown error")
                except Exception as e:
                    last_error = str(e)

                if attempt < max_attempts - 1:
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff

            return {
                "success": False,
                "error": f"Failed after {max_attempts} attempts: {last_error}",
                "_retried": True,
                "_attempts": max_attempts,
            }

        return wrapper

    return decorator


def cache_result(cache_instance: Optional[TestCache] = None):
    """Decorator to cache test results based on tool code hash.

    Args:
        cache_instance: TestCache instance (creates new if None)

    Usage:
        cache = TestCache()

        @cache_result(cache)
        @mcp_test(tool_name="chat")
        async def test_chat_basic(mcp_client):
            result = await mcp_client.call_tool("chat", {"prompt": "test"})
            assert result["success"]
            return result
    """
    if cache_instance is None:
        cache_instance = TestCache()

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            test_name = func.__name__
            tool_name = _test_registry.tests.get(test_name, {}).get("tool_name", "unknown")

            # Check cache
            if cache_instance.should_skip(test_name, tool_name):
                return {
                    "success": True,
                    "cached": True,
                    "skipped": True,
                    "message": "Result from cache",
                }

            # Run test
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start

                status = "passed" if result.get("success", False) else "failed"
                error = result.get("error")
                cache_instance.record(test_name, tool_name, status, duration, error)

                return result
            except Exception as e:
                duration = time.time() - start
                cache_instance.record(test_name, tool_name, "error", duration, str(e))
                raise

        return wrapper

    return decorator


def slow_test(func: Callable):
    """Decorator to mark test as slow.

    Adds "slow" tag to test metadata for filtering.

    Usage:
        @slow_test
        @mcp_test(tool_name="batch_processing")
        async def test_large_batch(mcp_client):
            # Long-running test
            ...
    """
    test_name = func.__name__
    if test_name in _test_registry.tests:
        tags = _test_registry.tests[test_name].get("tags", [])
        if "slow" not in tags:
            tags.append("slow")
            _test_registry.tests[test_name]["tags"] = tags

    return func


def integration_test(func: Callable):
    """Decorator to mark test as integration test.

    Adds "integration" tag and sets category to "integration".

    Usage:
        @integration_test
        @mcp_test(tool_name="workflow")
        async def test_multi_tool_workflow(mcp_client):
            # Integration test spanning multiple tools
            ...
    """
    test_name = func.__name__
    if test_name in _test_registry.tests:
        _test_registry.tests[test_name]["category"] = "integration"
        tags = _test_registry.tests[test_name].get("tags", [])
        if "integration" not in tags:
            tags.append("integration")
            _test_registry.tests[test_name]["tags"] = tags

    return func


def get_test_registry() -> TestRegistry:
    """Get the global test registry.

    Returns:
        TestRegistry: Global registry instance
    """
    return _test_registry
