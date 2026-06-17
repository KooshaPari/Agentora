"""System and routing metrics for tracking model selection and health.

This module provides RoutingMetrics, SystemMetrics, and HealthMetrics dataclasses
for system-level monitoring.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from pheno.observability.ports import MetricData, MetricType


@dataclass
class SystemMetrics:
    """System-level resource metrics.

    Tracks CPU, memory, and other system resources.
    """

    cpu_usage_percent: float = 0.0
    memory_usage_bytes: int = 0
    memory_limit_bytes: int = 0
    disk_usage_bytes: int = 0
    network_io_bytes: int = 0
    active_connections: int = 0
    timestamps: list[float] = field(default_factory=list)

    def record(self, timestamp: float) -> None:
        """Record a system metrics snapshot.

        Args:
            timestamp: Unix timestamp for this snapshot
        """
        self.timestamps.append(timestamp)

    def get_memory_usage_percent(self) -> float:
        """Get memory usage as percentage.

        Returns:
            Memory usage percentage (0-100)
        """
        if self.memory_limit_bytes == 0:
            return 0.0
        return (self.memory_usage_bytes / self.memory_limit_bytes) * 100

    def to_metric_data(self, timestamp: float) -> list[MetricData]:
        """Export system metrics as MetricData list.

        Args:
            timestamp: Unix timestamp for metrics

        Returns:
            List of MetricData objects
        """
        return [
            MetricData(
                name="system.cpu.usage",
                value=self.cpu_usage_percent,
                metric_type=MetricType.GAUGE,
                timestamp=timestamp,
            ),
            MetricData(
                name="system.memory.usage",
                value=float(self.memory_usage_bytes),
                metric_type=MetricType.GAUGE,
                timestamp=timestamp,
            ),
            MetricData(
                name="system.memory.limit",
                value=float(self.memory_limit_bytes),
                metric_type=MetricType.GAUGE,
                timestamp=timestamp,
            ),
            MetricData(
                name="system.memory.usage_percent",
                value=self.get_memory_usage_percent(),
                metric_type=MetricType.GAUGE,
                timestamp=timestamp,
            ),
            MetricData(
                name="system.disk.usage",
                value=float(self.disk_usage_bytes),
                metric_type=MetricType.GAUGE,
                timestamp=timestamp,
            ),
            MetricData(
                name="system.network.io",
                value=float(self.network_io_bytes),
                metric_type=MetricType.COUNTER,
                timestamp=timestamp,
            ),
            MetricData(
                name="system.connections.active",
                value=float(self.active_connections),
                metric_type=MetricType.GAUGE,
                timestamp=timestamp,
            ),
        ]


@dataclass
class HealthMetrics:
    """Health check and uptime metrics.

    Tracks service health, uptime, and readiness.
    """

    is_healthy: bool = True
    is_ready: bool = True
    uptime_seconds: float = 0.0
    last_health_check: float = 0.0
    consecutive_failures: int = 0
    total_health_checks: int = 0
    failed_health_checks: int = 0

    def record_health_check(self, is_healthy: bool, timestamp: float) -> None:
        """Record a health check result.

        Args:
            is_healthy: Whether the health check passed
            timestamp: Unix timestamp of the check
        """
        self.total_health_checks += 1
        self.last_health_check = timestamp

        if is_healthy:
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1
            self.failed_health_checks += 1

        self.is_healthy = is_healthy

    def to_metric_data(self, timestamp: float) -> list[MetricData]:
        """Export health metrics as MetricData list.

        Args:
            timestamp: Unix timestamp for metrics

        Returns:
            List of MetricData objects
        """
        return [
            MetricData(
                name="health.is_healthy",
                value=1.0 if self.is_healthy else 0.0,
                metric_type=MetricType.GAUGE,
                timestamp=timestamp,
            ),
            MetricData(
                name="health.is_ready",
                value=1.0 if self.is_ready else 0.0,
                metric_type=MetricType.GAUGE,
                timestamp=timestamp,
            ),
            MetricData(
                name="health.uptime",
                value=self.uptime_seconds,
                metric_type=MetricType.GAUGE,
                timestamp=timestamp,
            ),
            MetricData(
                name="health.checks.total",
                value=float(self.total_health_checks),
                metric_type=MetricType.COUNTER,
                timestamp=timestamp,
            ),
            MetricData(
                name="health.checks.failed",
                value=float(self.failed_health_checks),
                metric_type=MetricType.COUNTER,
                timestamp=timestamp,
            ),
            MetricData(
                name="health.failures.consecutive",
                value=float(self.consecutive_failures),
                metric_type=MetricType.GAUGE,
                timestamp=timestamp,
            ),
        ]


@dataclass
class RoutingMetrics:
    """Metrics for routing decisions and effectiveness.

    Tracks model selection, routing quality, and method consensus.
    """

    total_routes: int = 0
    successful_routes: int = 0
    failed_routes: int = 0
    fallback_routes: int = 0
    model_selections: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    method_votes: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    routing_latencies: list[float] = field(default_factory=list)
    confidence_scores: list[float] = field(default_factory=list)
    average_confidence: float = 0.0

    def get_routing_effectiveness(self) -> dict[str, Any]:
        """Calculate routing effectiveness metrics.

        Returns:
            Dictionary with routing statistics
        """
        success_rate = (
            (self.successful_routes / self.total_routes) * 100
            if self.total_routes > 0
            else 0.0
        )
        fallback_rate = (
            (self.fallback_routes / self.total_routes) * 100
            if self.total_routes > 0
            else 0.0
        )
        avg_routing_latency = (
            sum(self.routing_latencies) / len(self.routing_latencies)
            if self.routing_latencies
            else 0.0
        )

        return {
            "success_rate_pct": success_rate,
            "fallback_rate_pct": fallback_rate,
            "average_confidence": self.average_confidence,
            "average_routing_latency_ms": avg_routing_latency,
            "model_distribution": dict(self.model_selections),
            "method_distribution": dict(self.method_votes),
            "total_routes": self.total_routes,
        }

    def to_metric_data(self, timestamp: float) -> list[MetricData]:
        """Export routing metrics as MetricData list.

        Args:
            timestamp: Unix timestamp for metrics

        Returns:
            List of MetricData objects
        """
        metrics: list[MetricData] = []

        if self.total_routes > 0:
            metrics.extend(
                [
                    MetricData(
                        name="routing.requests.total",
                        value=float(self.total_routes),
                        metric_type=MetricType.COUNTER,
                        timestamp=timestamp,
                    ),
                    MetricData(
                        name="routing.success.total",
                        value=float(self.successful_routes),
                        metric_type=MetricType.COUNTER,
                        timestamp=timestamp,
                    ),
                    MetricData(
                        name="routing.failed.total",
                        value=float(self.failed_routes),
                        metric_type=MetricType.COUNTER,
                        timestamp=timestamp,
                    ),
                    MetricData(
                        name="routing.fallback.total",
                        value=float(self.fallback_routes),
                        metric_type=MetricType.COUNTER,
                        timestamp=timestamp,
                    ),
                ],
            )

        if self.routing_latencies:
            avg_latency = sum(self.routing_latencies) / len(self.routing_latencies)
            metrics.append(
                MetricData(
                    name="routing.latency.average",
                    value=avg_latency,
                    metric_type=MetricType.GAUGE,
                    timestamp=timestamp,
                ),
            )

        if self.average_confidence > 0:
            metrics.append(
                MetricData(
                    name="routing.confidence.average",
                    value=self.average_confidence,
                    metric_type=MetricType.GAUGE,
                    timestamp=timestamp,
                ),
            )

        return metrics
