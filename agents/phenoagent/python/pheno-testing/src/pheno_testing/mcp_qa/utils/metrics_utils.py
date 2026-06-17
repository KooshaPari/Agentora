"""Unified Metrics Utilities for MCP Projects.

Provides metrics collection, aggregation, and reporting utilities
for tracking application performance and usage.

Usage:
    from pheno.testing.mcp_qa.utils.metrics_utils import MetricsCollector, Counter, Timer

    collector = MetricsCollector()
    collector.increment("requests")

    with collector.timer("operation"):
        # Your code here
        pass
"""

from __future__ import annotations

import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from pheno.testing.mcp_qa.utils.logging_utils import get_logger

logger = get_logger(__name__)


# ============================================================================
# Metric Types
# ============================================================================


@dataclass
class MetricValue:
    """Base metric value with metadata.

    Attributes:
        name: Metric name
        value: Metric value
        timestamp: Unix timestamp
        tags: Optional tags for filtering
    """

    name: str
    value: Union[int, float]
    timestamp: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        """
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp,
            "tags": self.tags,
        }


class Counter:
    """Simple counter metric.

    Example:
        counter = Counter("requests")
        counter.increment()
        counter.increment(5)
        print(counter.value)  # 6
    """

    def __init__(self, name: str, initial: int = 0):
        """Initialize counter.

        Args:
            name: Metric name
            initial: Initial value
        """
        self.name = name
        self._value = initial

    def increment(self, amount: int = 1):
        """
        Increment counter.
        """
        self._value += amount

    def decrement(self, amount: int = 1):
        """
        Decrement counter.
        """
        self._value -= amount

    def reset(self):
        """
        Reset counter to zero.
        """
        self._value = 0

    @property
    def value(self) -> int:
        """
        Get current value.
        """
        return self._value


class Gauge:
    """Gauge metric (can go up or down).

    Example:
        gauge = Gauge("memory_usage")
        gauge.set(1024)
        gauge.increment(512)
        print(gauge.value)  # 1536
    """

    def __init__(self, name: str, initial: float = 0.0):
        """Initialize gauge.

        Args:
            name: Metric name
            initial: Initial value
        """
        self.name = name
        self._value = initial

    def set(self, value: float):
        """
        Set gauge value.
        """
        self._value = value

    def increment(self, amount: float = 1.0):
        """
        Increment gauge.
        """
        self._value += amount

    def decrement(self, amount: float = 1.0):
        """
        Decrement gauge.
        """
        self._value -= amount

    @property
    def value(self) -> float:
        """
        Get current value.
        """
        return self._value


class Histogram:
    """Histogram metric for tracking distributions.

    Example:
        histogram = Histogram("response_time")
        histogram.observe(0.123)
        histogram.observe(0.456)
        stats = histogram.statistics()
    """

    def __init__(self, name: str):
        """Initialize histogram.

        Args:
            name: Metric name
        """
        self.name = name
        self._values: List[float] = []

    def observe(self, value: float):
        """
        Record an observation.
        """
        self._values.append(value)

    def reset(self):
        """
        Clear all observations.
        """
        self._values.clear()

    @property
    def count(self) -> int:
        """
        Number of observations.
        """
        return len(self._values)

    def statistics(self) -> Dict[str, float]:
        """Calculate statistics.

        Returns:
            Dictionary with min, max, mean, median, p95, p99
        """
        if not self._values:
            return {
                "count": 0,
                "min": 0.0,
                "max": 0.0,
                "mean": 0.0,
                "median": 0.0,
                "p95": 0.0,
                "p99": 0.0,
            }

        sorted_values = sorted(self._values)
        count = len(sorted_values)

        return {
            "count": count,
            "min": sorted_values[0],
            "max": sorted_values[-1],
            "mean": sum(sorted_values) / count,
            "median": sorted_values[count // 2],
            "p95": sorted_values[int(count * 0.95)],
            "p99": sorted_values[int(count * 0.99)],
        }


# ============================================================================
# Metrics Collector
# ============================================================================


class MetricsCollector:
    """Central metrics collector with multiple metric types.

    Example:
        collector = MetricsCollector()

        # Counter
        collector.increment("requests")
        collector.increment("requests", tags={"method": "GET"})

        # Gauge
        collector.set_gauge("memory", 1024)

        # Histogram
        collector.observe("latency", 0.123)

        # Timer
        with collector.timer("operation"):
            # Code to time
            pass

        # Get metrics
        metrics = collector.get_metrics()
    """

    def __init__(self):
        """
        Initialize metrics collector.
        """
        self._counters: Dict[str, Counter] = defaultdict(lambda: Counter(""))
        self._gauges: Dict[str, Gauge] = defaultdict(lambda: Gauge(""))
        self._histograms: Dict[str, Histogram] = defaultdict(lambda: Histogram(""))
        self._timers: Dict[str, List[float]] = defaultdict(list)

    def increment(self, name: str, amount: int = 1, tags: Optional[Dict[str, str]] = None):
        """Increment a counter.

        Args:
            name: Counter name
            amount: Amount to increment
            tags: Optional tags
        """
        key = self._make_key(name, tags)
        counter = self._counters[key]
        counter.name = name
        counter.increment(amount)

    def decrement(self, name: str, amount: int = 1, tags: Optional[Dict[str, str]] = None):
        """Decrement a counter.

        Args:
            name: Counter name
            amount: Amount to decrement
            tags: Optional tags
        """
        key = self._make_key(name, tags)
        counter = self._counters[key]
        counter.name = name
        counter.decrement(amount)

    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Set a gauge value.

        Args:
            name: Gauge name
            value: Gauge value
            tags: Optional tags
        """
        key = self._make_key(name, tags)
        gauge = self._gauges[key]
        gauge.name = name
        gauge.set(value)

    def observe(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a histogram observation.

        Args:
            name: Histogram name
            value: Observed value
            tags: Optional tags
        """
        key = self._make_key(name, tags)
        histogram = self._histograms[key]
        histogram.name = name
        histogram.observe(value)

    @contextmanager
    def timer(self, name: str, tags: Optional[Dict[str, str]] = None):
        """Context manager for timing operations.

        Args:
            name: Timer name
            tags: Optional tags

        Example:
            with collector.timer("database_query"):
                result = db.query()
        """
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            self.observe(name, duration, tags)

    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics.

        Returns:
            Dictionary with counters, gauges, and histograms
        """
        return {
            "counters": {key: counter.value for key, counter in self._counters.items()},
            "gauges": {key: gauge.value for key, gauge in self._gauges.items()},
            "histograms": {
                key: histogram.statistics() for key, histogram in self._histograms.items()
            },
        }

    def reset(self):
        """
        Reset all metrics.
        """
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        self._timers.clear()

    @staticmethod
    def _make_key(name: str, tags: Optional[Dict[str, str]] = None) -> str:
        """
        Create metric key from name and tags.
        """
        if not tags:
            return name

        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}{{{tag_str}}}"


