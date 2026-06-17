"""
Metric and cost data structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass
class MetricOptions:
    """
    Options controlling metric retrieval windows and filters.
    """

    since: datetime | None = None
    until: datetime | None = None
    granularity: str | None = None
    instance_id: str | None = None
    metric_names: list[str] | None = None


@dataclass
class Metric:
    """
    Single data point within a time-series metric.
    """

    name: str
    value: float
    unit: str
    timestamp: datetime
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class CostEstimate:
    """
    Estimated cost projection for planned resource usage.
    """

    hourly_usd: float
    daily_usd: float
    monthly_usd: float
    breakdown: dict[str, float]
    confidence: str
    currency: str
    last_updated: datetime


@dataclass
class Cost:
    """
    Actual cost incurred for resource consumption.
    """

    total_usd: float
    breakdown: dict[str, float]
    start_time: datetime
    end_time: datetime
    currency: str


@dataclass
class TimeRange:
    """
    Inclusive time range used for metrics and log queries.
    """

    start: datetime
    end: datetime


__all__ = ["Cost", "CostEstimate", "Metric", "MetricOptions", "TimeRange"]
