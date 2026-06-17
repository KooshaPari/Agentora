"""
Reusable launcher for ServiceInfra-managed service bundles.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from pheno.infra.orchestrator import OrchestratorConfig, ServiceOrchestrator
from pheno.infra.service_infra import ServiceInfraManager
from pheno.infra.service_manager import ServiceConfig

ServiceFactory = Callable[..., list[ServiceConfig]]


@dataclass
class ServiceLauncher:
    """
    Thin wrapper around ``ServiceOrchestrator`` for common CLI flows.
    """

    project_name: str
    service_factory: ServiceFactory
    dependencies: dict[str, Iterable[str]] = field(default_factory=dict)
    service_domain: str | None = None
    logger: logging.Logger | None = None
    startup_config: OrchestratorConfig | None = None

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
        Start configured services and optionally monitor them.
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

        if await orchestrator.start_all():
            self.logger.info("=" * 60)
            self.logger.info("✅ Services started successfully")
            orchestrator.print_status()
            self.logger.info("=" * 60)

            if monitor:
                await orchestrator.monitor()
            return True

        self.logger.error("Failed to start services")
        return False

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
