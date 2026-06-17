"""
Resource configuration and state models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import datetime

    from .deployment_models import DeployConfig
    from .enums import DeploymentState, HealthStatus, ResourceType


@dataclass
class ResourceConfig:
    """
    Provider-agnostic configuration for creating or updating a resource.
    """

    name: str
    type: ResourceType
    provider: str
    region: str | None = None
    tags: dict[str, str] = field(default_factory=dict)
    spec: dict[str, Any] = field(default_factory=dict)
    deploy: DeployConfig | None = None


@dataclass
class Endpoint:
    """
    Describes a network endpoint exposed by a resource.
    """

    type: str
    url: str
    primary: bool
    port: int | None = None
    protocol: str | None = None


@dataclass
class Resource:
    """
    Snapshot of a deployed cloud resource and its metadata.
    """

    id: str
    name: str
    type: ResourceType
    provider: str
    status: DeploymentState
    health_status: HealthStatus
    created_at: datetime
    updated_at: datetime
    region: str | None = None
    tags: dict[str, str] = field(default_factory=dict)
    endpoints: list[Endpoint] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    last_deployed_at: datetime | None = None


@dataclass
class ResourceFilter:
    """
    Filter criteria used when listing resources across providers.
    """

    types: list[ResourceType] | None = None
    providers: list[str] | None = None
    regions: list[str] | None = None
    tags: dict[str, str] | None = None
    states: list[DeploymentState] | None = None


@dataclass
class ResourceDependency:
    """
    Declarative dependency relationship between resources.
    """

    resource: str
    depends_on: list[str]
    wait_for: str | None = None


__all__ = [
    "Endpoint",
    "Resource",
    "ResourceConfig",
    "ResourceDependency",
    "ResourceFilter",
]
