"""
Project Routing Templates - Default project routing configuration

Provides default routing templates for projects with domain + base path mapping,
project-specific routing rules, and integration with the reverse proxy system.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ProjectRoute:
    """
    Route configuration for a project.
    """

    project_name: str
    """
    Name of the project.
    """

    path_prefix: str
    """
    Base path prefix for the project (e.g., '/api/v1').
    """

    domain: str
    """
    Domain for the project (e.g., 'api.example.com').
    """

    service_name: str
    """
    Name of the service handling this route.
    """

    port: int
    """
    Port where the service is running.
    """

    host: str = "localhost"
    """
    Host where the service is running.
    """

    health_check_path: str = "/health"
    """
    Health check endpoint path.
    """

    metadata: dict[str, Any] = field(default_factory=dict)
    """
    Additional metadata for the route.
    """

    is_active: bool = True
    """
    Whether this route is currently active.
    """


@dataclass
class ProjectRoutingConfig:
    """
    Configuration for project routing.
    """

    project_name: str
    """
    Name of the project.
    """

    domain: str
    """
    Primary domain for the project.
    """

    base_path: str = "/"
    """
    Base path prefix for all project routes.
    """

    routes: list[ProjectRoute] = field(default_factory=list)
    """
    List of routes for this project.
    """

    fallback_config: dict[str, Any] = field(default_factory=dict)
    """
    Fallback configuration for the project.
    """

    maintenance_config: dict[str, Any] = field(default_factory=dict)
    """
    Maintenance mode configuration.
    """

    health_check_interval: float = 5.0
    """
    Health check interval in seconds.
    """

    health_check_timeout: float = 2.0
    """
    Health check timeout in seconds.
    """


class ProjectRoutingManager:
    """
    Manages project routing configuration and templates.

    Features:
    - Default routing templates for common project patterns
    - Domain + base path mapping
    - Project-specific routing rules
    - Integration with reverse proxy system
    - Fallback and maintenance configuration
    """

    def __init__(self, templates_dir: Path | None = None):
        """Initialize project routing manager.

        Args:
            templates_dir: Directory containing routing templates
        """
        self.templates_dir = templates_dir or Path(__file__).parent / "templates"
        self._project_configs: dict[str, ProjectRoutingConfig] = {}
        self._active_routes: dict[str, ProjectRoute] = {}

        logger.info("ProjectRoutingManager initialized")

    def create_default_config(
        self,
        project_name: str,
        domain: str = "localhost",
        base_path: str = "/",
        services: list[dict[str, Any]] | None = None,
    ) -> ProjectRoutingConfig:
        """
        Create a default routing configuration for a project.

        Args:
            project_name: Name of the project
            domain: Primary domain for the project
            base_path: Base path prefix for all routes
            services: List of services to create routes for

        Returns:
            Project routing configuration
        """
        routes = []

        if services:
            for service in services:
                route = ProjectRoute(
                    project_name=project_name,
                    path_prefix=f"{base_path.rstrip('/')}/{service.get('name', 'service')}",
                    domain=domain,
                    service_name=service.get("name", "service"),
                    port=service.get("port", 8000),
                    host=service.get("host", "localhost"),
                    health_check_path=service.get("health_check_path", "/health"),
                    metadata=service.get("metadata", {}),
                )
                routes.append(route)

        config = ProjectRoutingConfig(
            project_name=project_name,
            domain=domain,
            base_path=base_path,
            routes=routes,
            fallback_config={
                "page_type": "loading",
                "service_name": project_name,
                "refresh_interval": 5,
                "message": f"{project_name} is starting up...",
            },
            maintenance_config={
                "enabled": False,
                "message": f"{project_name} is under maintenance",
                "estimated_duration": "30 minutes",
            },
        )

        self._project_configs[project_name] = config
        logger.info(f"Created default routing config for project '{project_name}'")

        return config

    def add_route(
        self,
        project_name: str,
        service_name: str,
        port: int,
        path_prefix: str | None = None,
        domain: str | None = None,
        host: str = "localhost",
        health_check_path: str = "/health",
        metadata: dict[str, Any] | None = None,
    ) -> ProjectRoute:
        """
        Add a route to a project.

        Args:
            project_name: Name of the project
            service_name: Name of the service
            port: Port where the service is running
            path_prefix: Path prefix for the route
            domain: Domain for the route
            host: Host where the service is running
            health_check_path: Health check endpoint path
            metadata: Additional metadata

        Returns:
            Created route
        """
        config = self._project_configs.get(project_name)
        if not config:
            config = self.create_default_config(project_name)

        if not path_prefix:
            path_prefix = f"/{service_name}"

        if not domain:
            domain = config.domain

        route = ProjectRoute(
            project_name=project_name,
            path_prefix=path_prefix,
            domain=domain,
            service_name=service_name,
            port=port,
            host=host,
            health_check_path=health_check_path,
            metadata=metadata or {},
        )

        config.routes.append(route)
        self._active_routes[f"{project_name}:{service_name}"] = route

        logger.info(
            f"Added route '{path_prefix}' for service '{service_name}' in project '{project_name}'",
        )

        return route

    def remove_route(
        self,
        project_name: str,
        service_name: str,
    ) -> bool:
        """
        Remove a route from a project.

        Args:
            project_name: Name of the project
            service_name: Name of the service

        Returns:
            True if route was removed
        """
        config = self._project_configs.get(project_name)
        if not config:
            return False

        # Remove from config
        config.routes = [r for r in config.routes if r.service_name != service_name]

        # Remove from active routes
        route_key = f"{project_name}:{service_name}"
        if route_key in self._active_routes:
            del self._active_routes[route_key]
            logger.info(f"Removed route for service '{service_name}' in project '{project_name}'")
            return True

        return False

    def get_project_routes(
        self,
        project_name: str,
    ) -> list[ProjectRoute]:
        """
        Get all routes for a project.

        Args:
            project_name: Name of the project

        Returns:
            List of routes for the project
        """
        config = self._project_configs.get(project_name)
        if not config:
            return []

        return config.routes

    def get_route_by_path(
        self,
        path: str,
        domain: str | None = None,
    ) -> ProjectRoute | None:
        """
        Find a route by path and optionally domain.

        Args:
            path: Path to match
            domain: Domain to match (optional)

        Returns:
            Matching route or None
        """
        for route in self._active_routes.values():
            if not route.is_active:
                continue

            if domain and route.domain != domain:
                continue

            if path.startswith(route.path_prefix):
                return route

        return None

    def get_project_config(
        self,
        project_name: str,
    ) -> ProjectRoutingConfig | None:
        """
        Get routing configuration for a project.

        Args:
            project_name: Name of the project

        Returns:
            Project routing configuration or None
        """
        return self._project_configs.get(project_name)

    def update_fallback_config(
        self,
        project_name: str,
        fallback_config: dict[str, Any],
    ) -> None:
        """
        Update fallback configuration for a project.

        Args:
            project_name: Name of the project
            fallback_config: Fallback configuration
        """
        config = self._project_configs.get(project_name)
        if not config:
            config = self.create_default_config(project_name)

        config.fallback_config.update(fallback_config)
        logger.info(f"Updated fallback config for project '{project_name}'")

    def update_maintenance_config(
        self,
        project_name: str,
        maintenance_config: dict[str, Any],
    ) -> None:
        """
        Update maintenance configuration for a project.

        Args:
            project_name: Name of the project
            maintenance_config: Maintenance configuration
        """
        config = self._project_configs.get(project_name)
        if not config:
            config = self.create_default_config(project_name)

        config.maintenance_config.update(maintenance_config)
        logger.info(f"Updated maintenance config for project '{project_name}'")

    def enable_maintenance(
        self,
        project_name: str,
        message: str | None = None,
        estimated_duration: str | None = None,
    ) -> None:
        """
        Enable maintenance mode for a project.

        Args:
            project_name: Name of the project
            message: Maintenance message
            estimated_duration: Estimated duration
        """
        config = self._project_configs.get(project_name)
        if not config:
            config = self.create_default_config(project_name)

        config.maintenance_config.update(
            {
                "enabled": True,
                "message": message or f"{project_name} is under maintenance",
                "estimated_duration": estimated_duration or "30 minutes",
            },
        )

        logger.info(f"Enabled maintenance mode for project '{project_name}'")

    def disable_maintenance(
        self,
        project_name: str,
    ) -> None:
        """
        Disable maintenance mode for a project.

        Args:
            project_name: Name of the project
        """
        config = self._project_configs.get(project_name)
        if not config:
            return

        config.maintenance_config["enabled"] = False
        logger.info(f"Disabled maintenance mode for project '{project_name}'")

    def get_all_routes(self) -> list[ProjectRoute]:
        """
        Get all active routes across all projects.

        Returns:
            List of all active routes
        """
        return [route for route in self._active_routes.values() if route.is_active]

    def get_routes_by_domain(
        self,
        domain: str,
    ) -> list[ProjectRoute]:
        """
        Get all routes for a specific domain.

        Args:
            domain: Domain to filter by

        Returns:
            List of routes for the domain
        """
        return [
            route
            for route in self._active_routes.values()
            if route.is_active and route.domain == domain
        ]

    def export_config(
        self,
        project_name: str,
        format: str = "json",
    ) -> str:
        """
        Export routing configuration for a project.

        Args:
            project_name: Name of the project
            format: Export format (json, yaml)

        Returns:
            Exported configuration
        """
        config = self._project_configs.get(project_name)
        if not config:
            return ""

        if format == "json":
            import json

            return json.dumps(
                {
                    "project_name": config.project_name,
                    "domain": config.domain,
                    "base_path": config.base_path,
                    "routes": [
                        {
                            "path_prefix": route.path_prefix,
                            "domain": route.domain,
                            "service_name": route.service_name,
                            "port": route.port,
                            "host": route.host,
                            "health_check_path": route.health_check_path,
                            "metadata": route.metadata,
                            "is_active": route.is_active,
                        }
                        for route in config.routes
                    ],
                    "fallback_config": config.fallback_config,
                    "maintenance_config": config.maintenance_config,
                    "health_check_interval": config.health_check_interval,
                    "health_check_timeout": config.health_check_timeout,
                },
                indent=2,
            )
        if format == "yaml":
            import yaml

            return yaml.dump(
                {
                    "project_name": config.project_name,
                    "domain": config.domain,
                    "base_path": config.base_path,
                    "routes": [
                        {
                            "path_prefix": route.path_prefix,
                            "domain": route.domain,
                            "service_name": route.service_name,
                            "port": route.port,
                            "host": route.host,
                            "health_check_path": route.health_check_path,
                            "metadata": route.metadata,
                            "is_active": route.is_active,
                        }
                        for route in config.routes
                    ],
                    "fallback_config": config.fallback_config,
                    "maintenance_config": config.maintenance_config,
                    "health_check_interval": config.health_check_interval,
                    "health_check_timeout": config.health_check_timeout,
                },
                default_flow_style=False,
            )
        raise ValueError(f"Unsupported format: {format}")

    def import_config(
        self,
        project_name: str,
        config_data: str,
        format: str = "json",
    ) -> None:
        """
        Import routing configuration for a project.

        Args:
            project_name: Name of the project
            config_data: Configuration data
            format: Import format (json, yaml)
        """
        if format == "json":
            import json

            data = json.loads(config_data)
        elif format == "yaml":
            import yaml

            data = yaml.safe_load(config_data)
        else:
            raise ValueError(f"Unsupported format: {format}")

        # Create config from imported data
        config = ProjectRoutingConfig(
            project_name=data["project_name"],
            domain=data["domain"],
            base_path=data["base_path"],
            fallback_config=data.get("fallback_config", {}),
            maintenance_config=data.get("maintenance_config", {}),
            health_check_interval=data.get("health_check_interval", 5.0),
            health_check_timeout=data.get("health_check_timeout", 2.0),
        )

        # Create routes from imported data
        for route_data in data.get("routes", []):
            route = ProjectRoute(
                project_name=route_data["project_name"],
                path_prefix=route_data["path_prefix"],
                domain=route_data["domain"],
                service_name=route_data["service_name"],
                port=route_data["port"],
                host=route_data["host"],
                health_check_path=route_data["health_check_path"],
                metadata=route_data.get("metadata", {}),
                is_active=route_data.get("is_active", True),
            )
            config.routes.append(route)
            self._active_routes[f"{project_name}:{route.service_name}"] = route

        self._project_configs[project_name] = config
        logger.info(f"Imported routing config for project '{project_name}'")
