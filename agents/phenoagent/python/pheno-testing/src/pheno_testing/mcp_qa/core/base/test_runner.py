"""Base Test Runner for MCP Testing.

Abstract base class providing common test execution infrastructure.
Projects extend this to implement project-specific test execution logic.

Provides:
- Parallel/sequential execution with worker isolation
- Progress tracking (tqdm)
- Cache integration
- Reporter coordination
- Auto-discovery via decorators
- Detailed error capturing for debugging
- Configurable concurrency limits
- Worker-specific environment isolation
- Thread-safe test execution with asyncio.gather()
- Semaphore for concurrency control
- Worker ID assignment for debugging
- Progress tracking across workers
- Error isolation (one worker failure doesn't crash all)
- Result aggregation from parallel runs

Example:
    class MyProjectRunner(BaseTestRunner):
        def _get_adapter_class(self):
            return MyProjectClientAdapter

        def _get_metadata(self) -> Dict[str, Any]:
            return {
                "endpoint": self.client_adapter.endpoint,
                "project": "my-project"
            }
"""

import asyncio
import os
import threading
import traceback
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from tqdm import tqdm as _tqdm

    HAS_TQDM = True
except ImportError:
    _tqdm = None  # type: ignore[assignment]
    HAS_TQDM = False

try:
    from pheno.testing.mcp_qa.reporters import ConsoleReporter, TestReporter
    from ..cache import TestCache
    from ..test_registry import get_test_registry
except ImportError:
    from pheno.testing.mcp_qa.core.cache import TestCache
    from pheno.testing.mcp_qa.core.test_registry import get_test_registry
    from pheno.testing.mcp_qa.reporters import ConsoleReporter, TestReporter

from ._worker import WorkerContext
from ._connection import ConnectionPoolManager
from ._progress import ProgressTracker, ComprehensiveProgressDisplay
from ._executor import TestExecutor


