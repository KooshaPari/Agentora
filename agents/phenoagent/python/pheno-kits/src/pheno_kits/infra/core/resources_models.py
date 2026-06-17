"""Data models for unified resource management."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any


class ResourceReuseStrategy(Enum):
    """Strategies that control how shared resources are reused across projects."""

    ALWAYS = "always"
    """Always reuse an existing shared resource when one is discovered."""

    CONDITIONAL = "conditional"
    """Reuse only when compatibility checks pass for the requested configuration."""

    NEVER = "never"
    """Never reuse resources; every project receives a dedicated instance."""

    SMART = "smart"
    """Use heuristics to determine whether reuse is desirable."""


class ResourceScope(Enum):
    """Scope indicating whether a resource is shared globally or project-specific."""

    PROJECT = "project"
    """Resource belongs exclusively to a single project (tenanted)."""

    SHARED = "shared"
    """Resource is eligible for reuse across multiple projects."""


@dataclass
class ResourceDependency:
    """Describes dependency relationships between higher-level resources."""

    resource_name: str
    """Friendly name of the resource that depends on other components."""

    dependencies: list[str]
    """Required dependent resource names that must also be active."""

    optional_dependencies: list[str] = field(default_factory=list)
    """Dependencies that are helpful but not strictly required."""

    compatibility_requirements: dict[str, dict[str, Any]] = field(default_factory=dict)
    """Optional compatibility assertions for each dependency."""


@dataclass
class ResourceReference:
    """Internal record that tracks cached resources and their usage metadata."""

    cache_key: str
    """Canonical key used to look up the reference in the manager cache."""

    resource_name: str
    """Friendly name exposed to callers (without project scoping details)."""

    adapter_name: str
    """Concrete adapter identifier used to address the running resource."""

    scope: ResourceScope
    """Whether the resource is project-specific or shareable across projects."""

    reference_count: int = 0
    """Number of active projects currently holding a reference."""

    created_at: float = field(default_factory=time.time)
    """Timestamp when the resource reference was first created."""

    last_accessed: float = field(default_factory=time.time)
    """Timestamp of the most recent access or reference refresh."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Arbitrary metadata captured at resource registration time."""

    projects: set[str] = field(default_factory=set)
    """Projects currently mapped to this resource."""

    resource_type: str | None = None
    """Adapter type (for example ``docker`` or ``systemd``)."""

    config_signature: str | None = None
    """Stable fingerprint of the configuration payload."""

    compatibility_score: float = 1.0
    """Rolling heuristic score used by SMART reuse decisions."""

    is_healthy: bool = False
    """Last recorded health-check result for the resource."""

    dependencies: list[str] = field(default_factory=list)
    """Cached dependency list for quick validation."""

    def touch(self) -> None:
        """Update the ``last_accessed`` timestamp to the current time."""
        self.last_accessed = time.time()
