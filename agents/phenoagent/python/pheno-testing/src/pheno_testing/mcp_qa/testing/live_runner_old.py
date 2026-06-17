"""Live Test Runner with Real-time Callbacks.

Extends TestRunner with event emission for TUI integration.
"""

import asyncio
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .runner import TestRunner


class LiveTestRunner(TestRunner):
    """
    Test runner with real-time event callbacks for TUI.
    """

    def __init__(
        self,
        *args,
        on_test_start: Optional[Callable] = None,
        on_test_complete: Optional[Callable] = None,
        on_suite_start: Optional[Callable] = None,
        on_suite_complete: Optional[Callable] = None,
        **kwargs,
    ):
        """Initialize live test runner.

        Args:
            on_test_start: Callback(test_name, tool_name) when test starts
            on_test_complete: Callback(test_name, result) when test completes
            on_suite_start: Callback(total_tests) when suite starts
            on_suite_complete: Callback(summary) when suite completes
        """
        super().__init__(*args, **kwargs)
        self.on_test_start = on_test_start or (lambda *args: None)
        self.on_test_complete = on_test_complete or (lambda *args: None)
        self.on_suite_start = on_suite_start or (lambda *args: None)
        self.on_suite_complete = on_suite_complete or (lambda *args: None)

    async def run_all(self, categories: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run all tests with live callbacks.
        """
        self.start_time = datetime.now()
        self.results = []

        # Get tests
        if categories:
            tests_to_run = {}
            for cat in categories:
                tests_to_run.update(self.test_registry.get_tests(cat))
        else:
            tests_to_run = self.test_registry.get_tests()

        # Emit suite start
        self.on_suite_start(len(tests_to_run))

        # Group by category
        by_category: Dict[str, List] = {}
        for test_name, test_info in tests_to_run.items():
            category = test_info["category"]
            by_category.setdefault(category, []).append((test_name, test_info))

        # Run tests
        for category, tests in sorted(by_category.items()):
            if self.parallel:
                tasks = [
                    self._run_single_test_live(test_name, test_info)
                    for test_name, test_info in tests
                ]
                await asyncio.gather(*tasks)
            else:
                for test_name, test_info in tests:
                    await self._run_single_test_live(test_name, test_info)

        self.end_time = datetime.now()

        # Generate reports
        metadata = {
            "endpoint": self.client_adapter.endpoint,
            "auth_status": "authenticated",
            "duration_seconds": (self.end_time - self.start_time).total_seconds(),
        }

        for reporter in self.reporters:
            reporter.report(self.results, metadata)

        # Calculate summary
        summary = {
            "total": len(self.results),
            "passed": sum(1 for r in self.results if r.get("success") and not r.get("skipped")),
            "failed": sum(1 for r in self.results if not r.get("success") and not r.get("skipped")),
            "skipped": sum(1 for r in self.results if r.get("skipped")),
            "cached": sum(1 for r in self.results if r.get("cached")),
            "duration_seconds": (self.end_time - self.start_time).total_seconds(),
            "results": self.results,
        }

        # Emit suite complete
        self.on_suite_complete(summary)

        return summary

    async def _run_single_test_live(self, test_name: str, test_info: Dict[str, Any]) -> None:
        """
        Run single test with live callbacks.
        """
        tool_name = test_info["tool_name"]

        # Emit test start
        self.on_test_start(test_name, tool_name)

        # Check cache
        if self.cache_instance and self.cache_instance.should_skip(test_name, tool_name):
            result = {
                "test_name": test_name,
                "tool_name": tool_name,
                "success": True,
                "cached": True,
                "skipped": False,
                "duration_ms": 0,
                "error": None,
            }
            self.results.append(result)
            self.on_test_complete(test_name, result)
            return

        # Run test (same as parent but with callback)
        import time

        start = time.time()

        try:
            test_func = test_info["func"]
            test_result = await test_func(self.client_adapter)

            duration_ms = (time.time() - start) * 1000

            if isinstance(test_result, dict):
                success = test_result.get("success", False)
                error = test_result.get("error")
                skipped = test_result.get("skipped", False)
            else:
                success = bool(test_result)
                error = None
                skipped = False

            result = {
                "test_name": test_name,
                "tool_name": tool_name,
                "success": success,
                "cached": False,
                "skipped": skipped,
                "duration_ms": duration_ms,
                "error": error,
            }

            if self.cache_instance and not skipped:
                status = "passed" if success else "failed"
                self.cache_instance.record(test_name, tool_name, status, duration_ms / 1000, error)

            self.results.append(result)
            self.on_test_complete(test_name, result)

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            error = str(e)

            result = {
                "test_name": test_name,
                "tool_name": tool_name,
                "success": False,
                "cached": False,
                "skipped": False,
                "duration_ms": duration_ms,
                "error": error,
            }

            if self.cache_instance:
                self.cache_instance.record(test_name, tool_name, "error", duration_ms / 1000, error)

            self.results.append(result)
            self.on_test_complete(test_name, result)
