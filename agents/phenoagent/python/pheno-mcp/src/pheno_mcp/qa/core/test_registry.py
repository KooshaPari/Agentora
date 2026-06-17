"""Test registry for the MCP QA toolkit.

This is a direct lift of the decorator-based registry that previously lived in
the standalone ``mcp_qa`` project.  It provides a small amount of structure so
projects can register asynchronous tests with metadata and later retrieve them
in priority order.
"""

from __future__ import annotations

import asyncio
import functools
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


class TestRegistry:
    """
    Centralised registry for decorator-based test discovery.
    """

    def __init__(self) -> None:
        self.tests: dict[str, dict[str, Any]] = {}

    def register(
        self,
        name: str,
        func: Callable[..., Any],
        *,
        tool_name: str,
        category: str = "functional",
        priority: int = 5,
        requires_auth: bool = False,
        timeout_seconds: int = 30,
        tags: list[str] | None = None,
    ) -> None:
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
        category: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, dict[str, Any]]:
        tests = self.tests
        if category:
            tests = {name: meta for name, meta in tests.items() if meta["category"] == category}
        if tags:
            tests = {
                name: meta
                for name, meta in tests.items()
                if all(tag in meta.get("tags", []) for tag in tags)
            }
        return tests

    def get_by_priority(self, category: str | None = None) -> list[tuple[str, dict[str, Any]]]:
        tests = self.get_tests(category)
        return sorted(tests.items(), key=lambda item: item[1]["priority"], reverse=True)

    def clear(self) -> None:
        self.tests.clear()

    def get_stats(self) -> dict[str, Any]:
        categories: dict[str, int] = {}
        for meta in self.tests.values():
            cat = meta["category"]
            categories[cat] = categories.get(cat, 0) + 1
        return {
            "total_tests": len(self.tests),
            "categories": categories,
            "tests_requiring_auth": sum(1 for meta in self.tests.values() if meta["requires_auth"]),
        }


_registry = TestRegistry()


def get_test_registry() -> TestRegistry:
    return _registry


def mcp_test(
    *,
    tool_name: str,
    category: str = "functional",
    priority: int = 5,
    timeout_seconds: int = 30,
    tags: list[str] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        _registry.register(
            func.__name__,
            func,
            tool_name=tool_name,
            category=category,
            priority=priority,
            timeout_seconds=timeout_seconds,
            tags=tags,
        )

        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                return await func(*args, **kwargs)

            return async_wrapper

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        return wrapper

    return decorator


def require_auth(func: Callable[..., Any]) -> Callable[..., Any]:
    entry = _registry.tests.get(func.__name__)
    if entry:
        entry["requires_auth"] = True

    if asyncio.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        return async_wrapper

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)

    return wrapper


__all__ = [
    "TestRegistry",
    "get_test_registry",
    "mcp_test",
    "require_auth",
]
