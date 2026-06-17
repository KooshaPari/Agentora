"""Data models for cleanup operations."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from pheno.kits.infra.core.cleanup._constants import PROTECTED_PORTS


@dataclass
class CleanupStats:
    """Summary statistics for a cleanup action."""

    inspected: int = 0
    terminated: int = 0
    force_killed: int = 0
    skipped: int = 0
    errors: int = 0

    def as_dict(self) -> dict[str, int]:
        """Return a serialisable representation."""
        return {
            "inspected": self.inspected,
            "terminated": self.terminated,
            "force_killed": self.force_killed,
            "skipped": self.skipped,
            "errors": self.errors,
        }

    def merge(self, other: CleanupStats) -> None:
        """Accumulate counts from another statistics snapshot."""
        self.inspected += other.inspected
        self.terminated += other.terminated
        self.force_killed += other.force_killed
        self.skipped += other.skipped
        self.errors += other.errors


@dataclass
class CleanupReport:
    """Structured report returned by :class:`CleanupManager` operations."""

    process_stats: CleanupStats = field(default_factory=CleanupStats)
    port_summary: dict[str, Any] = field(default_factory=dict)
    dns_summary: dict[str, Any] = field(default_factory=dict)
    governance_summary: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """Convert the report into a dictionary for logging or serialization."""
        return {
            "process": self.process_stats.as_dict(),
            "ports": self.port_summary,
            "dns": self.dns_summary,
            "governance": self.governance_summary,
        }


@dataclass
class CleanupConfig:
    """Configuration flags used by :class:`CleanupManager`."""

    cleanup_tunnels: bool = True
    cleanup_dns_processes: bool = True
    cleanup_related_services: bool = True
    cleanup_shared_resources: bool = False
    cleanup_ports: bool = True
    cleanup_dns_records: bool = True
    force_kill: bool = True
    grace_period: float = 3.0
    protected_ports: set[int] = field(default_factory=lambda: set(PROTECTED_PORTS))
    ports_to_scan: list[int] | None = None
    dns_domains: tuple[str, ...] = ()
    project: str | None = None
    service: str | None = None
    scope: str | None = None
    metadata_cleanup: bool = False
    cleanup_stale_metadata: bool = False
    shared_resource_registry: Any = None


@dataclass
class ProcessDiscoveryRecord:
    """Record describing a discovered process."""

    pid: int
    name: str
    cmdline: list[str]
    ports: list[int]
    status: str
    username: str | None
    create_time: float | None

    def as_dict(self) -> dict[str, Any]:
        """Dictionary representation suitable for JSON logging."""
        return {
            "pid": self.pid,
            "name": self.name,
            "cmdline": self.cmdline,
            "ports": self.ports,
            "status": self.status,
            "username": self.username,
            "create_time": self.create_time,
        }
