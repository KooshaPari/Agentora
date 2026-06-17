"""
Performance metrics resource scheme.
"""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING, Any

from .base import ResourceSchemeHandler
from .common import LOGGER, PSUTIL_AVAILABLE, psutil

if TYPE_CHECKING:
    from ..template_engine import ResourceContext


class MetricsResourceScheme(ResourceSchemeHandler):
    """Handler for metrics:// resources - performance metrics."""

    def __init__(self):
        super().__init__("metrics")
        self.metrics_history: list[dict[str, Any]] = []
        self.max_history = 1000

    async def handle_request(self, context: ResourceContext) -> dict[str, Any]:
        """
        Default to current metrics.
        """
        return await self.get_metrics(context)

    async def get_metrics(self, context: ResourceContext) -> dict[str, Any]:
        """
        Get performance metrics.
        """
        metric_type = context.get_parameter("type", "all")
        current_metrics: dict[str, Any] = {}

        if metric_type in ["all", "server"]:
            current_metrics["server"] = {
                "uptime_seconds": context.get_server_info("uptime_seconds", 0),
                "requests_total": context.get_server_info("requests_total", 0),
                "tools_executed": context.get_server_info("tools_executed", 0),
                "errors_total": context.get_server_info("errors_total", 0),
            }

        if metric_type in ["all", "performance"] and PSUTIL_AVAILABLE:
            try:
                assert psutil is not None
                process = psutil.Process(os.getpid())
                current_metrics["performance"] = {
                    "cpu_percent": process.cpu_percent(),
                    "memory_rss_mb": process.memory_info().rss / 1024 / 1024,
                    "memory_vms_mb": process.memory_info().vms / 1024 / 1024,
                    "threads": process.num_threads(),
                    "open_files": len(process.open_files()),
                }
            except Exception as exc:  # pragma: no cover - defensive
                LOGGER.error("Error collecting performance metrics: %s", exc)
                current_metrics["performance"] = {"error": str(exc)}
        elif metric_type in ["all", "performance"]:
            current_metrics["performance"] = {
                "error": "psutil not available - install with 'pip install psutil' for detailed metrics",
            }

        if metric_type in ["all", "cache"]:
            current_metrics["cache"] = context.get_server_info("cache_stats", {})

        if metric_type in ["all", "tools"]:
            current_metrics["tools"] = {
                "total": context.get_server_info("tools_count", 0),
                "usage": context.get_server_info("tool_usage_stats", {}),
                "average_execution_time": context.get_server_info("avg_tool_execution_time", 0),
            }

        self.metrics_history.append(
            {
                "timestamp": int(time.time()),
                "metrics": current_metrics,
            },
        )

        if len(self.metrics_history) > self.max_history:
            self.metrics_history = self.metrics_history[-self.max_history :]

        return {
            "current": current_metrics,
            "type": metric_type,
            "timestamp": int(time.time()),
        }

    async def get_metrics_history(self, context: ResourceContext) -> dict[str, Any]:
        """
        Get historical metrics data.
        """
        limit = int(context.get_parameter("limit", 100))
        since = context.get_parameter("since")

        history = self.metrics_history

        if since:
            try:
                since_timestamp = int(since)
                history = [entry for entry in history if entry["timestamp"] >= since_timestamp]
            except ValueError:
                LOGGER.warning("Invalid 'since' parameter for metrics history: %s", since)

        if limit > 0:
            history = history[-limit:]

        return {
            "history": history,
            "total": len(history),
            "limit": limit,
            "since": since,
            "timestamp": int(time.time()),
        }


__all__ = ["MetricsResourceScheme"]
