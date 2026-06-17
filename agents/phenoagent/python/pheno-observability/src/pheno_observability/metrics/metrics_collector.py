"""Advanced metrics collector with anomaly detection and alerting.

This module provides the AdvancedMetricsCollector class that tracks comprehensive
metrics across multiple domains and provides real-time anomaly detection.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from pheno.observability.ports import (
    Alert,
    AlertingPort,
    AlertSeverity,
    DashboardConfig,
    DashboardPort,
    MetricData,
)

from .metrics_aggregation import AggregatedMetrics

if TYPE_CHECKING:
    from collections.abc import Callable


class AdvancedMetricsCollector:
    """Advanced metrics collector with anomaly detection and alerting.

    This collector tracks comprehensive metrics across multiple domains and
    provides real-time anomaly detection, alerting, and dashboard data generation.

    Attributes:
        metrics: Aggregated metrics container
        anomaly_thresholds: Configurable anomaly detection thresholds
        alerting: Optional alerting port for sending alerts
        dashboard: Optional dashboard port for visualization
    """

    def __init__(
        self,
        alerting: AlertingPort | None = None,
        dashboard: DashboardPort | None = None,
    ):
        """Initialize metrics collector.

        Args:
            alerting: Optional alerting port for notifications
            dashboard: Optional dashboard port for visualization
        """
        self.metrics = AggregatedMetrics()
        self._anomaly_thresholds: dict[str, float] = {
            "token_savings_min_pct": 30.0,
            "compression_ratio_min": 0.5,
            "quality_min": 0.5,
            "confidence_min": 0.5,
            "latency_max_ms": 5000.0,
            "success_rate_min_pct": 90.0,
        }
        self._alerts: list[Alert] = []
        self._alerting = alerting
        self._dashboard = dashboard
        self._custom_metric_handlers: dict[str, Callable] = {}

    def configure_thresholds(self, thresholds: dict[str, float]) -> None:
        """Configure anomaly detection thresholds.

        Args:
            thresholds: Dictionary of threshold names to values
        """
        self._anomaly_thresholds.update(thresholds)

    def register_custom_metric_handler(
        self,
        metric_name: str,
        handler: Callable,
    ) -> None:
        """Register a custom metric handler.

        Args:
            metric_name: Name of the custom metric
            handler: Callable that processes the metric
        """
        self._custom_metric_handlers[metric_name] = handler

    def record_token_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str | None = None,
        cached_tokens: int = 0,
        savings_tokens: int = 0,
        compression_ratio: float | None = None,
    ) -> None:
        """Record token usage metrics.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Optional model name
            cached_tokens: Number of cached tokens
            savings_tokens: Tokens saved through optimizations
            compression_ratio: Compression ratio achieved
        """
        tm = self.metrics.token_metrics
        tm.total_requests += 1
        tm.total_input_tokens += input_tokens
        tm.total_output_tokens += output_tokens
        tm.total_cached_tokens += cached_tokens
        tm.total_savings_tokens += savings_tokens

        if model:
            tm.per_model_tokens[model]["input"] += input_tokens
            tm.per_model_tokens[model]["output"] += output_tokens

        if compression_ratio is not None:
            tm.compression_ratios.append(compression_ratio)
            n = len(tm.compression_ratios)
            tm.average_compression_ratio = (
                tm.average_compression_ratio * (n - 1) + compression_ratio
            ) / n

            if compression_ratio < self._anomaly_thresholds["compression_ratio_min"]:
                self._add_alert(
                    alert_type="low_compression",
                    severity=AlertSeverity.WARNING,
                    message=f"Compression ratio {compression_ratio:.2%} below threshold "
                    f"{self._anomaly_thresholds['compression_ratio_min']:.2%}",
                    metadata={"compression_ratio": compression_ratio, "model": model},
                )

        self.metrics.last_updated = time.time()

    def record_quality_metrics(
        self,
        quality_score: float | None = None,
        accuracy_score: float | None = None,
        relevance_score: float | None = None,
        confidence_score: float | None = None,
    ) -> None:
        """Record quality metrics.

        Args:
            quality_score: Overall quality score (0-1)
            accuracy_score: Accuracy score (0-1)
            relevance_score: Relevance score (0-1)
            confidence_score: Confidence score (0-1)
        """
        qm = self.metrics.quality_metrics
        qm.total_measurements += 1

        if quality_score is not None:
            qm.quality_scores.append(quality_score)
            n = len(qm.quality_scores)
            qm.average_quality = (qm.average_quality * (n - 1) + quality_score) / n

            if quality_score < self._anomaly_thresholds["quality_min"]:
                self._add_alert(
                    alert_type="low_quality",
                    severity=AlertSeverity.WARNING,
                    message=f"Quality score {quality_score:.2%} below threshold",
                    metadata={"quality_score": quality_score},
                )

        if accuracy_score is not None:
            qm.accuracy_scores.append(accuracy_score)
            n = len(qm.accuracy_scores)
            qm.average_accuracy = (qm.average_accuracy * (n - 1) + accuracy_score) / n

        if relevance_score is not None:
            qm.relevance_scores.append(relevance_score)
            n = len(qm.relevance_scores)
            qm.average_relevance = (
                qm.average_relevance * (n - 1) + relevance_score
            ) / n

        if confidence_score is not None:
            qm.confidence_scores.append(confidence_score)
            n = len(qm.confidence_scores)
            qm.average_confidence = (
                qm.average_confidence * (n - 1) + confidence_score
            ) / n

            if confidence_score < self._anomaly_thresholds["confidence_min"]:
                self._add_alert(
                    alert_type="low_confidence",
                    severity=AlertSeverity.WARNING,
                    message=f"Confidence score {confidence_score:.2%} below threshold",
                    metadata={"confidence_score": confidence_score},
                )

        self.metrics.last_updated = time.time()

    def record_performance(
        self,
        latency_ms: float,
        success: bool,
        throughput_rps: float | None = None,
    ) -> None:
        """Record performance metrics.

        Args:
            latency_ms: Request latency in milliseconds
            success: Whether the request succeeded
            throughput_rps: Throughput in requests per second
        """
        pm = self.metrics.performance_metrics
        pm.total_requests += 1

        if success:
            pm.successful_requests += 1
            pm.total_latency_ms += latency_ms
            pm.latencies.append(latency_ms)

            if latency_ms > self._anomaly_thresholds["latency_max_ms"]:
                self._add_alert(
                    alert_type="high_latency",
                    severity=AlertSeverity.WARNING,
                    message=f"Request latency {latency_ms:.1f}ms above threshold",
                    metadata={"latency_ms": latency_ms},
                )
        else:
            pm.failed_requests += 1

        if throughput_rps is not None:
            pm.throughput_per_second = throughput_rps

        success_rate = (pm.successful_requests / pm.total_requests) * 100
        if success_rate < self._anomaly_thresholds["success_rate_min_pct"]:
            self._add_alert(
                alert_type="low_success_rate",
                severity=AlertSeverity.ERROR,
                message=f"Success rate {success_rate:.1f}% below threshold",
                metadata={
                    "success_rate_pct": success_rate,
                    "total_requests": pm.total_requests,
                    "failed_requests": pm.failed_requests,
                },
            )

        self.metrics.last_updated = time.time()

    def record_routing(
        self,
        model: str,
        confidence: float,
        success: bool,
        is_fallback: bool = False,
        routing_latency_ms: float | None = None,
        method_votes: dict[str, str] | None = None,
    ) -> None:
        """Record routing decision metrics.

        Args:
            model: Selected model
            confidence: Routing confidence score
            success: Whether routing succeeded
            is_fallback: Whether this was a fallback route
            routing_latency_ms: Time taken for routing decision
            method_votes: Votes from different routing methods
        """
        rm = self.metrics.routing_metrics
        rm.total_routes += 1

        if success:
            rm.successful_routes += 1
        else:
            rm.failed_routes += 1

        if is_fallback:
            rm.fallback_routes += 1

        rm.model_selections[model] += 1
        rm.confidence_scores.append(confidence)
        n = len(rm.confidence_scores)
        rm.average_confidence = (rm.average_confidence * (n - 1) + confidence) / n

        if routing_latency_ms is not None:
            rm.routing_latencies.append(routing_latency_ms)

        if method_votes:
            for method, voted_model in method_votes.items():
                rm.method_votes[f"{method}:{voted_model}"] += 1

        self.metrics.last_updated = time.time()

    def record_custom_metric(self, metric_name: str, value: Any) -> None:
        """Record a custom metric.

        Args:
            metric_name: Name of the custom metric
            value: Metric value
        """
        self.metrics.custom_metrics[metric_name] = value

        if metric_name in self._custom_metric_handlers:
            self._custom_metric_handlers[metric_name](value)

        self.metrics.last_updated = time.time()

    def _add_alert(
        self,
        alert_type: str,
        severity: AlertSeverity,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add an anomaly alert.

        Args:
            alert_type: Type of alert
            severity: Alert severity level
            message: Alert message
            metadata: Additional alert data
        """
        alert = Alert(
            alert_type=alert_type,
            severity=severity,
            message=message,
            timestamp=time.time(),
            source="AdvancedMetricsCollector",
            metadata=metadata or {},
        )
        self._alerts.append(alert)

        if self._alerting:
            import asyncio

            try:
                asyncio.create_task(self._alerting.send_alert(alert))
            except RuntimeError:
                pass

        if len(self._alerts) > 1000:
            self._alerts = self._alerts[-1000:]

    def get_summary(self) -> dict[str, Any]:
        """Get comprehensive metrics summary.

        Returns:
            Summary dictionary with all metrics
        """
        return self.metrics.get_summary()

    def get_alerts(
        self,
        since: float | None = None,
        severity: AlertSeverity | None = None,
        limit: int = 100,
    ) -> list[Alert]:
        """Get recent anomaly alerts.

        Args:
            since: Unix timestamp to filter alerts
            severity: Filter by severity level
            limit: Maximum number of alerts to return

        Returns:
            List of alerts
        """
        filtered_alerts = self._alerts

        if since:
            filtered_alerts = [a for a in filtered_alerts if a.timestamp >= since]

        if severity:
            filtered_alerts = [a for a in filtered_alerts if a.severity == severity]

        return filtered_alerts[-limit:]

    async def get_dashboard_data(self) -> dict[str, Any]:
        """Get formatted data for dashboard display.

        Returns:
            Dashboard data with visualizations
        """
        summary = self.get_summary()

        dashboard_data = {
            **summary,
            "alerts": [
                {
                    "type": a.alert_type,
                    "severity": a.severity.value,
                    "message": a.message,
                    "timestamp": a.timestamp,
                    "metadata": a.metadata,
                }
                for a in self.get_alerts(limit=20)
            ],
            "trends": {
                "compression_ratios": self.metrics.token_metrics.compression_ratios[
                    -50:
                ],
                "quality_scores": self.metrics.quality_metrics.quality_scores[-50:],
                "latencies": self.metrics.performance_metrics.latencies[-50:],
                "confidence_scores": self.metrics.routing_metrics.confidence_scores[
                    -50:
                ],
            },
        }

        if self._dashboard:
            config = DashboardConfig(
                name="advanced_metrics",
                metrics=[
                    "token_usage",
                    "quality",
                    "performance",
                    "routing",
                ],
            )
            dashboard_layout = await self._dashboard.generate_dashboard(config)
            dashboard_data["layout"] = dashboard_layout

        return dashboard_data

    def reset_metrics(self) -> None:
        """Reset all metrics (for testing or new measurement period)."""
        self.metrics = AggregatedMetrics()
        self._alerts.clear()

    def export_metrics(self) -> list[MetricData]:
        """Export metrics in standardized format.

        Returns:
            List of MetricData objects
        """
        timestamp = time.time()
        metrics_list: list[MetricData] = []

        metrics_list.extend(self.metrics.token_metrics.to_metric_data(timestamp))
        metrics_list.extend(self.metrics.quality_metrics.to_metric_data(timestamp))
        metrics_list.extend(self.metrics.performance_metrics.to_metric_data(timestamp))
        metrics_list.extend(self.metrics.routing_metrics.to_metric_data(timestamp))
        metrics_list.extend(self.metrics.health_metrics.to_metric_data(timestamp))
        metrics_list.extend(self.metrics.system_metrics.to_metric_data(timestamp))

        return metrics_list


_metrics_collector: AdvancedMetricsCollector | None = None


def get_metrics_collector() -> AdvancedMetricsCollector:
    """Get or create the global metrics collector.

    Returns:
        AdvancedMetricsCollector instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = AdvancedMetricsCollector()
    return _metrics_collector


def reset_metrics_collector() -> None:
    """Reset the global metrics collector (for testing)."""
    global _metrics_collector
    _metrics_collector = None
