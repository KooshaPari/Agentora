"""Test Decorators for Atoms MCP Test Framework.

Provides decorators for:
- Test registration and discovery
- Authentication requirements
- Conditional skipping
- Timeout enforcement
- Retry logic
- Result caching
"""

import asyncio
import functools
import time
from typing import Any, Callable, Dict, Optional


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
    ):
        """
        Register a test function.
        """
        self.tests[name] = {
            "func": func,
            "tool_name": tool_name,
            "category": category,
            "priority": priority,
            "requires_auth": requires_auth,
            "timeout_seconds": timeout_seconds,
        }

    def get_tests(self, category: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Get all tests, optionally filtered by category.
        """
        if category:
            return {k: v for k, v in self.tests.items() if v["category"] == category}
        return self.tests


# Global test registry
_test_registry = TestRegistry()


def mcp_test(
    tool_name: str,
    category: str = "functional",
    priority: int = 5,
    timeout_seconds: int = 30,
):
    """Decorator to register an MCP test.

    Usage:
        @mcp_test(tool_name="workspace_tool", category="core", priority=10)
        async def test_list_workspaces(client):
            result = await client.call_tool("workspace_tool", {"operation": "list_workspaces"})
            assert result.get("success")
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
        @mcp_test(tool_name="entity_tool")
        async def test_create_organization(client):
            ...
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

    Usage:
        @skip_if(lambda: not HAS_POSTGRES, reason="Postgres not available")
        @mcp_test(tool_name="entity_tool")
        async def test_create_organization(client):
            ...
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if condition():
                return {"success": False, "skipped": True, "skip_reason": reason}
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def timeout(seconds: int):
    """Decorator to enforce timeout on test execution.

    Usage:
        @timeout(30)
        @mcp_test(tool_name="query_tool")
        async def test_rag_search(client):
            ...
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


def retry(max_attempts: int = 3, delay_seconds: float = 1.0):
    """Decorator to retry test on failure.

    Usage:
        @retry(max_attempts=3, delay_seconds=2.0)
        @mcp_test(tool_name="query_tool")
        async def test_search(client):
            ...
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None

            for attempt in range(max_attempts):
                try:
                    result = await func(*args, **kwargs)
                    if result.get("success", False):
                        return result
                    last_error = result.get("error", "Unknown error")
                except Exception as e:
                    last_error = str(e)

                if attempt < max_attempts - 1:
                    await asyncio.sleep(delay_seconds)

            return {
                "success": False,
                "error": f"Failed after {max_attempts} attempts: {last_error}",
            }

        return wrapper

    return decorator


def cache_result(cache_instance: Optional["TestCache"] = None):  # type: ignore # noqa: F821
    """Decorator to cache test results based on tool code hash.

    Usage:
        cache = TestCache()

        @cache_result(cache)
        @mcp_test(tool_name="workspace_tool")
        async def test_list_workspaces(client):
            ...
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            test_name = func.__name__
            tool_name = _test_registry.tests.get(test_name, {}).get("tool_name", "unknown")

            # Check cache
            if cache_instance and cache_instance.should_skip(test_name, tool_name):
                return {"success": True, "cached": True, "skipped": True}

            # Run test
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start

                if cache_instance:
                    status = "passed" if result.get("success", False) else "failed"
                    cache_instance.record(test_name, tool_name, status, duration)

                return result
            except Exception:
                duration = time.time() - start
                if cache_instance:
                    cache_instance.record(test_name, tool_name, "error", duration)
                raise

        return wrapper

    return decorator


def get_test_registry() -> TestRegistry:
    """
    Get the global test registry.
    """
    return _test_registry
