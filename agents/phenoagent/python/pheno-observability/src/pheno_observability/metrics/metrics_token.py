"""Token metrics for tracking usage, costs, and compression.

This module provides the TokenMetrics dataclass for tracking token consumption
across input/output and calculating savings from optimizations.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from pheno.observability.ports import MetricData, MetricType


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

        original_tokens = self.total_input_tokens + self.total_savings_tokens
        token_savings_pct = (
            (self.total_savings_tokens / original_tokens) * 100
            if original_tokens > 0
            else 0.0
        )

        input_cost = (self.total_input_tokens / 1000) * cost_per_1k_tokens
        saved_cost = (self.total_savings_tokens / 1000) * cost_per_1k_tokens
        cost_savings_pct = (
            (saved_cost / (input_cost + saved_cost)) * 100
            if (input_cost + saved_cost) > 0
            else 0.0
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

    def to_metric_data(self, timestamp: float) -> list[MetricData]:
        """Export token metrics as MetricData list.

        Args:
            timestamp: Unix timestamp for metrics

        Returns:
            List of MetricData objects
        """
        return [
            MetricData(
                name="token.input.total",
                value=float(self.total_input_tokens),
                metric_type=MetricType.COUNTER,
                timestamp=timestamp,
            ),
            MetricData(
                name="token.output.total",
                value=float(self.total_output_tokens),
                metric_type=MetricType.COUNTER,
                timestamp=timestamp,
            ),
            MetricData(
                name="token.savings.total",
                value=float(self.total_savings_tokens),
                metric_type=MetricType.COUNTER,
                timestamp=timestamp,
            ),
            MetricData(
                name="token.cached.total",
                value=float(self.total_cached_tokens),
                metric_type=MetricType.COUNTER,
                timestamp=timestamp,
            ),
            MetricData(
                name="token.requests.total",
                value=float(self.total_requests),
                metric_type=MetricType.COUNTER,
                timestamp=timestamp,
            ),
        ]
