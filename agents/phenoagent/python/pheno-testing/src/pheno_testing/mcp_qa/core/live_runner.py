"""
Live Test Runner - Event-Driven Test Execution for TUI Integration

Combines best features from both Zen and Atoms frameworks:
- Real-time event callbacks
- Progress notifications
- Suite lifecycle hooks
- Supports both parallel and sequential modes
"""

import asyncio
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .base.test_runner import BaseTestRunner as TestRunner


class LiveTestRunner(TestRunner):
    """Test runner with real-time event callbacks for TUI integration.

    Events:
    - on_suite_start(total_tests): When test suite begins
    - on_suite_complete(summary): When test suite finishes
    - on_test_start(test_name, tool_name): When individual test starts
    - on_test_complete(test_name, result): When individual test completes
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
        """Initialize live test runner with event callbacks.

        Args:
            on_test_start: Callback(test_name, tool_name) when test starts
            on_test_complete: Callback(test_name, result) when test completes
            on_suite_start: Callback(total_tests) when suite starts
            on_suite_complete: Callback(summary) when suite completes
            *args, **kwargs: Passed to TestRunner
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

        # Initialize semaphore for parallel execution
        if self.parallel:
            self._semaphore = asyncio.Semaphore(self.parallel_workers)

        # Get tests
        if categories:
            tests_to_run = {}
            for cat in categories:
                tests_to_run.update(self.test_registry.get_tests(cat))
        else:
            tests_to_run = self.test_registry.get_tests()

        # Emit suite start
        self.on_suite_start(len(tests_to_run))

        if not tests_to_run:
            summary = self._empty_summary()
            self.on_suite_complete(summary)
            return summary

        # Group by category
        by_category: Dict[str, List] = {}
        for test_name, test_info in tests_to_run.items():
            category = test_info["category"]
            by_category.setdefault(category, []).append((test_name, test_info))

        # Run tests with callbacks
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
            "duration_seconds": (self.end_time - self.start_time).total_seconds(),
        }

        for reporter in self.reporters:
            reporter.report(self.results, metadata)

        # Calculate summary
        summary = self._generate_summary()

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

        # Check cache (simplified)
        if self.cache_instance:
            cached_result = self.cache_instance.cache.get(test_name, {})
            if cached_result.get("status") == "passed":
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

        # Run test
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
                self.cache_instance.cache[test_name] = {
                    "status": status,
                    "timestamp": time.time(),
                    "tool_name": tool_name,
                }

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
                self.cache_instance.cache[test_name] = {
                    "status": "error",
                    "timestamp": time.time(),
                    "tool_name": tool_name,
                }

            self.results.append(result)
            self.on_test_complete(test_name, result)
