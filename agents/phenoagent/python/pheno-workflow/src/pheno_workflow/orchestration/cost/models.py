"""Cost Models.

Data models for cost optimization.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class CostStrategy:
    """
    Represents a cost optimization strategy.
    """

    model: str
    max_budget: float
    max_iterations: int
    use_cache: bool
    estimated_cost: float
    routing_decision: str  # 'refact_subscription', 'cache', 'optimized_api', 'premium_api'
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class UsageMetrics:
    """
    Tracks usage metrics for cost optimization.
    """

    tenant_id: str
    requests_count: int = 0
    total_cost: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    refact_requests: int = 0
    api_requests: int = 0
    last_reset: datetime = field(default_factory=datetime.now)

    def get_cache_hit_rate(self) -> float:
        """
        Calculate cache hit rate.
        """
        total_cache_requests = self.cache_hits + self.cache_misses
        if total_cache_requests == 0:
            return 0.0
        return self.cache_hits / total_cache_requests

    def get_average_cost_per_request(self) -> float:
        """
        Calculate average cost per request.
        """
        if self.requests_count == 0:
            return 0.0
        return self.total_cost / self.requests_count

    def reset(self):
        """
        Reset metrics.
        """
        self.requests_count = 0
        self.total_cost = 0.0
        self.cache_hits = 0
        self.cache_misses = 0
        self.refact_requests = 0
        self.api_requests = 0
        self.last_reset = datetime.now()
