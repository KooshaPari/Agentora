"""Simplified base test runner for MCP QA suites.

This implementation focuses on providing a pragmatic async execution loop that works
well for the in-tree tests.  It intentionally keeps the contract small while leaving
room for future enhancements such as richer progress reporting or connection pooling.
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from ...reporters import ConsoleReporter, TestReporter
from ..cache import TestCache
from ..test_registry import get_test_registry

if TYPE_CHECKING:
    from collections.abc import Iterable


class BaseTestRunner(ABC):
    """
    Executes registered MCP QA tests.
    """

    def __init__(
        self,
        client_adapter: Any,
        *,
        cache: bool = True,
        reporters: Iterable[TestReporter] | None = None,
    ) -> None:
        self.client_adapter = client_adapter
        self.cache = TestCache() if cache else None
        self.reporters = list(reporters or [ConsoleReporter()])
        self.registry = get_test_registry()

    async def run_all(self, categories: list[str] | None = None) -> dict[str, Any]:
        tests = self._select_tests(categories)
        results: list[dict[str, Any]] = []
        start = time.perf_counter()

        for name, meta in tests:
            result = await self._run_single(name, meta)
            results.append(result)

        duration = time.perf_counter() - start
        summary = self._summarise(results, duration)

        metadata = dict(self._get_metadata())
        metadata.setdefault("duration_seconds", duration)
        for reporter in self.reporters:
            try:
                reporter.report(results, metadata)
            except Exception:
                # Reporters are auxiliary; a failure should not abort the run.
                continue

        return summary

    # ---------------------------------------------------------------- helpers
    def _select_tests(self, categories: list[str] | None) -> list[tuple[str, dict[str, Any]]]:
        if categories:
            selected: dict[str, dict[str, Any]] = {}
            for category in categories:
                selected.update(self.registry.get_tests(category))
        else:
            selected = self.registry.get_tests()
        # Preserve registration order but honour priority
        return sorted(selected.items(), key=lambda item: item[1]["priority"], reverse=True)

    async def _run_single(self, name: str, meta: dict[str, Any]) -> dict[str, Any]:
        tool = meta.get("tool_name", "")
        timeout = meta.get("timeout_seconds", 30)

        if self.cache and self.cache.should_skip(name, tool):
            return {
                "test_name": name,
                "tool_name": tool,
                "success": True,
                "cached": True,
                "skipped": True,
                "duration_ms": 0.0,
            }

        func = meta["func"]
        start = time.perf_counter()
        try:
            await asyncio.wait_for(func(self.client_adapter), timeout=timeout)
            duration = (time.perf_counter() - start) * 1000
            result = {
                "test_name": name,
                "tool_name": tool,
                "success": True,
                "cached": False,
                "skipped": False,
                "duration_ms": duration,
            }
            if self.cache:
                self.cache.record(name, tool, "passed", duration / 1000)
            return result
        except TimeoutError:
            duration = (time.perf_counter() - start) * 1000
            if self.cache:
                self.cache.record(name, tool, "timeout", duration / 1000, "timeout")
            return {
                "test_name": name,
                "tool_name": tool,
                "success": False,
                "cached": False,
                "skipped": False,
                "duration_ms": duration,
                "error": f"Test timeout after {timeout}s",
            }
        except Exception as exc:
            duration = (time.perf_counter() - start) * 1000
            if self.cache:
                self.cache.record(name, tool, "failed", duration / 1000, str(exc))
            return {
                "test_name": name,
                "tool_name": tool,
                "success": False,
                "cached": False,
                "skipped": False,
                "duration_ms": duration,
                "error": str(exc),
            }

    def _summarise(self, results: list[dict[str, Any]], duration: float) -> dict[str, Any]:
        passed = sum(1 for r in results if r["success"] and not r["skipped"])
        failed = sum(1 for r in results if not r["success"] and not r["skipped"])
        skipped = sum(1 for r in results if r["skipped"])
        cached = sum(1 for r in results if r.get("cached"))
        return {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "cached": cached,
            "duration_seconds": duration,
            "results": results,
        }

    # ---------------------------------------------------------------- abstract
    @abstractmethod
    def _get_metadata(self) -> dict[str, Any]:
        """
        Projects provide run-specific metadata for reporting.
        """


__all__ = ["BaseTestRunner"]
