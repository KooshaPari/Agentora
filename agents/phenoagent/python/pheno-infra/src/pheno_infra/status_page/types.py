"""
Status Page types.
"""

from __future__ import annotations

from enum import Enum


class ServiceStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    STARTING = "starting"
    MAINTENANCE = "maintenance"
