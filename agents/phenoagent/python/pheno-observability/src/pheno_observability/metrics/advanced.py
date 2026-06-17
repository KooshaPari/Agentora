"""Advanced Metrics and Observability Framework.

This module provides comprehensive metrics tracking for various system aspects:
- Token usage and cost tracking
- Performance metrics (latency, throughput)
- Quality metrics (accuracy, relevance)
- System health and resource utilization
- Custom domain-specific metrics

The framework is backend-agnostic and supports multiple exporters
(Prometheus, OpenTelemetry, CloudWatch, etc.).
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pheno.observability.ports import (
    Alert,
    AlertingPort,
    AlertSeverity,
    DashboardConfig,
    DashboardPort,
    MetricData,
    MetricType,
)

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class TokenMetrics:
    """Metrics for token usage tracking.

    Tracks token consumption across input/output and calculates savings from
    optimizations like context folding or caching.
    """

    total_requests: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cached_tokens: int = 0
    total_savings_tokens: int = 0
    average_compression_ratio: float = 0.0
    compression_ratios: list[float] = field(default_factory=list)
    per_model_tokens: dict[str, dict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: {"input": 0, "output": 0}),
    )

    def calculate_savings(self, cost_per_1k_tokens: float = 0.01) -> dict[str, Any]:
        """Calculate cost savings from optimizations.

        Args:
            cost_per_1k_tokens: Cost per 1000 tokens (default $0.01)

        Returns:
            Dictionary with savings statistics
        """
        if self.total_input_tokens == 0:
            return {
                "token_savings_pct": 0.0,
                "cost_savings_pct": 0.0,
                "total_cost_saved_usd": 0.0,
            }

        # Calculate token savings percentage
        original_tokens = self.total_input_tokens + self.total_savings_tokens
        token_savings_pct = (
            (self.total_savings_tokens / original_tokens) * 100 if original_tokens > 0 else 0.0
        )

        # Calculate cost savings
        input_cost = (self.total_input_tokens / 1000) * cost_per_1k_tokens
        saved_cost = (self.total_savings_tokens / 1000) * cost_per_1k_tokens
        cost_savings_pct = (
            (saved_cost / (input_cost + saved_cost)) * 100 if (input_cost + saved_cost) > 0 else 0.0
        )

        return {
            "token_savings_pct": token_savings_pct,
            "cost_savings_pct": cost_savings_pct,
            "total_cost_saved_usd": saved_cost,
            "total_cost_usd": input_cost,
        }

    def get_model_breakdown(self) -> dict[str, dict[str, int]]:
        """Get token usage breakdown by model.

        Returns:
            Dictionary mapping model names to token counts
        """
        return dict(self.per_model_tokens)


@dataclass
class QualityMetrics:
    """Metrics for tracking quality and accuracy.

    Used for ensemble routing, A/B testing, and quality monitoring.
    """

    total_measurements: int = 0
    quality_scores: list[float] = field(default_factory=list)
    average_quality: float = 0.0
    accuracy_scores: list[float] = field(default_factory=list)
    average_accuracy: float = 0.0
    relevance_scores: list[float] = field(default_factory=list)
    average_relevance: float = 0.0
    confidence_scores: list[float] = field(default_factory=list)
    average_confidence: float = 0.0

    def calculate_improvement(self, baseline_quality: float = 0.7) -> dict[str, Any]:
        """Calculate quality improvement over baseline.

        Args:
            baseline_quality: Baseline quality score

        Returns:
            Dictionary with improvement statistics
        """
        if not self.quality_scores:
            return {
                "quality_improvement_pct": 0.0,
                "average_quality": 0.0,
                "baseline_quality": baseline_quality,
            }

        avg_quality = sum(self.quality_scores) / len(self.quality_scores)
        improvement_pct = (
            ((avg_quality - baseline_quality) / baseline_quality) * 100
            if baseline_quality > 0
            else 0.0
        )

        return {
            "quality_improvement_pct": improvement_pct,
            "average_quality": avg_quality,
            "baseline_quality": baseline_quality,
            "confidence": self.average_confidence,
            "measurements": self.total_measurements,
        }


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

    def calculate_improvements(self, baseline_latency_ms: float = 1000.0) -> dict[str, Any]:
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

        # Calculate percentiles
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
            (self.successful_routes / self.total_routes) * 100 if self.total_routes > 0 else 0.0
        )
        fallback_rate = (
            (self.fallback_routes / self.total_routes) * 100 if self.total_routes > 0 else 0.0
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


@dataclass
class AggregatedMetrics:
    """Aggregated metrics across all tracking categories.

    This is the main metrics container that combines all metric types and provides
    comprehensive summaries.
    """

    token_metrics: TokenMetrics = field(default_factory=TokenMetrics)
    quality_metrics: QualityMetrics = field(default_factory=QualityMetrics)
    performance_metrics: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    routing_metrics: RoutingMetrics = field(default_factory=RoutingMetrics)
    custom_metrics: dict[str, Any] = field(default_factory=dict)

    start_time: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)

    def get_summary(self) -> dict[str, Any]:
        """Get comprehensive summary of all metrics.

        Returns:
            Summary dictionary with all improvements and statistics
        """
        uptime_seconds = time.time() - self.start_time

        # Calculate individual improvements
        token_savings = self.token_metrics.calculate_savings()
        quality_improvement = self.quality_metrics.calculate_improvement()
        performance_improvement = self.performance_metrics.calculate_improvements()
        routing_effectiveness = self.routing_metrics.get_routing_effectiveness()

        return {
            "overview": {
                "uptime_seconds": uptime_seconds,
                "uptime_hours": uptime_seconds / 3600,
                "last_updated": time.ctime(self.last_updated),
                "last_updated_timestamp": self.last_updated,
            },
            "token_usage": {
                "total_requests": self.token_metrics.total_requests,
                "total_input_tokens": self.token_metrics.total_input_tokens,
                "total_output_tokens": self.token_metrics.total_output_tokens,
                "token_savings_pct": token_savings["token_savings_pct"],
                "cost_saved_usd": token_savings["total_cost_saved_usd"],
                "total_cost_usd": token_savings["total_cost_usd"],
                "model_breakdown": self.token_metrics.get_model_breakdown(),
            },
            "quality": {
                "quality_improvement_pct": quality_improvement["quality_improvement_pct"],
                "average_quality": quality_improvement["average_quality"],
                "average_confidence": self.quality_metrics.average_confidence,
                "total_measurements": self.quality_metrics.total_measurements,
            },
            "performance": {
                "total_requests": self.performance_metrics.total_requests,
                "success_rate_pct": performance_improvement["success_rate_pct"],
                "latency_reduction_pct": performance_improvement["latency_reduction_pct"],
                "average_latency_ms": performance_improvement["average_latency_ms"],
                "p50_latency_ms": performance_improvement["p50_latency_ms"],
                "p95_latency_ms": performance_improvement["p95_latency_ms"],
                "p99_latency_ms": performance_improvement["p99_latency_ms"],
            },
            "routing": routing_effectiveness,
            "custom": self.custom_metrics,
        }


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

    def register_custom_metric_handler(self, metric_name: str, handler: Callable) -> None:
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

            # Check for anomalies
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
            qm.average_relevance = (qm.average_relevance * (n - 1) + relevance_score) / n

        if confidence_score is not None:
            qm.confidence_scores.append(confidence_score)
            n = len(qm.confidence_scores)
            qm.average_confidence = (qm.average_confidence * (n - 1) + confidence_score) / n

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

        # Check success rate
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

        # Call custom handler if registered
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

        # Send to alerting port if configured
        if self._alerting:
            import asyncio

            try:
                asyncio.create_task(self._alerting.send_alert(alert))
            except RuntimeError:
                # No event loop, skip async alert
                pass

        # Keep only recent alerts
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
                "compression_ratios": self.metrics.token_metrics.compression_ratios[-50:],
                "quality_scores": self.metrics.quality_metrics.quality_scores[-50:],
                "latencies": self.metrics.performance_metrics.latencies[-50:],
                "confidence_scores": self.metrics.routing_metrics.confidence_scores[-50:],
            },
        }

        # Generate dashboard if port configured
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
        """
        Reset all metrics (for testing or new measurement period).
        """
        self.metrics = AggregatedMetrics()
        self._alerts.clear()

    def export_metrics(self) -> list[MetricData]:
        """Export metrics in standardized format.

        Returns:
            List of MetricData objects
        """
        timestamp = time.time()
        metrics_list: list[MetricData] = []

        # Token metrics
        metrics_list.extend(
            [
                MetricData(
                    name="token.input.total",
                    value=float(self.metrics.token_metrics.total_input_tokens),
                    metric_type=MetricType.COUNTER,
                    timestamp=timestamp,
                ),
                MetricData(
                    name="token.output.total",
                    value=float(self.metrics.token_metrics.total_output_tokens),
                    metric_type=MetricType.COUNTER,
                    timestamp=timestamp,
                ),
                MetricData(
                    name="token.savings.total",
                    value=float(self.metrics.token_metrics.total_savings_tokens),
                    metric_type=MetricType.COUNTER,
                    timestamp=timestamp,
                ),
            ],
        )

        # Quality metrics
        if self.metrics.quality_metrics.average_quality > 0:
            metrics_list.append(
                MetricData(
                    name="quality.average",
                    value=self.metrics.quality_metrics.average_quality,
                    metric_type=MetricType.GAUGE,
                    timestamp=timestamp,
                ),
            )

        # Performance metrics
        if self.metrics.performance_metrics.latencies:
            avg_latency = sum(self.metrics.performance_metrics.latencies) / len(
                self.metrics.performance_metrics.latencies,
            )
            metrics_list.append(
                MetricData(
                    name="performance.latency.average",
                    value=avg_latency,
                    metric_type=MetricType.GAUGE,
                    timestamp=timestamp,
                ),
            )

        # Success rate
        if self.metrics.performance_metrics.total_requests > 0:
            success_rate = (
                self.metrics.performance_metrics.successful_requests
                / self.metrics.performance_metrics.total_requests
            )
            metrics_list.append(
                MetricData(
                    name="performance.success_rate",
                    value=success_rate,
                    metric_type=MetricType.GAUGE,
                    timestamp=timestamp,
                ),
            )

        return metrics_list


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
            # Format metric name
            prom_name = metric.name.replace(".", "_")

            # Add labels if present
            labels_str = ""
            if metric.labels:
                labels = ",".join(f'{k}="{v}"' for k, v in metric.labels.items())
                labels_str = f"{{{labels}}}"

            # Add metric line
            lines.append(f"{prom_name}{labels_str} {metric.value} {int(metric.timestamp * 1000)}")

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
                            {"key": "service.name", "value": {"stringValue": "pheno-sdk"}},
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
        """
        Convert MetricData to OTLP metric format.
        """
        otlp_metric: dict[str, Any] = {
            "name": metric.name,
            "description": metric.metadata.get("description", ""),
        }

        # Add data points based on metric type
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

            async with aiohttp.ClientSession() as session, session.post(
                url,
                json=data,
                headers={"Content-Type": "application/json"},
            ) as resp:
                return resp.status == 200
        except Exception:
            return False


class CloudWatchBackend:
    """AWS CloudWatch metrics backend adapter.

    Exports metrics to AWS CloudWatch using the PutMetricData API.
    """

    def __init__(
        self,
        namespace: str = "PhenoSDK",
        region: str = "us-east-1",
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
    ):
        """Initialize CloudWatch backend.

        Args:
            namespace: CloudWatch namespace
            region: AWS region
            aws_access_key_id: Optional AWS access key
            aws_secret_access_key: Optional AWS secret key
        """
        self.namespace = namespace
        self.region = region
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key

    async def export(self, metrics: list[MetricData]) -> list[dict[str, Any]]:
        """Export metrics in CloudWatch format.

        Args:
            metrics: Metrics to export

        Returns:
            List of CloudWatch metric data dictionaries
        """
        metric_data = []

        for metric in metrics:
            cw_metric = {
                "MetricName": metric.name.replace(".", "/"),
                "Value": metric.value,
                "Timestamp": metric.timestamp,
                "Unit": metric.metadata.get("unit", "None"),
            }

            # Add dimensions (CloudWatch equivalent of labels)
            if metric.labels:
                cw_metric["Dimensions"] = [
                    {"Name": k, "Value": v} for k, v in metric.labels.items()
                ]

            metric_data.append(cw_metric)

        return metric_data

    async def push(self, metrics: list[MetricData]) -> bool:
        """Push metrics to CloudWatch.

        Args:
            metrics: Metrics to push

        Returns:
            True if successful
        """
        try:
            # Try to import boto3
            import boto3

            # Create CloudWatch client
            session_kwargs: dict[str, Any] = {"region_name": self.region}
            if self.aws_access_key_id and self.aws_secret_access_key:
                session_kwargs.update(
                    {
                        "aws_access_key_id": self.aws_access_key_id,
                        "aws_secret_access_key": self.aws_secret_access_key,
                    },
                )

            client = boto3.client("cloudwatch", **session_kwargs)

            # Convert metrics
            metric_data = await self.export(metrics)

            # Push in batches of 20 (CloudWatch limit)
            for i in range(0, len(metric_data), 20):
                batch = metric_data[i : i + 20]
                client.put_metric_data(Namespace=self.namespace, MetricData=batch)

            return True
        except Exception:
            return False


class DatadogBackend:
    """Datadog metrics backend adapter.

    Exports metrics to Datadog using the Datadog API.
    """

    def __init__(
        self,
        api_key: str | None = None,
        app_key: str | None = None,
        site: str = "datadoghq.com",
    ):
        """Initialize Datadog backend.

        Args:
            api_key: Datadog API key
            app_key: Datadog application key
            site: Datadog site (e.g., datadoghq.com, datadoghq.eu)
        """
        self.api_key = api_key
        self.app_key = app_key
        self.site = site

    async def export(self, metrics: list[MetricData]) -> dict[str, Any]:
        """Export metrics in Datadog format.

        Args:
            metrics: Metrics to export

        Returns:
            Datadog-formatted metrics dictionary
        """
        series = []

        for metric in metrics:
            dd_metric = {
                "metric": metric.name,
                "points": [[metric.timestamp, metric.value]],
                "type": "gauge" if metric.metric_type == MetricType.GAUGE else "count",
            }

            # Add tags (Datadog equivalent of labels)
            if metric.labels:
                dd_metric["tags"] = [f"{k}:{v}" for k, v in metric.labels.items()]

            series.append(dd_metric)

        return {"series": series}

    async def push(self, metrics: list[MetricData]) -> bool:
        """Push metrics to Datadog.

        Args:
            metrics: Metrics to push

        Returns:
            True if successful
        """
        if not self.api_key:
            return False

        try:

            import aiohttp

            data = await self.export(metrics)
            url = f"https://api.{self.site}/api/v1/series"

            headers = {
                "DD-API-KEY": self.api_key,
                "Content-Type": "application/json",
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers) as resp:
                    return resp.status == 202
        except Exception:
            return False


# Singleton instance
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
    """
    Reset the global metrics collector (for testing).
    """
    global _metrics_collector
    _metrics_collector = None