# ============================================================================
# Metric Aggregation
# ============================================================================


class MetricsAggregator:
    """Aggregate metrics over time windows.

    Example:
        aggregator = MetricsAggregator(window_seconds=60)

        # Record metrics
        for i in range(100):
            aggregator.record("requests", 1)

        # Get aggregated stats
        stats = aggregator.aggregate("requests")
    """

    def __init__(self, window_seconds: int = 60):
        """Initialize aggregator.

        Args:
            window_seconds: Time window for aggregation
        """
        self.window_seconds = window_seconds
        self._metrics: Dict[str, List[MetricValue]] = defaultdict(list)

    def record(self, name: str, value: Union[int, float], tags: Optional[Dict[str, str]] = None):
        """Record a metric value.

        Args:
            name: Metric name
            value: Metric value
            tags: Optional tags
        """
        metric = MetricValue(name=name, value=value, tags=tags or {})
        self._metrics[name].append(metric)

        # Clean old metrics
        self._clean_old_metrics(name)

    def aggregate(self, name: str) -> Dict[str, Any]:
        """Aggregate metrics for a name.

        Args:
            name: Metric name

        Returns:
            Aggregated statistics
        """
        self._clean_old_metrics(name)

        values = [m.value for m in self._metrics[name]]

        if not values:
            return {
                "count": 0,
                "sum": 0,
                "min": 0,
                "max": 0,
                "mean": 0,
            }

        return {
            "count": len(values),
            "sum": sum(values),
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / len(values),
        }

    def _clean_old_metrics(self, name: str):
        """
        Remove metrics outside time window.
        """
        cutoff = time.time() - self.window_seconds
        self._metrics[name] = [m for m in self._metrics[name] if m.timestamp > cutoff]


# ============================================================================
# Metrics Reporter
# ============================================================================


class MetricsReporter:
    """Format and report metrics.

    Example:
        collector = MetricsCollector()
        # ... collect metrics ...

        reporter = MetricsReporter(collector)
        print(reporter.format_text())
    """

    def __init__(self, collector: MetricsCollector):
        """Initialize reporter.

        Args:
            collector: MetricsCollector instance
        """
        self.collector = collector

    def format_text(self) -> str:
        """Format metrics as plain text.

        Returns:
            Formatted metrics string
        """
        metrics = self.collector.get_metrics()
        lines = ["=== Metrics Report ===\n"]

        # Counters
        if metrics["counters"]:
            lines.append("Counters:")
            for name, value in metrics["counters"].items():
                lines.append(f"  {name}: {value}")
            lines.append("")

        # Gauges
        if metrics["gauges"]:
            lines.append("Gauges:")
            for name, value in metrics["gauges"].items():
                lines.append(f"  {name}: {value:.2f}")
            lines.append("")

        # Histograms
        if metrics["histograms"]:
            lines.append("Histograms:")
            for name, stats in metrics["histograms"].items():
                lines.append(f"  {name}:")
                lines.append(f"    count: {stats['count']}")
                lines.append(f"    min: {stats['min']:.3f}")
                lines.append(f"    max: {stats['max']:.3f}")
                lines.append(f"    mean: {stats['mean']:.3f}")
                lines.append(f"    median: {stats['median']:.3f}")
                lines.append(f"    p95: {stats['p95']:.3f}")
                lines.append(f"    p99: {stats['p99']:.3f}")
            lines.append("")

        return "\n".join(lines)

    def format_json(self) -> Dict[str, Any]:
        """Format metrics as JSON-serializable dict.

        Returns:
            Metrics dictionary
        """
        return self.collector.get_metrics()

    def log_metrics(self):
        """
        Log metrics using logger.
        """
        logger.info(self.format_text())


__all__ = [
    "MetricValue",
    "Counter",
    "Gauge",
    "Histogram",
    "MetricsCollector",
    "MetricsAggregator",
    "MetricsReporter",
]
