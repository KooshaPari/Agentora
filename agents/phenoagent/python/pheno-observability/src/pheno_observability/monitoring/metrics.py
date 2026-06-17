"""Metrics Collection and Registry.

Unified metrics collection system that consolidates functionality from infra/monitoring,
MCP QA, and observability stacks.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from ..logging import get_logger

logger = get_logger(__name__)


@dataclass
class MetricPoint:
    """
    A single metric data point.
    """

    name: str
    value: int | float
    timestamp: float
    labels: dict[str, str] = field(default_factory=dict)
    metric_type: str = "gauge"  # gauge, counter, histogram, summary


@dataclass
class MetricSeries:
    """
    A series of metric points.
    """

    name: str
    points: list[MetricPoint] = field(default_factory=list)
    labels: dict[str, str] = field(default_factory=dict)
    metric_type: str = "gauge"

    def add_point(
        self,
        value: float,
        timestamp: float | None = None,
        labels: dict[str, str] | None = None,
    ) -> None:
        """
        Add a metric point to the series.
        """
        point = MetricPoint(
            name=self.name,
            value=value,
            timestamp=timestamp or time.time(),
            labels=labels or {},
            metric_type=self.metric_type,
        )
        self.points.append(point)

    def get_latest(self) -> MetricPoint | None:
        """
        Get the latest metric point.
        """
        return self.points[-1] if self.points else None

    def get_average(self, window_seconds: float | None = None) -> float | None:
        """
        Get average value over time window.
        """
        if not self.points:
            return None

        cutoff_time = time.time() - window_seconds if window_seconds else 0
        recent_points = [p for p in self.points if p.timestamp >= cutoff_time]

        if not recent_points:
            return None

        return sum(p.value for p in recent_points) / len(recent_points)


class MetricsCollector:
    """Collects and aggregates metrics from various sources.

    Consolidates metrics collection from infra/monitoring, MCP QA, and observability
    stacks into a unified interface.
    """

    def __init__(self, buffer_size: int = 1000):
        """Initialize metrics collector.

        Args:
            buffer_size: Maximum number of metric points to keep in memory
        """
        self.buffer_size = buffer_size
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

        # Metrics storage
        self._series: dict[str, MetricSeries] = {}
        self._counters: dict[str, float] = defaultdict(float)
        self._histograms: dict[str, list[float]] = defaultdict(list)

        # Collection state
        self._collecting = False
        self._collection_tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        """
        Start metrics collection.
        """
        if self._collecting:
            self.logger.warning("Metrics collector already started")
            return

        self._collecting = True
        self.logger.info("Started metrics collector")

    async def stop(self) -> None:
        """
        Stop metrics collection.
        """
        if not self._collecting:
            return

        # Cancel collection tasks
        for task in self._collection_tasks:
            task.cancel()

        if self._collection_tasks:
            await asyncio.gather(*self._collection_tasks, return_exceptions=True)

        self._collecting = False
        self.logger.info("Stopped metrics collector")

    def gauge(
        self, name: str, value: float, labels: dict[str, str] | None = None,
    ) -> None:
        """
        Record a gauge metric.
        """
        self._ensure_series(name, "gauge", labels or {})
        self._series[name].add_point(value, labels=labels)
        self._trim_series(name)

    def counter(
        self, name: str, value: float = 1, labels: dict[str, str] | None = None,
    ) -> None:
        """
        Record a counter metric.
        """
        self._ensure_series(name, "counter", labels or {})
        self._counters[name] += value
        self._series[name].add_point(self._counters[name], labels=labels)
        self._trim_series(name)

    def histogram(
        self, name: str, value: float, labels: dict[str, str] | None = None,
    ) -> None:
        """
        Record a histogram metric.
        """
        self._ensure_series(name, "histogram", labels or {})
        self._histograms[name].append(value)
        self._series[name].add_point(value, labels=labels)
        self._trim_series(name)

    def summary(
        self, name: str, value: float, labels: dict[str, str] | None = None,
    ) -> None:
        """
        Record a summary metric.
        """
        self._ensure_series(name, "summary", labels or {})
        self._series[name].add_point(value, labels=labels)
        self._trim_series(name)

    def _ensure_series(self, name: str, metric_type: str, labels: dict[str, str]) -> None:
        """
        Ensure a metric series exists.
        """
        if name not in self._series:
            self._series[name] = MetricSeries(
                name=name,
                metric_type=metric_type,
                labels=labels,
            )

    def _trim_series(self, name: str) -> None:
        """
        Trim series to buffer size.
        """
        if name in self._series and len(self._series[name].points) > self.buffer_size:
            # Keep only the most recent points
            self._series[name].points = self._series[name].points[-self.buffer_size :]

    def get_metric(self, name: str) -> MetricSeries | None:
        """
        Get a metric series by name.
        """
        return self._series.get(name)

    def get_all_metrics(self) -> dict[str, MetricSeries]:
        """
        Get all metric series.
        """
        return self._series.copy()

    def get_metric_summary(self) -> dict[str, Any]:
        """
        Get a summary of all metrics.
        """
        summary = self._create_base_summary()
        summary["series"] = self._build_series_summary()
        return summary

    def _create_base_summary(self) -> dict[str, Any]:
        """
        Create the base summary structure.
        """
        return {
            "total_series": len(self._series),
            "total_points": sum(len(series.points) for series in self._series.values()),
            "series": {},
        }

    def _build_series_summary(self) -> dict[str, Any]:
        """
        Build summary for all metric series.
        """
        series_summary = {}

        for name, series in self._series.items():
            series_summary[name] = self._build_single_series_summary(series)

        return series_summary

    def _build_single_series_summary(self, series: MetricSeries) -> dict[str, Any]:
        """
        Build summary for a single metric series.
        """
        latest = series.get_latest()
        return {
            "type": series.metric_type,
            "points_count": len(series.points),
            "latest_value": latest.value if latest else None,
            "latest_timestamp": latest.timestamp if latest else None,
            "average": series.get_average(),
        }


class MetricsRegistry:
    """Registry for managing multiple metrics collectors.

    Provides a centralized way to manage and query metrics from different components and
    services.
    """

    def __init__(self):
        """
        Initialize metrics registry.
        """
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        self._collectors: dict[str, MetricsCollector] = {}

    def register_collector(self, name: str, collector: MetricsCollector) -> None:
        """
        Register a metrics collector.
        """
        self._collectors[name] = collector
        self.logger.info(f"Registered metrics collector: {name}")

    def unregister_collector(self, name: str) -> None:
        """
        Unregister a metrics collector.
        """
        if name in self._collectors:
            del self._collectors[name]
            self.logger.info(f"Unregistered metrics collector: {name}")

    def get_collector(self, name: str) -> MetricsCollector | None:
        """
        Get a metrics collector by name.
        """
        return self._collectors.get(name)

    def get_all_metrics(self) -> dict[str, dict[str, Any]]:
        """
        Get all metrics from all collectors.
        """
        all_metrics = {}
        for name, collector in self._collectors.items():
            all_metrics[name] = collector.get_all_metrics()
        return all_metrics

    def get_global_summary(self) -> dict[str, Any]:
        """
        Get a global summary of all metrics.
        """
        summary = {
            "collectors": len(self._collectors),
            "collector_names": list(self._collectors.keys()),
            "metrics": {},
        }

        for name, collector in self._collectors.items():
            summary["metrics"][name] = collector.get_metric_summary()

        return summary

    async def start_all(self) -> None:
        """
        Start all registered collectors.
        """
        for name, collector in self._collectors.items():
            try:
                await collector.start()
                self.logger.info(f"Started collector: {name}")
            except Exception as e:
                self.logger.exception(f"Failed to start collector {name}: {e}")

    async def stop_all(self) -> None:
        """
        Stop all registered collectors.
        """
        for name, collector in self._collectors.items():
            try:
                await collector.stop()
                self.logger.info(f"Stopped collector: {name}")
            except Exception as e:
                self.logger.exception(f"Failed to stop collector {name}: {e}")
