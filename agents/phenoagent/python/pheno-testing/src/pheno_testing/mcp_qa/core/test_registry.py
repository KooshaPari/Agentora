"""
Test Registry - Unified Test Discovery and Registration

Combines best features from both Zen and Atoms frameworks:
- Decorator-based registration (@mcp_test)
- Category filtering and priority ordering
- Authentication requirements tracking
- Timeout configuration
- Conditional skipping support
"""

import asyncio
import functools
from typing import Any, Callable, Dict, List, Optional


class TestRegistry:
    """Centralized registry for test discovery via decorators.

    Features:
    - Test metadata storage (category, priority, timeout)
    - Category-based filtering
    - Priority-based ordering
    - Authentication requirements
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
        tags: Optional[List[str]] = None,
    ):
        """Register a test function with metadata.

        Args:
            name: Unique test identifier (usually function name)
            func: Test function (async callable)
            tool_name: MCP tool being tested
            category: Test category (core, integration, etc.)
            priority: Execution priority (higher = earlier)
            requires_auth: Whether test needs authentication
            timeout_seconds: Test timeout limit
            tags: Optional tags for filtering
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
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Get tests, optionally filtered by category or tags.

        Args:
            category: Filter by category (e.g., "core", "integration")
            tags: Filter by tags (test must have ALL specified tags)

        Returns:
            Dictionary of test_name -> test_metadata
        """
        tests = self.tests

        # Filter by category
        if category:
            tests = {k: v for k, v in tests.items() if v["category"] == category}

        # Filter by tags (AND logic - test must have all tags)
        if tags:
            tests = {
                k: v for k, v in tests.items() if all(tag in v.get("tags", []) for tag in tags)
            }

        return tests

    def get_by_priority(self, category: Optional[str] = None) -> List[tuple[str, Dict[str, Any]]]:
        """Get tests sorted by priority (highest first).

        Args:
            category: Optional category filter

        Returns:
            List of (test_name, metadata) tuples sorted by priority
        """
        tests = self.get_tests(category)
        return sorted(tests.items(), key=lambda x: x[1]["priority"], reverse=True)

    def clear(self):
        """
        Clear all registered tests (useful for testing).
        """
        self.tests.clear()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics.
        """
        categories = {}
        for test_info in self.tests.values():
            cat = test_info["category"]
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "total_tests": len(self.tests),
            "categories": categories,
            "tests_requiring_auth": sum(1 for t in self.tests.values() if t["requires_auth"]),
        }


# Global registry instance
_test_registry = TestRegistry()


def get_test_registry() -> TestRegistry:
    """
    Get the global test registry instance.
    """
    return _test_registry


# ============================================================================
# Decorators
# ============================================================================


def mcp_test(
    tool_name: str,
    category: str = "functional",
    priority: int = 5,
    timeout_seconds: int = 30,
    tags: Optional[List[str]] = None,
):
    """Decorator to register an MCP test.

    Usage:
        @mcp_test(tool_name="chat", category="core", priority=10)
        async def test_chat_basic(client):
            result = await client.call_tool("chat", {"prompt": "test"})
            assert result["success"]

    Args:
        tool_name: MCP tool being tested
        category: Test category (core, integration, etc.)
        priority: Execution priority (higher runs first)
        timeout_seconds: Test timeout limit
        tags: Optional tags for filtering
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
        @mcp_test(tool_name="chat")
        async def test_chat_basic(client):
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
        @mcp_test(tool_name="database")
        async def test_database(client):
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
        @mcp_test(tool_name="longrunning")
        async def test_long_operation(client):
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
        @mcp_test(tool_name="flaky_tool")
        async def test_flaky(client):
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
