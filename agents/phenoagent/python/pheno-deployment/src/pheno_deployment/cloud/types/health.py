"""
Health check configuration and results.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime, timedelta

    from .enums import HealthStatus


@dataclass
class HealthCheckConfig:
    """
    Configuration describing how provider health checks should behave.
    """

    type: str
    interval: timedelta
    timeout: timedelta
    retries: int
    initial_delay: timedelta
    success_threshold: int
    failure_threshold: int
    path: str | None = None
    port: int | None = None
    command: str | None = None


@dataclass
class HealthCheckStatus:
    """
    Result of executing a health check against a resource.
    """

    status: HealthStatus
    last_check: datetime
    consecutive_passes: int
    consecutive_fails: int
    details: str | None = None


__all__ = ["HealthCheckConfig", "HealthCheckStatus"]
