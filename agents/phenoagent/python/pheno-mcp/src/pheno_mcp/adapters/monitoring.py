"""In-Memory Monitoring Provider.

Implementation of MonitoringProvider for tracking workflows and metrics.
"""

import logging
from datetime import datetime
from typing import Any

from pheno.ports.mcp import MonitoringProvider

logger = logging.getLogger(__name__)


class InMemoryMonitoringProvider(MonitoringProvider):
    """In-memory monitoring provider implementation.

    Stores metrics and workflow data in memory.

    Example:
        >>> monitor = InMemoryMonitoringProvider()
        >>> await monitor.track_workflow("data-pipeline", {"user": "alice"})
        >>> await monitor.record_metric("execution_time", 1.23, {"tool": "search"})
    """

    def __init__(self):
        self._workflows: dict[str, dict[str, Any]] = {}
        self._metrics: list[dict[str, Any]] = []
        self._counters: dict[str, int] = {}
        self._histograms: dict[str, list[float]] = {}
        self._errors: list[dict[str, Any]] = []
        self._spans: dict[str, dict[str, Any]] = {}

    async def track_workflow(
        self, workflow_id: str, metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Track a workflow execution.
        """
        self._workflows[workflow_id] = {
            "workflow_id": workflow_id,
            "metadata": metadata or {},
            "started_at": datetime.now(),
            "status": "running",
        }
        logger.info(f"Tracking workflow: {workflow_id}")

    async def record_metric(
        self,
        name: str,
        value: float,
        tags: dict[str, str] | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        """
        Record a metric value.
        """
        metric = {
            "name": name,
            "value": value,
            "tags": tags or {},
            "timestamp": timestamp or datetime.now(),
        }
        self._metrics.append(metric)

    async def record_counter(
        self, name: str, increment: int = 1, tags: dict[str, str] | None = None,
    ) -> None:
        """
        Increment a counter metric.
        """
        key = f"{name}:{','.join(f'{k}={v}' for k, v in (tags or {}).items())}"
        self._counters[key] = self._counters.get(key, 0) + increment

    async def record_histogram(
        self, name: str, value: float, tags: dict[str, str] | None = None,
    ) -> None:
        """
        Record a histogram value.
        """
        key = f"{name}:{','.join(f'{k}={v}' for k, v in (tags or {}).items())}"
        if key not in self._histograms:
            self._histograms[key] = []
        self._histograms[key].append(value)

    async def get_metrics(
        self,
        filters: dict[str, Any] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get recorded metrics.
        """
        metrics = self._metrics.copy()

        # Filter by time range
        if start_time:
            metrics = [m for m in metrics if m["timestamp"] >= start_time]
        if end_time:
            metrics = [m for m in metrics if m["timestamp"] <= end_time]

        # Filter by name
        if filters and "name" in filters:
            metrics = [m for m in metrics if m["name"] == filters["name"]]

        # Filter by tags
        if filters and "tags" in filters:
            for tag_key, tag_value in filters["tags"].items():
                metrics = [m for m in metrics if m["tags"].get(tag_key) == tag_value]

        return metrics

    async def get_workflow_status(self, workflow_id: str) -> dict[str, Any]:
        """
        Get status of a workflow.
        """
        if workflow_id not in self._workflows:
            raise ValueError(f"Workflow not found: {workflow_id}")

        return self._workflows[workflow_id].copy()

    async def list_workflows(
        self, filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        List tracked workflows.
        """
        workflows = list(self._workflows.values())

        # Filter by metadata
        if filters:
            for key, value in filters.items():
                workflows = [w for w in workflows if w.get("metadata", {}).get(key) == value]

        return workflows

    async def record_error(
        self, error: Exception, context: dict[str, Any] | None = None,
    ) -> None:
        """
        Record an error.
        """
        error_record = {
            "error": str(error),
            "type": type(error).__name__,
            "context": context or {},
            "timestamp": datetime.now(),
        }
        self._errors.append(error_record)
        logger.error(f"Recorded error: {error}")

    async def start_span(self, name: str, attributes: dict[str, Any] | None = None) -> str:
        """
        Start a tracing span.
        """
        import uuid

        span_id = str(uuid.uuid4())

        self._spans[span_id] = {
            "span_id": span_id,
            "name": name,
            "attributes": attributes or {},
            "started_at": datetime.now(),
            "status": "active",
        }

        return span_id

    async def end_span(
        self, span_id: str, status: str = "ok", attributes: dict[str, Any] | None = None,
    ) -> None:
        """
        End a tracing span.
        """
        if span_id in self._spans:
            span = self._spans[span_id]
            span["status"] = status
            span["ended_at"] = datetime.now()

            if attributes:
                span["attributes"].update(attributes)

            # Calculate duration
            duration = (span["ended_at"] - span["started_at"]).total_seconds()
            span["duration_seconds"] = duration

    async def flush(self) -> None:
        """
        Flush any buffered metrics.
        """
        logger.info(f"Flushed monitoring data: {len(self._metrics)} metrics")

    # Helper methods for testing/inspection

    def get_counter_value(self, name: str, tags: dict[str, str] | None = None) -> int:
        """
        Get current counter value.
        """
        key = f"{name}:{','.join(f'{k}={v}' for k, v in (tags or {}).items())}"
        return self._counters.get(key, 0)

    def get_histogram_values(self, name: str, tags: dict[str, str] | None = None) -> list[float]:
        """
        Get histogram values.
        """
        key = f"{name}:{','.join(f'{k}={v}' for k, v in (tags or {}).items())}"
        return self._histograms.get(key, []).copy()

    def get_errors(self) -> list[dict[str, Any]]:
        """
        Get all recorded errors.
        """
        return self._errors.copy()

    def get_span(self, span_id: str) -> dict[str, Any] | None:
        """
        Get span by ID.
        """
        return self._spans.get(span_id, {}).copy() if span_id in self._spans else None

    def clear(self) -> None:
        """
        Clear all monitoring data.
        """
        self._workflows.clear()
        self._metrics.clear()
        self._counters.clear()
        self._histograms.clear()
        self._errors.clear()
        self._spans.clear()
        logger.info("Cleared all monitoring data")


__all__ = ["InMemoryMonitoringProvider"]