class BaseTestRunner(ABC):
    """Abstract base class for MCP test runners.

    Provides common infrastructure for test execution while allowing
    projects to customize specific behaviors.

    Projects must implement:
    - _get_adapter_class(): Return the project's client adapter class
    - _get_metadata(): Return project-specific metadata for reports
    """

    def __init__(
        self,
        client_adapter: Any,
        cache: bool = True,
        parallel: bool = False,
        parallel_workers: Optional[int] = None,
        reporters: Optional[List[TestReporter]] = None,
        use_optimizations: bool = True,
        verbose: bool = False,
    ):
        self.client_adapter = client_adapter
        self.use_cache = cache
        self.parallel = parallel
        self.use_optimizations = use_optimizations
        self.verbose = verbose

        if parallel_workers is None and parallel:
            try:
                parallel_workers = os.cpu_count() or 4
                if verbose:
                    print(f"Auto-detected optimal workers: {parallel_workers}")
            except Exception:
                parallel_workers = 4

        self.parallel_workers = max(1, parallel_workers or 4)
        self.cache_instance = TestCache() if cache else None
        self.reporters = reporters or [ConsoleReporter()]
        self.test_registry = get_test_registry()
        self.results: List[Dict[str, Any]] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

        pool_class = None
        cache_class = None
        if use_optimizations:
            try:
                from ..optimizations import PooledMCPClient, ResponseCacheLayer

                pool_class = PooledMCPClient
                cache_class = ResponseCacheLayer
            except (ImportError, ValueError):
                pass

        self._pool_manager = ConnectionPoolManager(
            pool_class=pool_class,
            cache_class=cache_class,
            parallel=parallel,
            workers=self.parallel_workers,
        )

        self._worker_context = WorkerContext(max_workers=self.parallel_workers)
        self._results_lock = threading.Lock()
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._executor = TestExecutor(
            cache_instance=self.cache_instance,
            reporters=self.reporters,
            results=self.results,
            results_lock=self._results_lock,
            verbose=self.verbose,
        )

    async def _initialize_connection_pool(self) -> None:
        """Initialize connection pool for parallel execution."""
        base_url = self._extract_base_url()
        await self._pool_manager.initialize(base_url)

    @property
    def connection_pool(self):
        return self._pool_manager.connection_pool

    @property
    def response_cache(self):
        return self._pool_manager.response_cache

    def _extract_base_url(self) -> str:
        """Extract base URL from client (overridable by projects)."""
        client = self.client_adapter.client
        if hasattr(client, "mcp_url"):
            return client.mcp_url
        elif hasattr(client, "_client") and hasattr(client._client, "mcp_url"):
            return client._client.mcp_url
        elif hasattr(client, "url"):
            return client.url
        else:
            return getattr(client, "base_url", "http://localhost:8000")

    async def run_all(self, categories: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run all registered tests.

        Args:
            categories: Optional list of categories to run (e.g., ["core", "entity"])

        Returns:
            Summary dict with total, passed, failed, skipped, cached, duration, results
        """
        self.start_time = datetime.now()
        self.results = []

        if self.parallel:
            await self._initialize_connection_pool()
            self._semaphore = asyncio.Semaphore(self.parallel_workers)
            self._worker_context.initialize_semaphore(self.parallel_workers)

        if categories:
            tests_to_run = {}
            for cat in categories:
                tests_to_run.update(self.test_registry.get_tests(cat))
        else:
            tests_to_run = self.test_registry.get_tests()

        if not tests_to_run:
            print("No tests found")
            return {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "cached": 0,
                "duration_seconds": 0.0,
                "results": [],
            }

        by_category: Dict[str, List] = {}
        for test_name, test_info in tests_to_run.items():
            category = test_info["category"]
            by_category.setdefault(category, []).append((test_name, test_info))

        category_order = self._get_category_order()
        sorted_categories = sorted(
            by_category.items(),
            key=lambda x: category_order.index(x[0]) if x[0] in category_order else 999,
        )

        total_tests = len(tests_to_run)

        if self.parallel:
            print(f"Parallel execution enabled: {self.parallel_workers} workers")

        use_enhanced_progress = False
        progress_display = None
        if ComprehensiveProgressDisplay:
            try:
                progress_display = ComprehensiveProgressDisplay(
                    total_tests=total_tests,
                    categories=list(by_category.keys()),
                    parallel=self.parallel,
                    workers=self.parallel_workers,
                )
                use_enhanced_progress = True
                for reporter in self.reporters:
                    if hasattr(reporter, "show_running"):
                        reporter.show_running = False
            except Exception:
                use_enhanced_progress = False

        pbar = None
        if not use_enhanced_progress and HAS_TQDM and _tqdm:
            pbar = _tqdm(
                total=total_tests,
                desc="Running tests",
                unit="test",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
            )

        try:
            if use_enhanced_progress and progress_display:
                with progress_display as prog:
                    for category, tests in by_category.items():
                        prog.set_category_total(category, len(tests))
                    await self._run_with_enhanced_progress(sorted_categories, progress_display)
            else:
                await self._run_with_basic_progress(sorted_categories, pbar)
        finally:
            if not use_enhanced_progress and pbar:
                pbar.close()

        self.end_time = datetime.now()

        metadata = self._get_metadata()
        metadata.update(
            {
                "auth_status": "authenticated",
                "duration_seconds": (self.end_time - self.start_time).total_seconds(),
                "parallel_mode": self.parallel,
                "parallel_workers": self.parallel_workers if self.parallel else 1,
            }
        )

        for reporter in self.reporters:
            reporter.report(self.results, metadata)

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

        if self.parallel:
            summary["worker_stats"] = self._worker_context.worker_errors

        return summary

    async def _run_with_enhanced_progress(self, sorted_categories, progress_display):
        """Run tests with enhanced progress display."""
        for category, tests in sorted_categories:
            progress_display.write(f"\n{category.upper()} Tests")

            if self.parallel:
                tasks = [
                    self._run_single_test_with_worker_enhanced(
                        test_name, test_info, category, progress_display
                    )
                    for test_name, test_info in tests
                ]
                await asyncio.gather(*tasks, return_exceptions=True)
            else:
                for test_name, test_info in tests:
                    await self._run_single_test_enhanced(
                        test_name, test_info, category, progress_display
                    )

    async def _run_with_basic_progress(self, sorted_categories, pbar):
        """Run tests with basic tqdm progress."""
        try:
            for category, tests in sorted_categories:
                if pbar:
                    pbar.write(f"\n{category.upper()} Tests")
                else:
                    print(f"\n{category.upper()} Tests")

                if self.parallel and len(tests) > 1:
                    print(
                        f"   Running {len(tests)} tests in parallel across {self.parallel_workers} workers..."
                    )
                    tasks = [
                        self._run_single_test_with_worker(test_name, test_info, pbar)
                        for test_name, test_info in tests
                    ]
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    for i, result in enumerate(results):
                        if isinstance(result, Exception):
                            test_name, test_info = tests[i]
                            error_msg = str(result)
                            if (
                                "not holding this lock" in error_msg
                                or "RuntimeError" in str(type(result))
                                or "530" in error_msg
                                or "502" in error_msg
                            ):
                                print("\nConnection/lock issue detected in worker")
                                print("   Treating as connection loss - cache invalidated")
                                if self.cache_instance:
                                    self.cache_instance.clear()
                                msg = f"⚠️  {test_name} - Connection issue (will retry next run)"
                                if pbar:
                                    pbar.write(msg)
                                else:
                                    print(msg)
                            else:
                                if "ModuleNotFoundError" in error_msg or "ImportError" in error_msg:
                                    print(f"\n❌ {test_name} - Import Error:")
                                    print(f"   {error_msg}")
                                    if hasattr(result, "__traceback__"):
                                        traceback.print_exception(
                                            type(result), result, result.__traceback__
                                        )
                                elif pbar:
                                    pbar.write(f"❌ {test_name} - Worker failed: {error_msg[:100]}")
                                else:
                                    print(f"❌ {test_name} - Worker failed: {error_msg[:100]}")
                else:
                    for test_name, test_info in tests:
                        await self._run_single_test(test_name, test_info, pbar)

        finally:
            if pbar:
                pbar.close()
            self._worker_context.cleanup_all()

    async def _run_single_test_enhanced(
        self,
        test_name: str,
        test_info: Dict[str, Any],
        category: str,
        progress_display,
        worker_id: Optional[int] = None,
    ):
        """Run single test with enhanced progress display."""
        tool_name = test_info["tool_name"]
        progress_display.set_current_test(
            test_name=test_name,
            tool_name=tool_name,
            category=category,
            worker_id=worker_id,
        )
        await self._run_single_test(test_name, test_info, None, worker_id=worker_id)

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
                worker_id=worker_id,
            )

    async def _run_single_test_with_worker_enhanced(
        self, test_name: str, test_info: Dict[str, Any], category: str, progress_display
    ):
        """Run single test with worker + enhanced progress."""
        if self._semaphore:
            async with self._semaphore:
                await self._run_single_test_enhanced_impl(
                    test_name, test_info, category, progress_display
                )
        else:
            await self._run_single_test_enhanced_impl(
                test_name, test_info, category, progress_display
            )

    async def _run_single_test_enhanced_impl(
        self, test_name: str, test_info: Dict[str, Any], category: str, progress_display
    ):
        """Implementation helper for enhanced test running."""
        worker_id = self._worker_context.get_worker_id()
        self._worker_context.setup_environment(worker_id)
        try:
            await self._run_single_test_enhanced(
                test_name, test_info, category, progress_display, worker_id=worker_id
            )
        except Exception as e:
            self._worker_context.record_error(worker_id, str(e))
            raise

    async def _run_single_test_with_worker(
        self, test_name: str, test_info: Dict[str, Any], pbar: Optional[Any] = None
    ) -> None:
        """Run a single test with worker isolation and dedicated MCP client."""
        if self._semaphore:
            async with self._semaphore:
                await self._run_single_test_with_worker_impl(test_name, test_info, pbar)
        else:
            await self._run_single_test_with_worker_impl(test_name, test_info, pbar)

    async def _run_single_test_with_worker_impl(
        self, test_name: str, test_info: Dict[str, Any], pbar: Optional[Any] = None
    ) -> None:
        """Implementation helper for worker-based test running."""
        worker_id = self._worker_context.get_worker_id()
        self._worker_context.setup_environment(worker_id)

        worker_client = None
        client_manager = getattr(self, "client_manager", None)
        if client_manager:
            try:
                worker_client = await client_manager.acquire(timeout=10.0)
            except Exception as e:
                print(f"Worker {worker_id} couldn't acquire client: {e}")

        try:
            if worker_client:
                AtomsMCPClientAdapter = getattr(self, "AtomsMCPClientAdapter", None)
                if AtomsMCPClientAdapter:
                    worker_adapter = AtomsMCPClientAdapter(worker_client, verbose_on_fail=True)
                    original_adapter = self.client_adapter
                    self.client_adapter = worker_adapter
                    try:
                        await self._run_single_test(test_name, test_info, pbar, worker_id=worker_id)
                    finally:
                        self.client_adapter = original_adapter
                else:
                    await self._run_single_test(test_name, test_info, pbar, worker_id=worker_id)
            else:
                await self._run_single_test(test_name, test_info, pbar, worker_id=worker_id)

        except Exception as e:
            error_msg = f"Test {test_name} failed in worker {worker_id}: {str(e)}"
            self._worker_context.record_error(worker_id, error_msg)
            raise
        finally:
            if worker_client and client_manager:
                await client_manager.release(worker_client)

    async def _run_single_test(
        self,
        test_name: str,
        test_info: Dict[str, Any],
        pbar: Optional[Any] = None,
        worker_id: Optional[int] = None,
    ) -> None:
        """Run a single test (delegates to TestExecutor)."""
        await self._executor.execute(
            test_name=test_name,
            test_info=test_info,
            client_adapter=self.client_adapter,
            pbar=pbar,
            worker_id=worker_id,
        )

    @abstractmethod
    def _get_metadata(self) -> Dict[str, Any]:
        """Get project-specific metadata for test reports."""
        pass

    def _get_category_order(self) -> List[str]:
        """Get test category execution order (overridable)."""
        return ["core", "entity", "query", "relationship", "workflow", "integration"]

    def _get_adapter_class(self):
        """Get the project client adapter class (optional override)."""
        return None


__all__ = ["BaseTestRunner"]
