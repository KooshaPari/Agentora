"""
Base MCP Entry Point Constructor
===============================

Provides the foundational classes and utilities for MCP server entry points.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pheno.infra.orchestration.launcher import ServiceLauncher
from pheno.infra.orchestrator import OrchestratorConfig, ServiceOrchestrator
from pheno.infra.service_infra import ServiceInfraManager
from pheno.infra.service_manager.models import ServiceConfig


@dataclass
class MCPServiceConfig:
    """
    Configuration for MCP services with sensible defaults.
    """

    name: str
    command: str | list[str]
    port: int
    domain: str | None = None
    health_check_path: str = "/health"
    startup_timeout: int = 30
    shutdown_timeout: int = 10
    environment: dict[str, str] | None = None
    working_directory: Path | None = None
    dependencies: list[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.environment is None:
            self.environment = {}

    def to_service_config(self) -> ServiceConfig:
        """
        Convert to ServiceInfra ServiceConfig.
        """
        # Convert command string to list if needed
        command = self.command if isinstance(self.command, list) else [self.command]

        return ServiceConfig(
            name=self.name,
            command=command,
            port=self.port,
            tunnel_domain=self.domain,
            health_check_url=self.health_check_path,
            cwd=self.working_directory,
            env=self.environment,
        )


class MCPEntryPoint:
    """Base class for MCP server entry points.

    Provides common functionality for MCP servers including:
    - Service orchestration using ServiceInfra
    - Automatic port allocation and tunnel management
    - Health checking and monitoring
    - Graceful shutdown handling
    """

    def __init__(
        self,
        project_name: str,
        service_configs: list[MCPServiceConfig],
        dependencies: dict[str, list[str]] | None = None,
        service_domain: str | None = None,
        logger: logging.Logger | None = None,
    ):
        self.project_name = project_name
        self.service_configs = service_configs
        self.dependencies = dependencies or {}
        self.service_domain = service_domain
        self.logger = logger or logging.getLogger(project_name)

        # Create service factory
        self.service_factory = self._create_service_factory()

        # Initialize ServiceLauncher
        self.service_launcher = ServiceLauncher(
            project_name=project_name,
            service_factory=self.service_factory,
            dependencies=self.dependencies,
            service_domain=service_domain,
            logger=self.logger,
        )

    def _create_service_factory(self):
        """
        Create a service factory function for the ServiceLauncher.
        """

        def service_factory(**kwargs):
            services = []
            for config in self.service_configs:
                # Apply any runtime overrides from kwargs
                service_config = config.to_service_config()

                # Override port if provided
                if "port" in kwargs:
                    service_config.port = kwargs["port"]

                # Override domain if provided
                if "domain" in kwargs:
                    service_config.tunnel_domain = kwargs["domain"]

                services.append(service_config)

            return services

        return service_factory

    async def start(self, monitor: bool = True, **service_kwargs) -> bool:
        """Start the MCP server and all its services.

        Args:
            monitor: Whether to monitor services after starting
            **service_kwargs: Additional service configuration overrides

        Returns:
            True if all services started successfully, False otherwise
        """
        self.logger.info(f"Starting {self.project_name} MCP server...")

        try:
            success = await self.service_launcher.start(monitor=monitor, **service_kwargs)

            if success:
                self.logger.info(f"✅ {self.project_name} MCP server started successfully")
            else:
                self.logger.error(f"❌ Failed to start {self.project_name} MCP server")

            return success

        except Exception as e:
            self.logger.exception(f"Error starting {self.project_name} MCP server: {e}")
            return False

    async def stop(self, **service_kwargs) -> None:
        """
        Stop the MCP server and all its services.
        """
        self.logger.info(f"Stopping {self.project_name} MCP server...")

        try:
            await self.service_launcher.stop(**service_kwargs)
            self.logger.info(f"✅ {self.project_name} MCP server stopped")
        except Exception as e:
            self.logger.exception(f"Error stopping {self.project_name} MCP server: {e}")

    def show_status(self) -> None:
        """
        Show the status of all services.
        """
        self.service_launcher.show_status()

    async def health_check(self) -> dict[str, Any]:
        """Perform a comprehensive health check of all services.

        Returns:
            Dictionary containing health status information
        """
        health_status = {"project": self.project_name, "services": {}, "overall_status": "healthy"}

        # Get service status from orchestrator
        config = OrchestratorConfig(project_name=self.project_name, save_state=False)
        service_infra = (
            ServiceInfraManager(domain=self.service_domain)
            if self.service_domain
            else ServiceInfraManager()
        )
        orchestrator = ServiceOrchestrator(config, service_infra)

        services = self.service_factory()
        self.service_launcher._register_services(orchestrator, services)
        state = orchestrator.load_state()

        if not state or "services" not in state:
            health_status["overall_status"] = "no_services"
            return health_status

        # Check each service
        for service_name, info in state.get("services", {}).items():
            service_health = {
                "state": info.get("state", "unknown"),
                "pid": info.get("pid"),
                "port": info.get("port"),
                "health_status": info.get("health_status", "unknown"),
                "tunnel_url": info.get("tunnel_url"),
            }

            health_status["services"][service_name] = service_health

            # Determine overall health
            if info.get("state") != "running":
                health_status["overall_status"] = "unhealthy"

        return health_status
