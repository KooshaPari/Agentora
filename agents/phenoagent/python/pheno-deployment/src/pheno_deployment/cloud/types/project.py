"""
Project-level deployment data structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import datetime

    from .credentials import Credentials
    from .deployment_models import Deployment, DeploymentStatus
    from .enums import DeploymentState, HealthStatus
    from .metrics import Cost, CostEstimate
    from .resource import Resource, ResourceConfig


@dataclass
class ProjectConfig:
    """
    Configuration describing a multi-resource project deployment.
    """

    name: str
    version: str
    environment: str
    providers: dict[str, Credentials]
    resources: list[ResourceConfig]
    region: str | None = None
    tags: dict[str, str] = field(default_factory=dict)
    dependencies: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ProjectDeployment:
    """
    Snapshot describing the state of a deployed project across providers.
    """

    id: str
    name: str
    environment: str
    version: str
    status: DeploymentState
    resources: list[Resource]
    deployments: list[Deployment]
    started_at: datetime
    updated_at: datetime
    finished_at: datetime | None = None


@dataclass
class ProjectStatus:
    """
    Aggregated status and cost information for a project.
    """

    project: ProjectDeployment
    health: HealthStatus
    resources: dict[str, DeploymentStatus]
    cost_estimate: CostEstimate | None = None
    actual_cost: Cost | None = None


__all__ = ["ProjectConfig", "ProjectDeployment", "ProjectStatus"]
