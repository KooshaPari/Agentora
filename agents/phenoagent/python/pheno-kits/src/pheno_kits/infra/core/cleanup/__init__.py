"""Unified cleanup manager for KINFRA and Pheno SDK services.

This module consolidates the legacy cleanup helpers scattered across
``pheno.infra.process_cleanup``, ``shared.startup_utils``, the governance
systems in ``pheno.infra.process_governance``, and the configurable policies
from ``pheno.infra.cleanup_policies``.

The :class:`CleanupManager` exposes a single orchestration surface that can:

* Discover running processes using psutil with optional metadata filters.
* Terminate tunnel, DNS, and service processes while respecting governance
  policies and protected ports.
* Clean up stale TCP listeners without disrupting shared infrastructure such
  as PostgreSQL (5432), NATS (4222), or the model hub (11434).
* Remove lingering Cloudflare tunnel configuration and DNS records when
  credentials or the ``cloudflared`` CLI are available.
* Register and enforce metadata-based lifecycle policies so projects can
  clean up their own processes without affecting neighbouring services.

All operations are designed to degrade gracefully when optional dependencies
(for example :mod:`psutil` or the Cloudflare SDK) are not installed.  The
manager returns structured dictionaries that callers may feed into higher
level telemetry or logging pipelines.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pheno.kits.infra.core.cleanup._constants import (
    HAS_CLOUDFLARE,
    PSUTIL_AVAILABLE,
    PROTECTED_PORTS,
)
from pheno.kits.infra.core.cleanup._models import (
    CleanupConfig,
    CleanupReport,
    CleanupStats,
    ProcessDiscoveryRecord,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pheno.infra.cleanup_policies import CleanupPolicyManager
    from pheno.infra.process_governance import ProcessGovernanceManager, ProcessMetadata
    from shared.resources import ResourceRegistry

from pheno.kits.infra.core.cleanup._dns import DnsCleanup
from pheno.kits.infra.core.cleanup._ports import PortCleanup
from pheno.kits.infra.core.cleanup._process import ProcessCleanup

logger = logging.getLogger(__name__)

CleanupPolicyManager: type | None
ProcessGovernanceManager: type | None
ProcessMetadata: type | None
ResourceRegistry: type | None


try:
    from pheno.infra.cleanup_policies import CleanupPolicyManager
except ImportError:  # pragma: no cover - optional runtime dependency
    CleanupPolicyManager = None  # type: ignore[assignment]


try:
    from pheno.infra.process_governance import ProcessGovernanceManager
except ImportError:  # pragma: no cover - optional runtime dependency
    ProcessGovernanceManager = None  # type: ignore[assignment]


try:
    from pheno.infra.process_governance import ProcessMetadata
except ImportError:  # pragma: no cover - optional runtime dependency
    ProcessMetadata = None  # type: ignore[assignment, misc]


try:
    from shared.resources import ResourceRegistry, get_shared_ports, is_shared_port
except ImportError:  # pragma: no cover - optional during packaging
    ResourceRegistry = None  # type: ignore[assignment]

    def get_shared_ports() -> list[int]:
        return []

    def is_shared_port(port: int) -> bool:
        return False


class CleanupManager:
    """High level orchestrator for environment cleanup routines.

    Parameters
    ----------
    config:
        Behaviour toggles and metadata filters applied to cleanup actions.
    policy_manager:
        Optional :class:`CleanupPolicyManager` for project specific rules.
    governance_manager:
        Optional :class:`ProcessGovernanceManager` that tracks metadata for
        long-lived processes.  When supplied, metadata-aware cleanup helpers
        such as :meth:`cleanup_governed_processes` become active.
    resource_registry:
        Optional :class:`shared.resources.ResourceRegistry`.  When omitted the
        registry is resolved lazily (if available) so that shared ports are
        preserved even during aggressive cleanup runs.
    """

    def __init__(
        self,
        config: CleanupConfig | None = None,
        policy_manager: CleanupPolicyManager | None = None,
        governance_manager: ProcessGovernanceManager | None = None,
        resource_registry: ResourceRegistry | None = None,
    ) -> None:
        self.config = config or CleanupConfig()

        self._policy_manager = policy_manager or (
            CleanupPolicyManager() if CleanupPolicyManager else None
        )
        self._governance_manager = governance_manager or (
            ProcessGovernanceManager(ProcessGovernanceConfig())  # type: ignore[call-arg]
            if ProcessGovernanceManager and ProcessGovernanceConfig
            else None
        )
        self._resource_registry = (
            resource_registry
            or self.config.shared_resource_registry
            or (ResourceRegistry.get_instance() if ResourceRegistry else None)
        )

        self._process_cleanup = ProcessCleanup(
            config=self.config,
            policy_manager=self._policy_manager,
            governance_manager=self._governance_manager,
        )
        self._port_cleanup = PortCleanup(
            config=self.config,
            resource_registry=self._resource_registry,
        )
        self._dns_cleanup = DnsCleanup(config=self.config)

        if self._policy_manager:
            logger.debug("CleanupManager initialised with policy manager support")
        if self._governance_manager:
            logger.debug("CleanupManager initialised with governance support")

    # ------------------------------------------------------------------
    # Public orchestration helpers
    # ------------------------------------------------------------------
    def cleanup_environment(
        self,
        service_name: str,
        ports: Sequence[int] | None = None,
        domains: Sequence[str] | None = None,
    ) -> CleanupReport:
        """Run all configured cleanup stages and return a consolidated report."""
        report = CleanupReport()

        if self.config.cleanup_tunnels or self.config.cleanup_dns_processes:
            logger.info("Starting process cleanup for service '%s'", service_name)
            process_stats = self._process_cleanup.cleanup_processes(service_name)
            report.process_stats = process_stats
            logger.info("Process cleanup complete: %s", process_stats.as_dict())

        if self.config.cleanup_ports:
            port_candidates = ports or self.config.ports_to_scan
            if port_candidates:
                report.port_summary = self._port_cleanup.cleanup_ports(port_candidates)

        if self.config.cleanup_dns_records:
            domain_candidates = domains or self.config.dns_domains
            if domain_candidates:
                report.dns_summary = self._dns_cleanup.cleanup_dns(domain_candidates)

        if self.config.metadata_cleanup and self._governance_manager:
            governance_report = self._process_cleanup.cleanup_governed_processes(
                project=self.config.project,
                service=self.config.service,
                scope=self.config.scope,
                cleanup_stale=self.config.cleanup_stale_metadata,
            )
            report.governance_summary = governance_report

        return report

    async def cleanup_environment_async(
        self,
        service_name: str,
        ports: Sequence[int] | None = None,
        domains: Sequence[str] | None = None,
    ) -> CleanupReport:
        """Async wrapper for :meth:`cleanup_environment`."""
        import asyncio

        return await asyncio.to_thread(
            self.cleanup_environment,
            service_name,
            ports,
            domains,
        )

    def discover_processes(
        self,
        patterns: Sequence[str] | None = None,
        include_ports: bool = True,
    ) -> list[ProcessDiscoveryRecord]:
        """Return processes whose names or command lines match ``patterns``."""
        return self._process_cleanup.discover_processes(patterns, include_ports)

    def register_process_metadata(self, pid: int, metadata: ProcessMetadata) -> None:
        """Register metadata with the governance manager when available."""
        self._process_cleanup.register_process_metadata(pid, metadata)

    def unregister_process_metadata(self, pid: int) -> None:
        """Remove metadata tracking for a PID when governance is enabled."""
        self._process_cleanup.unregister_process_metadata(pid)

    def cleanup_governed_processes(
        self,
        project: str | None = None,
        service: str | None = None,
        scope: str | None = None,
        cleanup_stale: bool = False,
    ) -> dict[str, Any]:
        """Invoke metadata-aware cleanup through the governance manager."""
        return self._process_cleanup.cleanup_governed_processes(
            project,
            service,
            scope,
            cleanup_stale,
        )

    def cleanup_ports(
        self,
        ports: Sequence[int],
        force: bool = False,
    ) -> dict[str, Any]:
        """Terminate processes bound to the supplied ``ports``."""
        return self._port_cleanup.cleanup_ports(ports, force)

    def cleanup_dns(self, domains: Sequence[str]) -> dict[str, Any]:
        """Attempt to remove lingering DNS records and config files."""
        return self._dns_cleanup.cleanup_dns(domains)


try:
    from pheno.infra.process_governance import ProcessGovernanceConfig
except ImportError:  # pragma: no cover - optional runtime dependency
    ProcessGovernanceConfig = None  # type: ignore[assignment]


__all__ = [
    "CleanupConfig",
    "CleanupManager",
    "CleanupReport",
    "CleanupStats",
    "ProcessDiscoveryRecord",
]
