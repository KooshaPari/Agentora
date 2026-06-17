"""
Enumerations for the cloud provider abstraction layer.
"""

from __future__ import annotations

from enum import StrEnum


class ResourceType(StrEnum):
    """
    Canonical resource type identifiers used across providers.
    """

    # Compute
    COMPUTE_VM = "compute.vm"
    COMPUTE_CONTAINER = "compute.container"
    COMPUTE_FUNCTION = "compute.function"
    COMPUTE_EDGE = "compute.edge"

    # Database
    DATABASE_SQL = "database.sql"
    DATABASE_NOSQL = "database.nosql"
    DATABASE_SERVERLESS = "database.serverless"

    # Storage
    STORAGE_OBJECT = "storage.object"
    STORAGE_BLOCK = "storage.block"
    STORAGE_FILE = "storage.file"

    # Network
    NETWORK_LOAD_BALANCER = "network.loadbalancer"
    NETWORK_CDN = "network.cdn"
    NETWORK_DNS = "network.dns"
    NETWORK_VPC = "network.vpc"


class DeploymentState(StrEnum):
    """
    High-level state machine describing resource deployment lifecycle.
    """

    PENDING = "PENDING"
    VALIDATING = "VALIDATING"
    BUILDING = "BUILDING"
    PROVISIONING = "PROVISIONING"
    DEPLOYING = "DEPLOYING"
    HEALTH_CHECK = "HEALTH_CHECK"
    ACTIVE = "ACTIVE"
    UPDATING = "UPDATING"
    SCALING = "SCALING"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    ROLLING_BACK = "ROLLING_BACK"
    DELETING = "DELETING"
    DELETED = "DELETED"


class DeploymentStrategy(StrEnum):
    """
    Supported rollout strategies for provider-agnostic deployments.
    """

    ROLLING = "rolling"
    BLUE_GREEN = "bluegreen"
    CANARY = "canary"
    ATOMIC = "atomic"
    RECREATE = "recreate"


class Capability(StrEnum):
    """
    Optional provider capabilities surfaced by CloudProvider.get_capabilities.
    """

    SCALABLE = "scalable"
    LOGGABLE = "loggable"
    EXECUTABLE = "executable"
    BACKUPABLE = "backupable"
    MONITORING = "monitoring"
    AUTO_SCALE = "autoscale"
    CUSTOM_DNS = "custom_dns"
    SSH = "ssh"


class HealthStatus(StrEnum):
    """
    Standardised health status values returned by health checks.
    """

    UNKNOWN = "UNKNOWN"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    CHECKING = "CHECKING"


__all__ = [
    "Capability",
    "DeploymentState",
    "DeploymentStrategy",
    "HealthStatus",
    "ResourceType",
]
