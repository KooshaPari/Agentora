"""Test execution engine for MCP testing.

Provides:
- Core test execution with caching, timing, and error handling
- Timeout and warning thresholds
- Result formatting and aggregation
- Skip handling for pytest.skip
- Detailed error capture with tracebacks and locals
"""

import asyncio
import sys
import time
import traceback
from typing import Any, Dict, List, Optional


try:
    from pheno.testing.mcp_qa.testing.logging_config import QuietLogger
except ImportError:

    class QuietLogger:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass


class TestExecutor:
    """Handles test execution including caching, timing, and error handling."""

    def __init__(
        self,
        cache_instance: Optional[Any] = None,
        reporters: Optional[List[Any]] = None,
        results: Optional[List[Dict[str, Any]]] = None,
        results_lock: Optional[Any] = None,
        verbose: bool = False,
    ):
        self.cache_instance = cache_instance
        self.reporters = reporters or []
        self.results = results or []
        self.results_lock = results_lock
        self.verbose = verbose

    async def execute(
        self,
        test_name: str,
        test_info: Dict[str, Any],
        client_adapter: Any,
        pbar: Optional[Any] = None,
        worker_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute a single test with caching, timing, and error handling."""
        test_func = test_info["func"]
        tool_name = test_info["tool_name"]

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
            self._add_result(result)
            if pbar:
                pbar.update(1)
            return result

        for reporter in self.reporters:
            if hasattr(reporter, "on_test_start"):
                try:
                    reporter.on_test_start(test_name, test_info)
                except Exception:
                    pass

        start = time.time()
        test_timeout = 60.0
        warning_threshold = 10.0

        async def warning_task():
            await asyncio.sleep(warning_threshold)
            print(f"\nTest {test_name} is taking longer than expected (>{warning_threshold}s)")

        warning_handle = asyncio.create_task(warning_task())

        try:
            if self.verbose:
                test_result = await asyncio.wait_for(
                    test_func(client_adapter), timeout=test_timeout
                )
            else:
                with QuietLogger():
                    test_result = await asyncio.wait_for(
                        test_func(client_adapter), timeout=test_timeout
                    )

            duration_ms = (time.time() - start) * 1000

            if not warning_handle.done():
                warning_handle.cancel()
                try:
                    await warning_handle
                except asyncio.CancelledError:
                    pass

            if isinstance(test_result, dict):
                success = test_result.get("success", False)
                error = test_result.get("error")
                skipped = test_result.get("skipped", False)
            else:
                success = True if test_result is None else bool(test_result)
                error = None
                skipped = False

            result = self._build_result(
                test_name=test_name,
                tool_name=tool_name,
                success=success,
                skipped=skipped,
                duration_ms=duration_ms,
                error=error,
                worker_id=worker_id,
            )

            self._finalize_result(result, test_name, tool_name, duration_ms)
            self._output_result(result, pbar)
            return result

        except asyncio.TimeoutError:
            return await self._handle_timeout(
                start, test_name, tool_name, test_timeout, pbar, worker_id, warning_handle
            )

        except Exception as e:
            return await self._handle_exception(
                e, start, test_name, tool_name, pbar, worker_id, warning_handle
            )

    async def _handle_timeout(
        self,
        start: float,
        test_name: str,
        tool_name: str,
        test_timeout: float,
        pbar: Optional[Any],
        worker_id: Optional[int],
        warning_handle: asyncio.Task,
    ) -> Dict[str, Any]:
        """Handle test timeout."""
        if not warning_handle.done():
            warning_handle.cancel()
            try:
                await warning_handle
            except asyncio.CancelledError:
                pass

        duration_ms = (time.time() - start) * 1000
        error = f"Test timeout after {test_timeout}s"

        result = self._build_result(
            test_name=test_name,
            tool_name=tool_name,
            success=False,
            skipped=False,
            duration_ms=duration_ms,
            error=error,
            worker_id=worker_id,
        )

        if self.cache_instance:
            self.cache_instance.record(test_name, tool_name, "timeout", duration_ms / 1000, error)

        self._add_result(result)
        self._output_timeout_result(result, pbar, test_timeout, worker_id)
        return result

    async def _handle_exception(
        self,
        e: Exception,
        start: float,
        test_name: str,
        tool_name: str,
        pbar: Optional[Any],
        worker_id: Optional[int],
        warning_handle: asyncio.Task,
    ) -> Dict[str, Any]:
        """Handle test exception."""
        if not warning_handle.done():
            warning_handle.cancel()
            try:
                await warning_handle
            except asyncio.CancelledError:
                pass

        duration_ms = (time.time() - start) * 1000
        exc_type, exc_value, exc_tb = sys.exc_info()
        is_skip = exc_type and exc_type.__name__ in ("Skipped", "SkipTest", "TestSkipped")

        if is_skip:
            result = self._build_result(
                test_name=test_name,
                tool_name=tool_name,
                success=True,
                skipped=True,
                duration_ms=duration_ms,
                error=None,
                skip_reason=str(e),
                worker_id=worker_id,
            )
            self._add_result(result)
            if pbar:
                pbar.update(1)
            return result

        tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        error_msg = str(e)

        if exc_type and exc_type.__name__ == "AssertionError":
            error = (
                f"AssertionError: {error_msg}"
                if error_msg
                else "AssertionError: (assertion failed without message)"
            )
        else:
            error = (
                error_msg
                if error_msg and error_msg.strip()
                else f"{exc_type.__name__ if exc_type else 'Exception'}: (no error message)"
            )

        locals_data = {}
        if exc_tb:
            frame = exc_tb.tb_frame
            try:
                locals_data = {
                    k: v for k, v in frame.f_locals.items() if not k.startswith("_") and k != "self"
                }
            except Exception:
                pass

        result = self._build_result(
            test_name=test_name,
            tool_name=tool_name,
            success=False,
            skipped=False,
            duration_ms=duration_ms,
            error=error,
            traceback=tb_str,
            locals=locals_data,
            worker_id=worker_id,
        )

        if "result" in locals_data and isinstance(locals_data["result"], dict):
            result["response"] = locals_data["result"].get("response")

        if "data" in locals_data:
            result["request_params"] = {
                "entity_type": locals_data.get("entity_type"),
                "operation": locals_data.get("operation"),
                "data": locals_data.get("data"),
            }

        if self.cache_instance:
            self.cache_instance.record(test_name, tool_name, "error", duration_ms / 1000, error)

        self._add_result(result)
        self._output_error_result(result, pbar, worker_id)
        return result

    def _build_result(
        self,
        test_name: str,
        tool_name: str,
        success: bool,
        skipped: bool,
        duration_ms: float,
        error: Optional[str] = None,
        traceback: Optional[str] = None,
        locals_data: Optional[Dict[str, Any]] = None,
        skip_reason: Optional[str] = None,
        worker_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Build a result dictionary."""
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
        if traceback:
            result["traceback"] = traceback
        if locals_data:
            result["locals"] = locals_data
        if skip_reason:
            result["skip_reason"] = skip_reason
        return result

    def _finalize_result(
        self, result: Dict[str, Any], test_name: str, tool_name: str, duration_ms: float
    ) -> None:
        """Finalize and record result."""
        if self.cache_instance and not result.get("skipped"):
            status = "passed" if result.get("success") else "failed"
            self.cache_instance.record(
                test_name, tool_name, status, duration_ms / 1000, result.get("error")
            )

        self._add_result(result)

        for reporter in self.reporters:
            if hasattr(reporter, "on_test_complete"):
                try:
                    reporter.on_test_complete(test_name, result)
                except Exception:
                    pass

    def _add_result(self, result: Dict[str, Any]) -> None:
        """Add result to results list (thread-safe)."""
        if self.results_lock:
            with self.results_lock:
                self.results.append(result)
        else:
            self.results.append(result)

    def _output_result(self, result: Dict[str, Any], pbar: Optional[Any]) -> None:
        """Output result based on success/failure status."""
        if pbar:
            pbar.update(1)
            if not result.get("success") and not result.get("skipped"):
                print(f"FAIL: {result['test_name']} ({result['duration_ms']:.2f}ms)")
        elif not result.get("success") and not result.get("skipped"):
            print(f"FAIL: {result['test_name']} ({result['duration_ms']:.2f}ms)")

    def _output_timeout_result(
        self,
        result: Dict[str, Any],
        pbar: Optional[Any],
        test_timeout: float,
        worker_id: Optional[int],
    ) -> None:
        """Output timeout result."""
        worker_tag = f" [W{worker_id}]" if worker_id is not None else ""
        if pbar:
            pbar.update(1)
            pbar.write(f"TIMEOUT: {result['test_name']} ({test_timeout}s){worker_tag}")
        else:
            print(f"TIMEOUT: {result['test_name']} ({test_timeout}s){worker_tag}")

    def _output_error_result(
        self, result: Dict[str, Any], pbar: Optional[Any], worker_id: Optional[int]
    ) -> None:
        """Output error result."""
        worker_tag = f" [W{worker_id}]" if worker_id is not None else ""
        error_msg = result.get("error", "")[:50]
        if pbar:
            pbar.update(1)
            pbar.write(f"ERROR: {result['test_name']} - {error_msg}{worker_tag}")
        else:
            print(f"ERROR: {result['test_name']} - {error_msg}{worker_tag}")
