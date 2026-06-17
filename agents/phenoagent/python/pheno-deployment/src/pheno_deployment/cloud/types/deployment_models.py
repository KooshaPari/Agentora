"""
Deployment-related data structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import datetime, timedelta

    from .enums import DeploymentState, DeploymentStrategy, HealthStatus
    from .health import HealthCheckConfig


@dataclass
class RollbackConfig:
    """
    Parameters controlling automated rollback behaviour after failures.
    """

    enabled: bool
    max_retries: int
    retry_interval: timedelta


@dataclass
class DeployConfig:
    """
    Wrapper grouping deployment behaviour configuration.
    """

    strategy: DeploymentStrategy
    health_check: HealthCheckConfig | None = None
    timeout: timedelta | None = None
    rollback: RollbackConfig | None = None


@dataclass
class DeploymentSource:
    """
    Configuration describing the source artifacts used for deployments.
    """

    type: str
    repository: str | None = None
    branch: str | None = None
    commit: str | None = None
    image: str | None = None
    tag: str | None = None
    path: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class DeploymentConfig:
    """
    Comprehensive deployment configuration sent to providers.
    """

    resource_id: str
    source: DeploymentSource
    strategy: DeploymentStrategy
    version: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    secrets: dict[str, str] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class DeploymentError:
    """
    Structured error information returned when deployments fail.
    """

    code: str
    message: str
    details: Any | None = None


@dataclass
class Deployment:
    """
    Snapshot describing an individual deployment execution.
    """

    id: str
    resource_id: str
    version: str
    state: DeploymentState
    strategy: DeploymentStrategy
    progress: int
    started_at: datetime
    updated_at: datetime
    message: str | None = None
    finished_at: datetime | None = None
    error: DeploymentError | None = None


@dataclass
class InstanceInfo:
    """
    Runtime information for a single resource instance.
    """

    id: str
    state: str
    health: HealthStatus
    started_at: datetime
    region: str | None = None
    cpu_usage: float | None = None
    memory_usage: float | None = None


@dataclass
class DeploymentStatus:
    """
    Aggregated status combining deployment metadata, health, and instances.
    """

    deployment: Deployment
    health: HealthStatus
    instances: list[InstanceInfo] = field(default_factory=list)
    last_health_check: datetime | None = None


__all__ = [
    "DeployConfig",
    "Deployment",
    "DeploymentConfig",
    "DeploymentError",
    "DeploymentSource",
    "DeploymentStatus",
    "InstanceInfo",
    "RollbackConfig",
]
