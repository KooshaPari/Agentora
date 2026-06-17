"""MCP-Specific Performance Monitor.

Monitors MCP protocol requests and responses for performance tracking.
"""

import logging
import time
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


class MCPPerformanceMonitor:
    """
    Monitor MCP protocol performance.
    """

    def __init__(self):
        self.request_metrics: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.active_requests: dict[str, float] = {}
        self.total_requests = 0
        self.total_errors = 0

    def start_request(self, request_id: str, request_type: str) -> None:
        """
        Start tracking an MCP request.
        """
        self.active_requests[request_id] = time.time()
        self.total_requests += 1

    def end_request(
        self,
        request_id: str,
        request_type: str,
        success: bool = True,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        End tracking an MCP request.
        """
        if request_id not in self.active_requests:
            return

        start_time = self.active_requests.pop(request_id)
        duration = time.time() - start_time

        metric = {
            "request_id": request_id,
            "request_type": request_type,
            "duration_seconds": duration,
            "success": success,
            "error": error,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }

        self.request_metrics[request_type].append(metric)

        if not success:
            self.total_errors += 1

        logger.debug(
            f"MCP request completed: {request_type} "
            f"(duration={duration:.3f}s, success={success})",
        )

    def get_metrics(self, request_type: str | None = None) -> dict[str, Any]:
        """
        Get performance metrics.
        """
        if request_type:
            metrics = self.request_metrics.get(request_type, [])
            return self._calculate_metrics(request_type, metrics)

        # Return metrics for all request types
        all_metrics = {}
        for req_type, metrics in self.request_metrics.items():
            all_metrics[req_type] = self._calculate_metrics(req_type, metrics)

        return all_metrics

    def _calculate_metrics(
        self, request_type: str, metrics: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Calculate aggregated metrics.
        """
        if not metrics:
            return {
                "request_type": request_type,
                "total_requests": 0,
                "success_rate": 0.0,
                "avg_duration": 0.0,
            }

        durations = [m["duration_seconds"] for m in metrics]
        successes = sum(1 for m in metrics if m["success"])

        return {
            "request_type": request_type,
            "total_requests": len(metrics),
            "successful_requests": successes,
            "failed_requests": len(metrics) - successes,
            "success_rate": successes / len(metrics) if metrics else 0.0,
            "avg_duration": sum(durations) / len(durations) if durations else 0.0,
            "min_duration": min(durations) if durations else 0.0,
            "max_duration": max(durations) if durations else 0.0,
            "active_requests": len(
                [k for k in self.active_requests if k.startswith(request_type)],
            ),
        }

    def get_summary(self) -> dict[str, Any]:
        """
        Get overall performance summary.
        """
        total_duration = 0.0
        total_count = 0

        for metrics in self.request_metrics.values():
            for metric in metrics:
                total_duration += metric["duration_seconds"]
                total_count += 1

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "error_rate": (
                self.total_errors / self.total_requests if self.total_requests > 0 else 0.0
            ),
            "avg_duration_overall": (total_duration / total_count if total_count > 0 else 0.0),
            "active_requests": len(self.active_requests),
            "request_types_tracked": len(self.request_metrics),
        }

    def clear_metrics(self, request_type: str | None = None) -> None:
        """
        Clear metrics.
        """
        if request_type:
            self.request_metrics[request_type].clear()
        else:
            self.request_metrics.clear()
            self.active_requests.clear()
            self.total_requests = 0
            self.total_errors = 0


# Global MCP monitor instance
_mcp_monitor: MCPPerformanceMonitor | None = None


def get_mcp_monitor() -> MCPPerformanceMonitor:
    """
    Get the global MCP performance monitor instance.
    """
    global _mcp_monitor
    if _mcp_monitor is None:
        _mcp_monitor = MCPPerformanceMonitor()
    return _mcp_monitor


def track_mcp_request(request_type: str):
    """
    Decorator to track MCP request performance.
    """

    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            import uuid

            monitor = get_mcp_monitor()
            request_id = f"{request_type}_{uuid.uuid4().hex[:8]}"

            monitor.start_request(request_id, request_type)

            try:
                result = await func(*args, **kwargs)
                monitor.end_request(request_id, request_type, success=True)
                return result

            except Exception as e:
                monitor.end_request(request_id, request_type, success=False, error=str(e))
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            import uuid

            monitor = get_mcp_monitor()
            request_id = f"{request_type}_{uuid.uuid4().hex[:8]}"

            monitor.start_request(request_id, request_type)

            try:
                result = func(*args, **kwargs)
                monitor.end_request(request_id, request_type, success=True)
                return result

            except Exception as e:
                monitor.end_request(request_id, request_type, success=False, error=str(e))
                raise

        import asyncio

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator
