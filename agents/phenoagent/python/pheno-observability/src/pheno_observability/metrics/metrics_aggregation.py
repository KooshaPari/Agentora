"""Aggregated metrics container.

This module provides AggregatedMetrics for combining all metric types.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .metrics_performance import PerformanceMetrics
from .metrics_quality import QualityMetrics
from .metrics_system import HealthMetrics, RoutingMetrics, SystemMetrics
from .metrics_token import TokenMetrics


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
    system_metrics: SystemMetrics = field(default_factory=SystemMetrics)
    health_metrics: HealthMetrics = field(default_factory=HealthMetrics)
    custom_metrics: dict[str, Any] = field(default_factory=dict)

    start_time: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)

    def get_summary(self) -> dict[str, Any]:
        """Get comprehensive summary of all metrics.

        Returns:
            Summary dictionary with all improvements and statistics
        """
        uptime_seconds = time.time() - self.start_time

        token_savings = self.token_metrics.calculate_savings()
        quality_improvement = self.quality_metrics.calculate_improvement()
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
                "quality_improvement_pct": quality_improvement[
                    "quality_improvement_pct"
                ],
                "average_quality": quality_improvement["average_quality"],
                "average_confidence": self.quality_metrics.average_confidence,
                "total_measurements": self.quality_metrics.total_measurements,
            },
            "routing": routing_effectiveness,
            "health": {
                "is_healthy": self.health_metrics.is_healthy,
                "is_ready": self.health_metrics.is_ready,
                "uptime_seconds": self.health_metrics.uptime_seconds,
                "consecutive_failures": self.health_metrics.consecutive_failures,
            },
            "custom": self.custom_metrics,
        }
