"""Metrics Scheme Handler.

Provides access to application metrics via metrics:// URIs.
"""

from collections import defaultdict
from datetime import datetime
from typing import Any

from pheno.ports.mcp import ResourceSchemeHandler


class MetricsSchemeHandler(ResourceSchemeHandler):
    """Handler for metrics:// scheme.

    Provides access to application metrics.

    URI Format:
        metrics://counters/http_requests_total
        metrics://gauges/memory_usage_bytes
        metrics://histograms/response_time_seconds
        metrics://all  (get all metrics)

    Example:
        >>> handler = MetricsSchemeHandler()
        >>> requests = await handler.get_resource("metrics://counters/http_requests_total")
        >>> all_metrics = await handler.get_resource("metrics://all")
    """

    def __init__(self):
        """
        Initialize metrics scheme handler.
        """
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = defaultdict(list)
        self._metadata: dict[str, dict[str, Any]] = {}

    def record_counter(self, name: str, value: float = 1.0, **tags) -> None:
        """Record a counter metric.

        Args:
            name: Metric name
            value: Value to add
            **tags: Optional tags
        """
        key = self._make_key(name, tags)
        self._counters[key] += value
        self._metadata[key] = {
            "type": "counter",
            "name": name,
            "tags": tags,
            "updated_at": datetime.now().isoformat(),
        }

    def record_gauge(self, name: str, value: float, **tags) -> None:
        """Record a gauge metric.

        Args:
            name: Metric name
            value: Current value
            **tags: Optional tags
        """
        key = self._make_key(name, tags)
        self._gauges[key] = value
        self._metadata[key] = {
            "type": "gauge",
            "name": name,
            "tags": tags,
            "updated_at": datetime.now().isoformat(),
        }

    def record_histogram(self, name: str, value: float, **tags) -> None:
        """Record a histogram value.

        Args:
            name: Metric name
            value: Value to record
            **tags: Optional tags
        """
        key = self._make_key(name, tags)
        self._histograms[key].append(value)
        self._metadata[key] = {
            "type": "histogram",
            "name": name,
            "tags": tags,
            "updated_at": datetime.now().isoformat(),
        }

    async def get_resource(self, uri: str) -> Any:
        """Get metrics.

        Args:
            uri: URI in format metrics://type/name

        Returns:
            Metric data

        Example:
            >>> data = await handler.get_resource("metrics://counters/requests")
        """
        _, path = uri.split("://", 1)

        if path == "all":
            return self._get_all_metrics()

        parts = path.split("/")
        metric_type = parts[0]
        metric_name = parts[1] if len(parts) > 1 else None

        if metric_type == "counters":
            return self._get_counters(metric_name)
        if metric_type == "gauges":
            return self._get_gauges(metric_name)
        if metric_type == "histograms":
            return self._get_histograms(metric_name)
        raise ValueError(f"Unknown metric type: {metric_type}")

    async def list_resources(self, uri: str) -> list[str]:
        """List available metrics.

        Args:
            uri: URI pattern

        Returns:
            List of metric URIs

        Example:
            >>> metrics = await handler.list_resources("metrics://counters/*")
        """
        _, path = uri.split("://", 1)

        if path in {"*", "all"}:
            # List all metric types
            return [
                "metrics://counters",
                "metrics://gauges",
                "metrics://histograms",
                "metrics://all",
            ]

        parts = path.split("/")
        metric_type = parts[0]

        if metric_type == "counters":
            names = {self._metadata[k]["name"] for k in self._counters}
            return [f"metrics://counters/{name}" for name in names]
        if metric_type == "gauges":
            names = {self._metadata[k]["name"] for k in self._gauges}
            return [f"metrics://gauges/{name}" for name in names]
        if metric_type == "histograms":
            names = {self._metadata[k]["name"] for k in self._histograms}
            return [f"metrics://histograms/{name}" for name in names]

        return []

    def supports_scheme(self, scheme: str) -> bool:
        """
        Check if scheme is supported.
        """
        return scheme == "metrics"

    # Helper methods

    def _make_key(self, name: str, tags: dict[str, str]) -> str:
        """
        Make a unique key for a metric.
        """
        if not tags:
            return name
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}{{{tag_str}}}"

    def _get_all_metrics(self) -> dict[str, Any]:
        """
        Get all metrics.
        """
        return {
            "counters": self._get_counters(),
            "gauges": self._get_gauges(),
            "histograms": self._get_histograms(),
        }

    def _get_counters(self, name: str | None = None) -> dict[str, Any]:
        """
        Get counter metrics.
        """
        if name:
            return {
                k: {"value": v, "metadata": self._metadata[k]}
                for k, v in self._counters.items()
                if self._metadata[k]["name"] == name
            }
        return {k: {"value": v, "metadata": self._metadata[k]} for k, v in self._counters.items()}

    def _get_gauges(self, name: str | None = None) -> dict[str, Any]:
        """
        Get gauge metrics.
        """
        if name:
            return {
                k: {"value": v, "metadata": self._metadata[k]}
                for k, v in self._gauges.items()
                if self._metadata[k]["name"] == name
            }
        return {k: {"value": v, "metadata": self._metadata[k]} for k, v in self._gauges.items()}

    def _get_histograms(self, name: str | None = None) -> dict[str, Any]:
        """
        Get histogram metrics.
        """
        if name:
            return {
                k: {
                    "values": v,
                    "count": len(v),
                    "sum": sum(v),
                    "avg": sum(v) / len(v) if v else 0,
                    "min": min(v) if v else 0,
                    "max": max(v) if v else 0,
                    "metadata": self._metadata[k],
                }
                for k, v in self._histograms.items()
                if self._metadata[k]["name"] == name
            }
        return {
            k: {
                "values": v,
                "count": len(v),
                "sum": sum(v),
                "avg": sum(v) / len(v) if v else 0,
                "min": min(v) if v else 0,
                "max": max(v) if v else 0,
                "metadata": self._metadata[k],
            }
            for k, v in self._histograms.items()
        }


__all__ = ["MetricsSchemeHandler"]
