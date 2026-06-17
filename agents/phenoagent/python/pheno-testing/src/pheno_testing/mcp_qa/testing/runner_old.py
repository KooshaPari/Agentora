"""
Test Runner - Orchestrates Test Execution

Provides:
- Parallel/sequential execution with worker isolation
- Progress tracking (tqdm)
- Cache integration
- Reporter coordination
- Auto-discovery via decorators
- Detailed error capturing for debugging
- Configurable concurrency limits (e.g., max_workers=10)
- Worker-specific environment isolation
- Thread-safe test execution with asyncio.gather()
- Semaphore for concurrency control
- Worker ID assignment for debugging
- Progress tracking across workers
- Error isolation (one worker failure doesn't crash all)
- Result aggregation from parallel runs
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

# AtomsMCPClientAdapter is project-specific - use BaseClientAdapter instead
# from .adapters import AtomsMCPClientAdapter
from .cache import TestCache
from .decorators import get_test_registry
from .reporters import ConsoleReporter, TestReporter


class TestRunner:
    """
    Orchestrates test execution with caching, parallel execution, and reporting.
    """

    def __init__(
        self,
        client_adapter: AtomsMCPClientAdapter,
        cache: bool = True,
        parallel: bool = False,
        parallel_workers: int = None,  # Auto-detect if None
        reporters: Optional[List[TestReporter]] = None,
        use_optimizations: bool = True,  # Enable connection pooling, etc.
    ):
        self.client_adapter = client_adapter
        self.use_cache = cache
        self.parallel = parallel
        self.use_optimizations = use_optimizations

        # Auto-detect optimal workers if not specified
        if parallel_workers is None and parallel:
            try:
                from .optimizations import ConcurrencyOptimizer

                parallel_workers = ConcurrencyOptimizer.get_optimal_workers()
                print(f"🔧 Auto-detected optimal workers: {parallel_workers}")
            except ImportError:
                parallel_workers = 4

        self.parallel_workers = max(1, parallel_workers or 4)
        self.cache_instance = TestCache() if cache else None
        self.reporters = reporters or [ConsoleReporter()]
        self.test_registry = get_test_registry()
        self.results: List[Dict[str, Any]] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

        # Connection pooling
        self.connection_pool = None
        self.response_cache = None

        # Initialize optimizations
        if use_optimizations:
            try:
                from .optimizations import PooledMCPClient, ResponseCacheLayer

                # Will be initialized when tests start
                self._pool_class = PooledMCPClient
                self._cache_class = ResponseCacheLayer
            except ImportError:
                pass

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
                # Create worker-specific environment variables
                self._worker_envs[worker_id] = {
                    "TEST_WORKER_ID": str(worker_id),
                    "TEST_WORKER_TEMP": f"/tmp/test_worker_{worker_id}",
                }
                self._active_workers.add(worker_id)
                self._worker_errors[worker_id] = []

                # Apply environment variables (thread-local)
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

    async def _initialize_connection_pool(self):
        """
        Initialize connection pool for parallel execution.
        """
        if not self.parallel or not self.use_optimizations:
            return

        try:
            from .optimizations import PooledMCPClient, ResponseCacheLayer

            # Create connection pool with base client
            self.connection_pool = PooledMCPClient(
                base_client=self.client_adapter.client,
                min_connections=self.parallel_workers,
                max_connections=self.parallel_workers * 2,
            )

            await self.connection_pool.initialize()

            # Initialize response cache
            self.response_cache = ResponseCacheLayer(max_size=1000, default_ttl=60)

            print("✅ Performance optimizations active")
            print(
                f"   Connection pool: {self.parallel_workers}-{self.parallel_workers * 2} clients"
            )
            print("   Response cache: LRU (1000 entries, 60s TTL)")

        except Exception as e:
            print(f"⚠️  Connection pool initialization failed: {e}")
            print("   Falling back to single client (will be slower)")

    async def run_all(self, categories: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run all registered tests.

        Args:
            categories: Optional list of categories to run (e.g., ["core", "entity"])

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

        # Initialize connection pool FIRST for parallel execution
        if self.parallel:
            await self._initialize_connection_pool()
            self._semaphore = asyncio.Semaphore(self.parallel_workers)

        # Get tests to run
        if categories:
            tests_to_run = {}
            for cat in categories:
                tests_to_run.update(self.test_registry.get_tests(cat))
        else:
            tests_to_run = self.test_registry.get_tests()

        if not tests_to_run:
            print("⚠️  No tests found")
            return {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "cached": 0,
                "duration_seconds": 0,
                "results": [],
            }

        # Group tests by category
        by_category: Dict[str, List] = {}
        for test_name, test_info in tests_to_run.items():
            category = test_info["category"]
            by_category.setdefault(category, []).append((test_name, test_info))

        # Sort categories by priority
        category_order = ["core", "entity", "query", "relationship", "workflow", "integration"]
        sorted_categories = sorted(
            by_category.items(),
            key=lambda x: category_order.index(x[0]) if x[0] in category_order else 999,
        )

        total_tests = len(tests_to_run)

        # Display parallel execution info
        if self.parallel:
            print(f"🔄 Parallel execution enabled: {self.parallel_workers} workers")

        # Use enhanced progress display
        try:
            from .progress_display import ComprehensiveProgressDisplay

            progress_display = ComprehensiveProgressDisplay(
                total_tests=total_tests,
                categories=list(by_category.keys()),
                parallel=self.parallel,
                workers=self.parallel_workers,
            )
            use_enhanced_progress = True
        except ImportError:
            use_enhanced_progress = False
            # Fallback to tqdm
            if HAS_TQDM:
                pbar = tqdm(
                    total=total_tests,
                    desc="Running tests",
                    unit="test",
                    bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
                )
            else:
                pbar = None

        try:
            # Start enhanced progress display
            if use_enhanced_progress:
                with progress_display as prog:
                    # Set category totals
                    for category, tests in by_category.items():
                        prog.set_category_total(category, len(tests))

                    # Run tests
                    await self._run_with_enhanced_progress(sorted_categories, prog)
            else:
                # Use tqdm or basic output
                await self._run_with_basic_progress(sorted_categories, pbar)

        finally:
            if not use_enhanced_progress and pbar:
                pbar.close()

    async def _run_with_enhanced_progress(self, sorted_categories, progress_display):
        """
        Run tests with enhanced progress display.
        """
        for category, tests in sorted_categories:
            progress_display.write(f"\n📋 {category.upper()} Tests")

            if self.parallel:
                # Parallel execution
                tasks = [
                    self._run_single_test_with_worker_enhanced(
                        test_name, test_info, category, progress_display
                    )
                    for test_name, test_info in tests
                ]
                await asyncio.gather(*tasks, return_exceptions=True)
            else:
                # Sequential execution
                for test_name, test_info in tests:
                    await self._run_single_test_enhanced(
                        test_name, test_info, category, progress_display
                    )

    async def _run_with_basic_progress(self, sorted_categories, pbar):
        """
        Run tests with basic tqdm progress.
        """
        try:
            for category, tests in sorted_categories:
                if pbar:
                    pbar.write(f"\n📋 {category.upper()} Tests")
                else:
                    print(f"\n📋 {category.upper()} Tests")

                # ALWAYS use parallel execution for speed
                if self.parallel and len(tests) > 1:
                    # Parallel execution with worker pool
                    print(
                        f"   🔄 Running {len(tests)} tests in parallel across {self.parallel_workers} workers..."
                    )

                    tasks = [
                        self._run_single_test_with_worker(test_name, test_info, pbar)
                        for test_name, test_info in tests
                    ]

                    # Execute all tests in parallel
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # Log any worker exceptions
                    for i, result in enumerate(results):
                        if isinstance(result, Exception):
                            test_name, test_info = tests[i]
                            error_msg = str(result)

                            # Check if it's a lock error or connection issue
                            if (
                                "not holding this lock" in error_msg
                                or "RuntimeError" in str(type(result))
                                or "530" in error_msg
                                or "502" in error_msg
                            ):
                                print("\n⚠️  Connection/lock issue detected in worker")
                                print("   Treating as connection loss - cache invalidated")

                                # Clear cache
                                if self.cache_instance:
                                    self.cache_instance.clear()

                                if pbar:
                                    pbar.write(
                                        f"⚠️  {test_name} - Connection issue (will retry next run)"
                                    )
                                else:
                                    print(
                                        f"⚠️  {test_name} - Connection issue (will retry next run)"
                                    )
                            else:
                                if pbar:
                                    pbar.write(f"❌ {test_name} - Worker failed: {error_msg[:50]}")
                                else:
                                    print(f"❌ {test_name} - Worker failed: {error_msg[:50]}")
                else:
                    # Sequential fallback for single test or if parallel disabled
                    for test_name, test_info in tests:
                        await self._run_single_test(test_name, test_info, pbar)

        finally:
            if pbar:
                pbar.close()

            # Cleanup all worker environments
            for worker_id in list(self._active_workers):
                self._cleanup_worker_environment(worker_id)

    async def _run_single_test_enhanced(
        self, test_name: str, test_info: Dict[str, Any], category: str, progress_display
    ):
        """
        Run single test with enhanced progress display.
        """
        tool_name = test_info["tool_name"]

        # Run test (reuse existing logic)
        await self._run_single_test(test_name, test_info, None)

        # Get last result
        if self.results:
            result = self.results[-1]
            progress_display.update(
                test_name=test_name,
                tool_name=tool_name,
                category=category,
                success=result.get("success", False),
                duration_ms=result.get("duration_ms", 0),
                cached=result.get("cached", False),
                skipped=result.get("skipped", False),
            )

    async def _run_single_test_with_worker_enhanced(
        self, test_name: str, test_info: Dict[str, Any], category: str, progress_display
    ):
        """
        Run single test with worker + enhanced progress.
        """
        # Acquire semaphore
        async with self._semaphore:
            worker_id = self._get_worker_id()
            self._setup_worker_environment(worker_id)

            try:
                await self._run_single_test_enhanced(
                    test_name, test_info, category, progress_display
                )
            except Exception as e:
                with self._worker_lock:
                    self._worker_errors[worker_id].append(str(e))
                raise

        self.end_time = datetime.now()

        # Generate reports
        metadata = {
            "endpoint": self.client_adapter.endpoint,
            "auth_status": "authenticated",
            "duration_seconds": (self.end_time - self.start_time).total_seconds(),
            "parallel_mode": self.parallel,
            "parallel_workers": self.parallel_workers if self.parallel else 1,
        }

        for reporter in self.reporters:
            reporter.report(self.results, metadata)

        # Return summary
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

    async def _run_single_test_with_worker(
        self, test_name: str, test_info: Dict[str, Any], pbar: Optional[Any] = None
    ) -> None:
        """
        Run a single test with worker isolation and dedicated MCP client.
        """
        # Acquire semaphore to limit concurrent execution
        async with self._semaphore:
            # Get worker ID and setup environment
            worker_id = self._get_worker_id()
            self._setup_worker_environment(worker_id)

            # Get dedicated client from ParallelClientManager
            worker_client = None
            if hasattr(self, "client_manager") and self.client_manager:
                try:
                    worker_client = await self.client_manager.acquire(timeout=10.0)
                except Exception as e:
                    print(f"⚠️  Worker {worker_id} couldn't acquire client: {e}")

            try:
                # Create adapter with worker's dedicated client
                if worker_client:
                    # AtomsMCPClientAdapter is project-specific - use BaseClientAdapter instead
                    # from .adapters import AtomsMCPClientAdapter
                    worker_adapter = AtomsMCPClientAdapter(worker_client, verbose_on_fail=True)

                    # Temporarily swap adapter for this test
                    original_adapter = self.client_adapter
                    self.client_adapter = worker_adapter

                    try:
                        await self._run_single_test(test_name, test_info, pbar, worker_id=worker_id)
                    finally:
                        # Restore original adapter
                        self.client_adapter = original_adapter
                else:
                    # Fallback to shared client (sequential mode)
                    await self._run_single_test(test_name, test_info, pbar, worker_id=worker_id)

            except Exception as e:
                # Log worker error
                error_msg = f"Test {test_name} failed in worker {worker_id}: {str(e)}"
                with self._worker_lock:
                    self._worker_errors[worker_id].append(error_msg)
                raise
            finally:
                # Return client to pool
                if worker_client and hasattr(self, "client_manager") and self.client_manager:
                    await self.client_manager.release(worker_client)

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
                "worker_id": worker_id,
            }

            # Thread-safe result aggregation
            with self._results_lock:
                self.results.append(result)

            # Silent for cached tests - just update progress
            if pbar:
                pbar.update(1)
            # No output for cached tests
            return

        # Run test
        start = time.time()

        try:
            # Call test function with client adapter
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
                self.cache_instance.record(test_name, tool_name, status, duration_ms / 1000, error)

            # Thread-safe result aggregation
            with self._results_lock:
                self.results.append(result)

            # Output: ONLY failures, suppress success/skip/cached
            if pbar:
                pbar.update(1)
                if not success and not skipped:  # Only print failures
                    print(f"❌ {test_name} ({duration_ms:.2f}ms)")
            elif not success and not skipped:
                print(f"❌ {test_name} ({duration_ms:.2f}ms)")

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            error = str(e)

            # Capture detailed error information
            exc_type, exc_value, exc_tb = sys.exc_info()
            tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))

            # Try to capture local variables from the test function frame
            locals_data = {}
            if exc_tb:
                frame = exc_tb.tb_frame
                # Get locals from the frame where the exception occurred
                try:
                    locals_data = {
                        k: v
                        for k, v in frame.f_locals.items()
                        if not k.startswith("_") and k != "self"
                    }
                except Exception:
                    pass

            result = {
                "test_name": test_name,
                "tool_name": tool_name,
                "success": False,
                "cached": False,
                "skipped": False,
                "duration_ms": duration_ms,
                "error": error,
                "traceback": tb_str,
                "locals": locals_data,
                "worker_id": worker_id,
            }

            # Try to extract request/response if available from locals
            if "result" in locals_data and isinstance(locals_data["result"], dict):
                result["response"] = locals_data["result"].get("response")

            # Try to extract request parameters
            if "data" in locals_data:
                result["request_params"] = {
                    "entity_type": locals_data.get("entity_type"),
                    "operation": locals_data.get("operation"),
                    "data": locals_data.get("data"),
                }

            if self.cache_instance:
                self.cache_instance.record(test_name, tool_name, "error", duration_ms / 1000, error)

            # Thread-safe result aggregation
            with self._results_lock:
                self.results.append(result)

            worker_tag = f" [W{worker_id}]" if worker_id is not None else ""
            if pbar:
                pbar.update(1)
                pbar.write(f"❌ {test_name} - {error[:50]}{worker_tag}")
            else:
                print(f"❌ {test_name} - {error[:50]}{worker_tag}")
