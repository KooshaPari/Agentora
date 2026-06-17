"""Performance metrics for tracking latency, throughput, and success rates.

This module provides PerformanceMetrics and LatencyMetrics dataclasses for
performance monitoring and anomaly detection.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from pheno.observability.ports import MetricData, MetricType


@dataclass
class LatencyMetrics:
    """Detailed latency tracking with percentile calculations.

    Provides p50, p95, p99 latency tracking and trend analysis.
    """

    latencies: list[float] = field(default_factory=list)
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    min_latency_ms: float = float("inf")
    max_latency_ms: float = 0.0
    total_latency_ms: float = 0.0

    def record(self, latency_ms: float) -> None:
        """Record a latency measurement.

        Args:
            latency_ms: Latency in milliseconds
        """
        self.latencies.append(latency_ms)
        self.total_latency_ms += latency_ms
        self.min_latency_ms = min(self.min_latency_ms, latency_ms)
        self.max_latency_ms = max(self.max_latency_ms, latency_ms)
        self._update_percentiles()

    def _update_percentiles(self) -> None:
        """Recalculate percentile values."""
        if not self.latencies:
            return

        sorted_latencies = sorted(self.latencies)
        n = len(sorted_latencies)

        self.p50_latency_ms = sorted_latencies[int(n * 0.5)] if n > 0 else 0.0
        self.p95_latency_ms = sorted_latencies[int(n * 0.95)] if n > 0 else 0.0
        self.p99_latency_ms = sorted_latencies[int(n * 0.99)] if n > 0 else 0.0

    def get_average(self) -> float:
        """Get average latency.

        Returns:
            Average latency in milliseconds
        """
        if not self.latencies:
            return 0.0
        return sum(self.latencies) / len(self.latencies)

    def to_metric_data(self, timestamp: float) -> list[MetricData]:
        """Export latency metrics as MetricData list.

        Args:
            timestamp: Unix timestamp for metrics

        Returns:
            List of MetricData objects
        """
        if not self.latencies:
            return []

        return [
            MetricData(
                name="latency.average",
                value=self.get_average(),
                metric_type=MetricType.GAUGE,
                timestamp=timestamp,
            ),
            MetricData(
                name="latency.p50",
                value=self.p50_latency_ms,
                metric_type=MetricType.GAUGE,
                timestamp=timestamp,
            ),
            MetricData(
                name="latency.p95",
                value=self.p95_latency_ms,
                metric_type=MetricType.GAUGE,
                timestamp=timestamp,
            ),
            MetricData(
                name="latency.p99",
                value=self.p99_latency_ms,
                metric_type=MetricType.GAUGE,
                timestamp=timestamp,
            ),
            MetricData(
                name="latency.min",
                value=self.min_latency_ms,
                metric_type=MetricType.GAUGE,
                timestamp=timestamp,
            ),
            MetricData(
                name="latency.max",
                value=self.max_latency_ms,
                metric_type=MetricType.GAUGE,
                timestamp=timestamp,
            ),
        ]


@dataclass
class PerformanceMetrics:
    """Metrics for performance tracking.

    Tracks latency, throughput, and resource utilization.
    """

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_latency_ms: float = 0.0
    latencies: list[float] = field(default_factory=list)
    throughput_per_second: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0

    def calculate_improvements(
        self, baseline_latency_ms: float = 1000.0,
    ) -> dict[str, Any]:
        """Calculate performance improvements over baseline.

        Args:
            baseline_latency_ms: Baseline latency in milliseconds

        Returns:
            Dictionary with improvement statistics
        """
        if not self.latencies:
            return {
                "latency_reduction_pct": 0.0,
                "average_latency_ms": 0.0,
                "success_rate_pct": 0.0,
            }

        avg_latency = sum(self.latencies) / len(self.latencies)
        latency_reduction_pct = (
            ((baseline_latency_ms - avg_latency) / baseline_latency_ms) * 100
            if baseline_latency_ms > 0
            else 0.0
        )

        success_rate = (
            (self.successful_requests / self.total_requests) * 100
            if self.total_requests > 0
            else 0.0
        )

        sorted_latencies = sorted(self.latencies)
        n = len(sorted_latencies)
        p50 = sorted_latencies[int(n * 0.5)] if n > 0 else 0.0
        p95 = sorted_latencies[int(n * 0.95)] if n > 0 else 0.0
        p99 = sorted_latencies[int(n * 0.99)] if n > 0 else 0.0

        return {
            "latency_reduction_pct": latency_reduction_pct,
            "average_latency_ms": avg_latency,
            "baseline_latency_ms": baseline_latency_ms,
            "success_rate_pct": success_rate,
            "p50_latency_ms": p50,
            "p95_latency_ms": p95,
            "p99_latency_ms": p99,
            "throughput_rps": self.throughput_per_second,
        }

    def to_metric_data(self, timestamp: float) -> list[MetricData]:
        """Export performance metrics as MetricData list.

        Args:
            timestamp: Unix timestamp for metrics

        Returns:
            List of MetricData objects
        """
        metrics: list[MetricData] = []

        if self.latencies:
            avg_latency = sum(self.latencies) / len(self.latencies)
            metrics.extend(
                [
                    MetricData(
                        name="performance.latency.average",
                        value=avg_latency,
                        metric_type=MetricType.GAUGE,
                        timestamp=timestamp,
                    ),
                    MetricData(
                        name="performance.latency.p50",
                        value=self.p50_latency_ms,
                        metric_type=MetricType.GAUGE,
                        timestamp=timestamp,
                    ),
                    MetricData(
                        name="performance.latency.p95",
                        value=self.p95_latency_ms,
                        metric_type=MetricType.GAUGE,
                        timestamp=timestamp,
                    ),
                    MetricData(
                        name="performance.latency.p99",
                        value=self.p99_latency_ms,
                        metric_type=MetricType.GAUGE,
                        timestamp=timestamp,
                    ),
                ],
            )

        if self.total_requests > 0:
            success_rate = self.successful_requests / self.total_requests
            metrics.extend(
                [
                    MetricData(
                        name="performance.success_rate",
                        value=success_rate,
                        metric_type=MetricType.GAUGE,
                        timestamp=timestamp,
                    ),
                    MetricData(
                        name="performance.requests.total",
                        value=float(self.total_requests),
                        metric_type=MetricType.COUNTER,
                        timestamp=timestamp,
                    ),
                    MetricData(
                        name="performance.requests.failed",
                        value=float(self.failed_requests),
                        metric_type=MetricType.COUNTER,
                        timestamp=timestamp,
                    ),
                ],
            )

        if self.throughput_per_second > 0:
            metrics.append(
                MetricData(
                    name="performance.throughput",
                    value=self.throughput_per_second,
                    metric_type=MetricType.GAUGE,
                    timestamp=timestamp,
                ),
            )

        return metrics


class PrometheusBackend:
    """Prometheus metrics backend adapter.

    Exports metrics in Prometheus exposition format and supports pushing to Prometheus
    Pushgateway.
    """

    def __init__(self, endpoint: str | None = None):
        """Initialize Prometheus backend.

        Args:
            endpoint: Optional Pushgateway endpoint
        """
        self.endpoint = endpoint

    async def export(self, metrics: list[MetricData]) -> str:
        """Export metrics in Prometheus format.

        Args:
            metrics: Metrics to export

        Returns:
            Prometheus-formatted metrics string
        """
        lines: list[str] = []

        for metric in metrics:
            prom_name = metric.name.replace(".", "_")

            labels_str = ""
            if metric.labels:
                labels = ",".join(f'{k}="{v}"' for k, v in metric.labels.items())
                labels_str = f"{{{labels}}}"

            lines.append(
                f"{prom_name}{labels_str} {metric.value} {int(metric.timestamp * 1000)}",
            )

        return "\n".join(lines) + "\n"

    async def push(self, metrics: list[MetricData], job: str = "pheno_sdk") -> bool:
        """Push metrics to Prometheus Pushgateway.

        Args:
            metrics: Metrics to push
            job: Job label for Pushgateway

        Returns:
            True if successful
        """
        if not self.endpoint:
            return False

        try:
            import aiohttp

            data = await self.export(metrics)
            url = f"{self.endpoint}/metrics/job/{job}"

            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data) as resp:
                    return resp.status == 200
        except Exception:
            return False


class OpenTelemetryBackend:
    """OpenTelemetry metrics backend adapter.

    Exports metrics via OpenTelemetry Protocol (OTLP) to collectors like Jaeger, Zipkin,
    or the OpenTelemetry Collector.
    """

    def __init__(self, endpoint: str | None = None):
        """Initialize OpenTelemetry backend.

        Args:
            endpoint: Optional OTLP endpoint (e.g., http://localhost:4318)
        """
        self.endpoint = endpoint

    async def export(self, metrics: list[MetricData]) -> dict[str, Any]:
        """Export metrics in OTLP JSON format.

        Args:
            metrics: Metrics to export

        Returns:
            OTLP-formatted metrics dictionary
        """
        return {
            "resourceMetrics": [
                {
                    "resource": {
                        "attributes": [
                            {
                                "key": "service.name",
                                "value": {"stringValue": "pheno-sdk"},
                            },
                        ],
                    },
                    "scopeMetrics": [
                        {
                            "scope": {"name": "pheno.observability.metrics"},
                            "metrics": [self._convert_metric(m) for m in metrics],
                        },
                    ],
                },
            ],
        }

    def _convert_metric(self, metric: MetricData) -> dict[str, Any]:
        """Convert MetricData to OTLP metric format."""
        otlp_metric: dict[str, Any] = {
            "name": metric.name,
            "description": metric.metadata.get("description", ""),
        }

        if metric.metric_type == MetricType.COUNTER:
            otlp_metric["sum"] = {
                "dataPoints": [
                    {
                        "asDouble": metric.value,
                        "timeUnixNano": int(metric.timestamp * 1e9),
                        "attributes": [
                            {"key": k, "value": {"stringValue": v}}
                            for k, v in metric.labels.items()
                        ],
                    },
                ],
                "isMonotonic": True,
            }
        elif metric.metric_type == MetricType.GAUGE:
            otlp_metric["gauge"] = {
                "dataPoints": [
                    {
                        "asDouble": metric.value,
                        "timeUnixNano": int(metric.timestamp * 1e9),
                        "attributes": [
                            {"key": k, "value": {"stringValue": v}}
                            for k, v in metric.labels.items()
                        ],
                    },
                ],
            }

        return otlp_metric

    async def push(self, metrics: list[MetricData]) -> bool:
        """Push metrics to OTLP endpoint.

        Args:
            metrics: Metrics to push

        Returns:
            True if successful
        """
        if not self.endpoint:
            return False

        try:
            import aiohttp

            data = await self.export(metrics)
            url = f"{self.endpoint}/v1/metrics"

            async with (
                aiohttp.ClientSession() as session,
                session.post(
                    url,
                    json=data,
                    headers={"Content-Type": "application/json"},
                ) as resp,
            ):
                return resp.status == 200
        except Exception:
            return False
