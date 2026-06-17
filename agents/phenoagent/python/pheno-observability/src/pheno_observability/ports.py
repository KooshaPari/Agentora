"""
Observability Ports - Abstract interfaces for observability integrations.

This module defines ports (interfaces) for metrics collection, alerting,
and monitoring to enable pluggable implementations across different backends
(Prometheus, OpenTelemetry, CloudWatch, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable


class MetricType(StrEnum):
    """
    Types of metrics that can be collected.
    """

    COUNTER = "counter"  # Monotonically increasing counter
    GAUGE = "gauge"  # Value that can go up or down
    HISTOGRAM = "histogram"  # Distribution of values
    SUMMARY = "summary"  # Summary statistics


class AlertSeverity(StrEnum):
    """
    Severity levels for alerts.
    """

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ExportFormat(StrEnum):
    """
    Export formats for metrics.
    """

    PROMETHEUS = "prometheus"
    OPENTELEMETRY = "opentelemetry"
    CLOUDWATCH = "cloudwatch"
    JSON = "json"
    CUSTOM = "custom"


@dataclass
class MetricData:
    """
    Standardized metric data structure.
    """

    name: str
    value: float
    metric_type: MetricType
    timestamp: float
    labels: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricQuery:
    """
    Query for retrieving metrics.
    """

    metric_name: str
    start_time: float | None = None
    end_time: float | None = None
    labels: dict[str, str] = field(default_factory=dict)
    aggregation: str | None = None  # avg, sum, min, max, etc.


@dataclass
class Alert:
    """
    Alert data structure.
    """

    alert_type: str
    severity: AlertSeverity
    message: str
    timestamp: float
    source: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DashboardConfig:
    """
    Configuration for dashboard generation.
    """

    name: str
    metrics: list[str]
    refresh_interval_seconds: int = 60
    layout: dict[str, Any] = field(default_factory=dict)
    filters: dict[str, str] = field(default_factory=dict)


@runtime_checkable
class MetricsCollectorPort(Protocol):
    """
    Port for metrics collection implementations.
    """

    def record_counter(
        self,
        name: str,
        value: float = 1.0,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Record a counter metric.

        Args:
            name: Metric name
            value: Counter increment value (default 1.0)
            labels: Optional labels/tags for the metric
        """
        ...

    def record_gauge(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Record a gauge metric.

        Args:
            name: Metric name
            value: Current gauge value
            labels: Optional labels/tags for the metric
        """
        ...

    def record_histogram(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Record a histogram metric.

        Args:
            name: Metric name
            value: Value to add to histogram
            labels: Optional labels/tags for the metric
        """
        ...

    async def query_metrics(
        self,
        query: MetricQuery,
    ) -> list[MetricData]:
        """Query metrics based on criteria.

        Args:
            query: Query parameters

        Returns:
            List of matching metrics
        """
        ...

    def get_all_metrics(self) -> list[MetricData]:
        """Get all collected metrics.

        Returns:
            List of all metrics
        """
        ...


@runtime_checkable
class MetricsExporterPort(Protocol):
    """
    Port for metrics export implementations.
    """

    async def export(
        self,
        metrics: list[MetricData],
        format: ExportFormat,
    ) -> str | bytes:
        """Export metrics in specified format.

        Args:
            metrics: Metrics to export
            format: Target format

        Returns:
            Formatted metrics data
        """
        ...

    def supports_format(self, format: ExportFormat) -> bool:
        """Check if format is supported.

        Args:
            format: Format to check

        Returns:
            True if supported
        """
        ...

    async def push_to_backend(
        self,
        metrics: list[MetricData],
        endpoint: str,
    ) -> bool:
        """Push metrics to backend endpoint.

        Args:
            metrics: Metrics to push
            endpoint: Backend endpoint URL

        Returns:
            True if successful
        """
        ...


@runtime_checkable
class AlertingPort(Protocol):
    """
    Port for alerting implementations.
    """

    def configure_rule(
        self,
        rule_name: str,
        condition: str,
        severity: AlertSeverity,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Configure an alerting rule.

        Args:
            rule_name: Unique rule identifier
            condition: Condition expression (e.g., "value > threshold")
            severity: Alert severity level
            metadata: Additional rule configuration
        """
        ...

    async def evaluate_rules(
        self,
        metrics: list[MetricData],
    ) -> list[Alert]:
        """Evaluate alerting rules against metrics.

        Args:
            metrics: Metrics to evaluate

        Returns:
            List of triggered alerts
        """
        ...

    async def send_alert(
        self,
        alert: Alert,
        channels: list[str] | None = None,
    ) -> bool:
        """Send alert to notification channels.

        Args:
            alert: Alert to send
            channels: Optional list of channels (email, slack, etc.)

        Returns:
            True if sent successfully
        """
        ...

    def get_active_alerts(self) -> list[Alert]:
        """Get currently active alerts.

        Returns:
            List of active alerts
        """
        ...


@runtime_checkable
class DashboardPort(Protocol):
    """
    Port for dashboard generation implementations.
    """

    async def generate_dashboard(
        self,
        config: DashboardConfig,
    ) -> dict[str, Any]:
        """Generate dashboard data.

        Args:
            config: Dashboard configuration

        Returns:
            Dashboard data structure
        """
        ...

    def add_panel(
        self,
        dashboard_name: str,
        panel_name: str,
        metrics: list[str],
        visualization_type: str = "timeseries",
    ) -> None:
        """Add a panel to dashboard.

        Args:
            dashboard_name: Target dashboard
            panel_name: Panel identifier
            metrics: Metrics to display
            visualization_type: Chart type (timeseries, gauge, etc.)
        """
        ...

    async def get_dashboard_data(
        self,
        dashboard_name: str,
        time_range: tuple[float, float] | None = None,
    ) -> dict[str, Any]:
        """Get current dashboard data.

        Args:
            dashboard_name: Dashboard identifier
            time_range: Optional time range (start, end)

        Returns:
            Dashboard data with all panels
        """
        ...


@runtime_checkable
class AnomalyDetectorPort(Protocol):
    """
    Port for anomaly detection implementations.
    """

    def configure_threshold(
        self,
        metric_name: str,
        min_value: float | None = None,
        max_value: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Configure threshold-based anomaly detection.

        Args:
            metric_name: Metric to monitor
            min_value: Minimum acceptable value
            max_value: Maximum acceptable value
            metadata: Additional configuration
        """
        ...

    async def detect_anomalies(
        self,
        metrics: list[MetricData],
    ) -> list[Alert]:
        """Detect anomalies in metrics.

        Args:
            metrics: Metrics to analyze

        Returns:
            List of anomaly alerts
        """
        ...

    def train_model(
        self,
        metric_name: str,
        historical_data: list[MetricData],
    ) -> None:
        """Train anomaly detection model on historical data.

        Args:
            metric_name: Metric to train on
            historical_data: Historical metric data
        """
        ...
