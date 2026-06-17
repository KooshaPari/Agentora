"""
Reusable launcher for ServiceInfra-managed service bundles.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

from pheno.infra.orchestrator import OrchestratorConfig, ServiceOrchestrator
from pheno.infra.service_infra import ServiceInfraManager
from pheno.infra.service_manager import ServiceConfig

ServiceFactory = Callable[..., list[ServiceConfig]]


@dataclass
class ServiceLauncher:
    """
    Thin wrapper around ``ServiceOrchestrator`` for common CLI flows with optional Rich
    TUI.
    """

    project_name: str
    service_factory: ServiceFactory
    dependencies: dict[str, Iterable[str]] = field(default_factory=dict)
    service_domain: str | None = None
    logger: logging.Logger | None = None
    startup_config: OrchestratorConfig | None = None

    # Rich TUI configuration
    enable_rich_tui: bool = True
    """
    Enable Rich-based TUI with scrolling logs.
    """

    monitor_resources: list[dict[str, Any]] = field(default_factory=list)
    """
    External resources to monitor (e.g., [{"name": "Postgres", "port": 5432}])
    """

    def __post_init__(self) -> None:
        self.logger = self.logger or logging.getLogger(self.project_name)
        self._normalized_deps: dict[str, list[str]] = {
            name.lower(): list(deps) for name, deps in self.dependencies.items()
        }

    def _register_services(
        self,
        orchestrator: ServiceOrchestrator,
        services: list[ServiceConfig],
    ) -> None:
        for service in services:
            depends_on = self._normalized_deps.get(service.name.lower())
            if depends_on:
                orchestrator.add_service(service, depends_on=depends_on)
            else:
                orchestrator.add_service(service)

    async def start(self, *, monitor: bool = True, **service_kwargs) -> bool:
        """
        Start configured services and optionally monitor them with Rich TUI.
        """
        config = self.startup_config or OrchestratorConfig(
            project_name=self.project_name,
            parallel_startup=False,
            auto_restart=True,
            save_state=True,
        )

        service_infra = (
            ServiceInfraManager(domain=self.service_domain)
            if self.service_domain
            else ServiceInfraManager()
        )
        orchestrator = ServiceOrchestrator(config, service_infra)

        services = self.service_factory(**service_kwargs)
        if not services:
            self.logger.error("No services returned from service factory")
            return False

        self._register_services(orchestrator, services)

        try:
            started = await orchestrator.start_all()
        except RuntimeError as exc:
            self.logger.exception("Failed to start services", exc_info=exc)
            await orchestrator.stop_all()
            return False

        if started:
            self.logger.info("=" * 60)
            self.logger.info("✅ Services started successfully")
            orchestrator.print_status()
            self.logger.info("=" * 60)

            if monitor:
                # Use Rich TUI monitor if enabled and available
                if self.enable_rich_tui:
                    service_manager = getattr(orchestrator, "service_manager", None)
                    processes = (
                        getattr(service_manager, "processes", None) if service_manager else None
                    )
                    if isinstance(processes, dict):
                        rich_supported = all(hasattr(proc, "poll") for proc in processes.values())
                    else:
                        rich_supported = False

                    if rich_supported:
                        with contextlib.suppress(asyncio.CancelledError):
                            await self._monitor_with_rich_tui(orchestrator, services)
                    else:
                        self.logger.debug(
                            "Rich TUI monitor not available; falling back to basic monitor",
                        )
                        with contextlib.suppress(asyncio.CancelledError):
                            await orchestrator.monitor()
                else:
                    with contextlib.suppress(asyncio.CancelledError):
                        await orchestrator.monitor()
            return True

        self.logger.error("Failed to start services")
        return False

    async def _monitor_with_rich_tui(
        self, orchestrator: ServiceOrchestrator, services: list[ServiceConfig],
    ) -> None:
        """
        Monitor services using Rich TUI with scrolling logs.
        """
        try:
            from pheno.infra.monitoring import MonitorConfig
        except ImportError:
            # Fallback to standard monitoring if Rich not available
            self.logger.warning("Rich monitoring not available, falling back to standard monitor")
            await orchestrator.monitor()
            return

        # Build monitor config
        service_names = [svc.name for svc in services]
        MonitorConfig(
            project_name=self.project_name,
            services=service_names,
            domain=self.service_domain,
            resources=self.monitor_resources,
        )

        # Rich monitor expects subprocess.Popen objects with stdout/stderr
        # Since we only have PIDs, use orchestrator's built-in monitor instead
        await orchestrator.monitor()

    async def stop(self, **service_kwargs) -> None:
        """
        Stop running services tracked by the orchestrator state file.
        """
        config = OrchestratorConfig(project_name=self.project_name, save_state=False)
        orchestrator = ServiceOrchestrator(config, ServiceInfraManager())

        state = orchestrator.load_state()
        if not state or "services" not in state:
            self.logger.info("No running services found")
            return

        services = self.service_factory(**service_kwargs)
        if not services:
            self.logger.warning("Service factory returned no services; skipping stop operation")
            return

        self._register_services(orchestrator, services)
        await orchestrator.stop_all()
        self.logger.info("✅ All services stopped")

    def show_status(self) -> None:
        """
        Print orchestrator status for the project.
        """
        config = OrchestratorConfig(project_name=self.project_name, save_state=False)
        orchestrator = ServiceOrchestrator(config, ServiceInfraManager())

        state = orchestrator.load_state()
        if not state:
            self.logger.info("No running services found")
            return

        self.logger.info("\n📋 Service Status")
        self.logger.info("=" * 60)
        for service_name, info in state.get("services", {}).items():
            self.logger.info(f"\n{service_name.upper()}:")
            self.logger.info(f"  State: {info.get('state')}")
            self.logger.info(f"  PID: {info.get('pid')}")
            self.logger.info(f"  Port: {info.get('port')}")
            if info.get("tunnel_url"):
                self.logger.info(f"  Public URL: {info.get('tunnel_url')}")
            if info.get("health_status"):
                self.logger.info(f"  Health: {info.get('health_status')}")
        self.logger.info("=" * 60)
