"""
Test Runner - Unified Test Execution Engine

Combines best features from both Zen and Atoms frameworks:
- Parallel and sequential execution
- Worker isolation and concurrency control
- Progress tracking (tqdm integration)
- Cache integration
- Reporter coordination
- Thread-safe result aggregation
- Worker statistics
"""

import asyncio
import os
import sys
import threading
import time
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

try:
    from tqdm import tqdm

    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

from .adapters import MCPClientAdapter
from .cache import TestCache
from .test_registry import get_test_registry


class TestRunner:
    """Orchestrates test execution with caching, parallel execution, and reporting.

    Features:
    - Parallel/sequential execution modes
    - Worker isolation with dedicated environments
    - Semaphore-based concurrency control
    - Progress tracking (tqdm)
    - Result aggregation
    - Cache integration
    - Auto-detection of optimal worker count
    """

    def __init__(
        self,
        client_adapter: MCPClientAdapter,
        cache: bool = True,
        parallel: bool = False,
        parallel_workers: Optional[int] = None,
        reporters: Optional[List[Any]] = None,
    ):
        """Initialize test runner.

        Args:
            client_adapter: MCP client adapter
            cache: Enable test caching
            parallel: Enable parallel execution
            parallel_workers: Number of parallel workers (auto-detect if None)
            reporters: List of test reporters
        """
        self.client_adapter = client_adapter
        self.use_cache = cache
        self.parallel = parallel

        # Auto-detect optimal workers if not specified
        if parallel_workers is None and parallel:
            parallel_workers = min(os.cpu_count() or 4, 8)  # Cap at 8 workers

        self.parallel_workers = max(1, parallel_workers or 4)
        self.cache_instance = TestCache() if cache else None
        self.reporters = reporters or []
        self.test_registry = get_test_registry()
        self.results: List[Dict[str, Any]] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

        # Worker management for parallel execution
        self._worker_lock = threading.Lock()
        self._active_workers: Set[int] = set()
        self._worker_errors: Dict[int, List[str]] = {}
        self._results_lock = threading.Lock()  # Thread-safe result aggregation
        self._semaphore: Optional[asyncio.Semaphore] = None  # Concurrency control
        self._worker_envs: Dict[int, Dict[str, str]] = {}  # Worker-specific environments

    def _get_worker_id(self) -> int:
        """
        Get unique worker ID for the current thread/task.
        """
        try:
            # Try to get asyncio task name (if running in async context)
            task = asyncio.current_task()
            if task:
                return hash(task) % 10000
        except RuntimeError:
            pass

        # Fall back to thread ID
        return threading.get_ident() % 10000

    def _setup_worker_environment(self, worker_id: int) -> None:
        """
        Set up worker-specific environment isolation.
        """
        with self._worker_lock:
            if worker_id not in self._worker_envs:
                self._worker_envs[worker_id] = {
                    "TEST_WORKER_ID": str(worker_id),
                    "TEST_WORKER_TEMP": f"/tmp/test_worker_{worker_id}",
                }
                self._active_workers.add(worker_id)
                self._worker_errors[worker_id] = []

                # Apply environment variables
                for key, value in self._worker_envs[worker_id].items():
                    os.environ[f"{key}_{worker_id}"] = value

    def _cleanup_worker_environment(self, worker_id: int) -> None:
        """
        Clean up worker-specific environment.
        """
        with self._worker_lock:
            if worker_id in self._worker_envs:
                # Remove worker-specific environment variables
                for key in self._worker_envs[worker_id].keys():
                    os.environ.pop(f"{key}_{worker_id}", None)

                self._active_workers.discard(worker_id)
                del self._worker_envs[worker_id]

    async def run_all(self, categories: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run all registered tests.

        Args:
            categories: Optional list of categories to run

        Returns:
            {
                "total": int,
                "passed": int,
                "failed": int,
                "skipped": int,
                "cached": int,
                "duration_seconds": float,
                "results": List[Dict],
                "worker_stats": Dict (if parallel mode)
            }
        """
        self.start_time = datetime.now()
        self.results = []

        # Initialize semaphore for parallel execution
        if self.parallel:
            self._semaphore = asyncio.Semaphore(self.parallel_workers)

        # Get tests to run
        if categories:
            tests_to_run = {}
            for cat in categories:
                tests_to_run.update(self.test_registry.get_tests(cat))
        else:
            tests_to_run = self.test_registry.get_tests()

        if not tests_to_run:
            print("No tests found")
            return self._empty_summary()

        # Group tests by category
        by_category: Dict[str, List] = {}
        for test_name, test_info in tests_to_run.items():
            category = test_info["category"]
            by_category.setdefault(category, []).append((test_name, test_info))

        total_tests = len(tests_to_run)

        # Display execution info
        if self.parallel:
            print(f"Parallel execution enabled: {self.parallel_workers} workers")

        # Setup progress bar
        pbar = None
        if HAS_TQDM:
            pbar = tqdm(
                total=total_tests,
                desc="Running tests",
                unit="test",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
            )

        try:
            # Run tests
            for category, tests in sorted(by_category.items()):
                if pbar:
                    pbar.write(f"\n{category.upper()} Tests")
                else:
                    print(f"\n{category.upper()} Tests")

                if self.parallel and len(tests) > 1:
                    # Parallel execution
                    print(
                        f"   Running {len(tests)} tests in parallel across {self.parallel_workers} workers..."
                    )
                    tasks = [
                        self._run_single_test_with_worker(test_name, test_info, pbar)
                        for test_name, test_info in tests
                    ]
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # Log any worker exceptions
                    for i, result in enumerate(results):
                        if isinstance(result, Exception):
                            test_name, test_info = tests[i]
                            error_msg = str(result)
                            if pbar:
                                pbar.write(f"Worker failed: {test_name} - {error_msg[:50]}")
                            else:
                                print(f"Worker failed: {test_name} - {error_msg[:50]}")
                else:
                    # Sequential execution
                    for test_name, test_info in tests:
                        await self._run_single_test(test_name, test_info, pbar)

        finally:
            if pbar:
                pbar.close()

            # Cleanup all worker environments
            for worker_id in list(self._active_workers):
                self._cleanup_worker_environment(worker_id)

        self.end_time = datetime.now()

        # Generate reports
        metadata = {
            "endpoint": self.client_adapter.endpoint,
            "duration_seconds": (self.end_time - self.start_time).total_seconds(),
            "parallel_mode": self.parallel,
            "parallel_workers": self.parallel_workers if self.parallel else 1,
        }

        for reporter in self.reporters:
            reporter.report(self.results, metadata)

        # Return summary
        return self._generate_summary()

    async def _run_single_test_with_worker(
        self,
        test_name: str,
        test_info: Dict[str, Any],
        pbar: Optional[Any] = None,
    ) -> None:
        """
        Run a single test with worker isolation and concurrency control.
        """
        async with self._semaphore:
            worker_id = self._get_worker_id()
            self._setup_worker_environment(worker_id)

            try:
                await self._run_single_test(test_name, test_info, pbar, worker_id=worker_id)
            except Exception as e:
                error_msg = f"Test {test_name} failed in worker {worker_id}: {str(e)}"
                with self._worker_lock:
                    self._worker_errors[worker_id].append(error_msg)
                raise

    async def _run_single_test(
        self,
        test_name: str,
        test_info: Dict[str, Any],
        pbar: Optional[Any] = None,
        worker_id: Optional[int] = None,
    ) -> None:
        """
        Run a single test with caching, timing, and error handling.
        """
        test_func = test_info["func"]
        tool_name = test_info["tool_name"]

        # Check cache (simplified - full hash checking done by cache)
        if self.cache_instance:
            # For now, use simple check - proper hash checking would need tool paths
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
                    "worker_id": worker_id,
                }

                with self._results_lock:
                    self.results.append(result)

                if pbar:
                    pbar.update(1)
                return

        # Run test
        start = time.time()

        try:
            test_result = await test_func(self.client_adapter)
            duration_ms = (time.time() - start) * 1000

            # Parse result
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
                "worker_id": worker_id,
            }

            # Update cache
            if self.cache_instance and not skipped:
                status = "passed" if success else "failed"
                # Simplified recording - proper implementation would compute hashes
                self.cache_instance.cache[test_name] = {
                    "status": status,
                    "timestamp": time.time(),
                    "tool_name": tool_name,
                }

            with self._results_lock:
                self.results.append(result)

            # Output only failures
            if pbar:
                pbar.update(1)
                if not success and not skipped:
                    print(f"FAILED: {test_name} ({duration_ms:.2f}ms)")
            elif not success and not skipped:
                print(f"FAILED: {test_name} ({duration_ms:.2f}ms)")

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            error = str(e)

            # Capture detailed error information
            exc_type, exc_value, exc_tb = sys.exc_info()
            tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))

            result = {
                "test_name": test_name,
                "tool_name": tool_name,
                "success": False,
                "cached": False,
                "skipped": False,
                "duration_ms": duration_ms,
                "error": error,
                "traceback": tb_str,
                "worker_id": worker_id,
            }

            if self.cache_instance:
                self.cache_instance.cache[test_name] = {
                    "status": "error",
                    "timestamp": time.time(),
                    "tool_name": tool_name,
                }

            with self._results_lock:
                self.results.append(result)

            worker_tag = f" [W{worker_id}]" if worker_id is not None else ""
            if pbar:
                pbar.update(1)
                pbar.write(f"ERROR: {test_name} - {error[:50]}{worker_tag}")
            else:
                print(f"ERROR: {test_name} - {error[:50]}{worker_tag}")

    def _empty_summary(self) -> Dict[str, Any]:
        """
        Return empty summary.
        """
        return {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "cached": 0,
            "duration_seconds": 0,
            "results": [],
        }

    def _generate_summary(self) -> Dict[str, Any]:
        """
        Generate test run summary.
        """
        passed = sum(1 for r in self.results if r.get("success") and not r.get("skipped"))
        failed = sum(1 for r in self.results if not r.get("success") and not r.get("skipped"))
        skipped = sum(1 for r in self.results if r.get("skipped"))
        cached = sum(1 for r in self.results if r.get("cached"))

        summary = {
            "total": len(self.results),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "cached": cached,
            "duration_seconds": (self.end_time - self.start_time).total_seconds(),
            "results": self.results,
        }

        # Add worker statistics for parallel runs
        if self.parallel:
            summary["worker_stats"] = {
                "workers_used": len(self._worker_errors),
                "worker_errors": {wid: len(errs) for wid, errs in self._worker_errors.items()},
            }

        return summary
