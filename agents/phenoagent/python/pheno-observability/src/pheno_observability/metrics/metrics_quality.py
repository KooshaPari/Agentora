"""Quality metrics for tracking accuracy, relevance, and confidence.

This module provides the QualityMetrics dataclass for ensemble routing,
A/B testing, and quality monitoring.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pheno.observability.ports import MetricData, MetricType


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

    def to_metric_data(self, timestamp: float) -> list[MetricData]:
        """Export quality metrics as MetricData list.

        Args:
            timestamp: Unix timestamp for metrics

        Returns:
            List of MetricData objects
        """
        metrics: list[MetricData] = []

        if self.average_quality > 0:
            metrics.append(
                MetricData(
                    name="quality.average",
                    value=self.average_quality,
                    metric_type=MetricType.GAUGE,
                    timestamp=timestamp,
                ),
            )

        if self.average_accuracy > 0:
            metrics.append(
                MetricData(
                    name="quality.accuracy",
                    value=self.average_accuracy,
                    metric_type=MetricType.GAUGE,
                    timestamp=timestamp,
                ),
            )

        if self.average_relevance > 0:
            metrics.append(
                MetricData(
                    name="quality.relevance",
                    value=self.average_relevance,
                    metric_type=MetricType.GAUGE,
                    timestamp=timestamp,
                ),
            )

        if self.average_confidence > 0:
            metrics.append(
                MetricData(
                    name="quality.confidence",
                    value=self.average_confidence,
                    metric_type=MetricType.GAUGE,
                    timestamp=timestamp,
                ),
            )

        metrics.append(
            MetricData(
                name="quality.measurements.total",
                value=float(self.total_measurements),
                metric_type=MetricType.COUNTER,
                timestamp=timestamp,
            ),
        )

        return metrics
