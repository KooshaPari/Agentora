"""
Scaling and pooling configuration types.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import timedelta


@dataclass
class ScalePolicy:
    """
    Policy governing how automatic scaling adjustments occur.
    """

    cooldown: timedelta
    step: int
    threshold: int


@dataclass
class ScaleConfig:
    """
    Scaling configuration applied to scalable resources.
    """

    min_instances: int
    max_instances: int
    target_cpu: int | None = None
    target_memory: int | None = None
    target_requests: int | None = None
    scale_up_policy: ScalePolicy | None = None
    scale_down_policy: ScalePolicy | None = None


@dataclass
class PoolConfig:
    """
    Connection pool configuration for database resources.
    """

    min_connections: int
    max_connections: int
    connection_timeout: int
    idle_timeout: int
    max_lifetime: int


__all__ = ["PoolConfig", "ScaleConfig", "ScalePolicy"]
