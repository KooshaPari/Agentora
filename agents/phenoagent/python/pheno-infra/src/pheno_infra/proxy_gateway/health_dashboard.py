"""
Health Dashboard - Project metadata integration for status dashboards

Provides enhanced health monitoring with:
- Project-specific health status
- Service dependency tracking
- Resource health aggregation
- Status dashboard generation
- Real-time health updates
"""

import asyncio
import contextlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ServiceHealth:
    """
    Health status for a service.
    """

    service_name: str
    """
    Name of the service.
    """

    project_name: str
    """
    Name of the project.
    """

    status: str
    """
    Health status (healthy, unhealthy, starting, stopping, error).
    """

    port: int
    """
    Port where the service is running.
    """

    host: str = "localhost"
    """
    Host where the service is running.
    """

    last_check: float = field(default_factory=time.time)
    """
    Timestamp of last health check.
    """

    response_time: float = 0.0
    """
    Response time in milliseconds.
    """

    error_message: str | None = None
    """
    Error message if unhealthy.
    """

    metadata: dict[str, Any] = field(default_factory=dict)
    """
    Additional metadata.
    """

    dependencies: list[str] = field(default_factory=list)
    """
    List of service dependencies.
    """

    uptime: float = 0.0
    """
    Service uptime in seconds.
    """


@dataclass
class ProjectHealth:
    """
    Health status for a project.
    """

    project_name: str
    """
    Name of the project.
    """

    overall_status: str
    """
    Overall project status (healthy, unhealthy, partial, maintenance).
    """

    services: dict[str, ServiceHealth] = field(default_factory=dict)
    """
    Health status of all services in the project.
    """

    last_updated: float = field(default_factory=time.time)
    """
    Timestamp of last update.
    """

    maintenance_mode: bool = False
    """
    Whether the project is in maintenance mode.
    """

    metadata: dict[str, Any] = field(default_factory=dict)
    """
    Additional project metadata.
    """


class HealthDashboard:
    """
    Health dashboard with project metadata integration.

    Features:
    - Project-specific health status tracking
    - Service dependency monitoring
    - Resource health aggregation
    - Real-time status updates
    - Dashboard generation
    """

    def __init__(self):
        """Initialize health dashboard."""
        self._project_health: dict[str, ProjectHealth] = {}
        self._health_checkers: dict[str, callable] = {}
        self._update_callbacks: list[callable] = []
        self._monitoring_task: asyncio.Task | None = None
        self._shutdown = False

        logger.info("HealthDashboard initialized")

    async def initialize(self) -> None:
        """Initialize the health dashboard."""
        if self._monitoring_task is None:
            self._monitoring_task = asyncio.create_task(self._monitor_health())

        logger.info("HealthDashboard initialized")

    def register_health_checker(
        self,
        service_name: str,
        checker: callable,
    ) -> None:
        """
        Register a health checker for a service.

        Args:
            service_name: Name of the service
            checker: Health check function
        """
        self._health_checkers[service_name] = checker
        logger.info(f"Registered health checker for service '{service_name}'")

    def unregister_health_checker(
        self,
        service_name: str,
    ) -> None:
        """
        Unregister a health checker for a service.

        Args:
            service_name: Name of the service
        """
        if service_name in self._health_checkers:
            del self._health_checkers[service_name]
            logger.info(f"Unregistered health checker for service '{service_name}'")

    def add_update_callback(
        self,
        callback: callable,
    ) -> None:
        """
        Add a callback for health updates.

        Args:
            callback: Callback function
        """
        self._update_callbacks.append(callback)
        logger.info("Added health update callback")

    def remove_update_callback(
        self,
        callback: callable,
    ) -> None:
        """
        Remove a health update callback.

        Args:
            callback: Callback function
        """
        if callback in self._update_callbacks:
            self._update_callbacks.remove(callback)
            logger.info("Removed health update callback")

    def update_service_health(
        self,
        project_name: str,
        service_name: str,
        status: str,
        port: int,
        host: str = "localhost",
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
        dependencies: list[str] | None = None,
    ) -> None:
        """
        Update health status for a service.

        Args:
            project_name: Name of the project
            service_name: Name of the service
            status: Health status
            port: Port where the service is running
            host: Host where the service is running
            error_message: Error message if unhealthy
            metadata: Additional metadata
            dependencies: List of service dependencies
        """
        # Get or create project health
        if project_name not in self._project_health:
            self._project_health[project_name] = ProjectHealth(
                project_name=project_name,
                overall_status="unknown",
            )

        project_health = self._project_health[project_name]

        # Update service health
        service_health = ServiceHealth(
            service_name=service_name,
            project_name=project_name,
            status=status,
            port=port,
            host=host,
            last_check=time.time(),
            error_message=error_message,
            metadata=metadata or {},
            dependencies=dependencies or [],
        )

        project_health.services[service_name] = service_health
        project_health.last_updated = time.time()

        # Update overall project status
        self._update_project_status(project_name)

        # Notify callbacks
        self._notify_callbacks(project_name, service_name, status)

        logger.debug(
            f"Updated health for service '{service_name}' in project '{project_name}': {status}",
        )

    def set_maintenance_mode(
        self,
        project_name: str,
        enabled: bool,
    ) -> None:
        """
        Set maintenance mode for a project.

        Args:
            project_name: Name of the project
            enabled: Whether maintenance mode is enabled
        """
        if project_name not in self._project_health:
            self._project_health[project_name] = ProjectHealth(
                project_name=project_name,
                overall_status="unknown",
            )

        project_health = self._project_health[project_name]
        project_health.maintenance_mode = enabled

        if enabled:
            project_health.overall_status = "maintenance"
        else:
            self._update_project_status(project_name)

        logger.info(f"Set maintenance mode for project '{project_name}': {enabled}")

    def get_project_health(
        self,
        project_name: str,
    ) -> ProjectHealth | None:
        """
        Get health status for a project.

        Args:
            project_name: Name of the project

        Returns:
            Project health status or None
        """
        return self._project_health.get(project_name)

    def get_service_health(
        self,
        project_name: str,
        service_name: str,
    ) -> ServiceHealth | None:
        """
        Get health status for a service.

        Args:
            project_name: Name of the project
            service_name: Name of the service

        Returns:
            Service health status or None
        """
        project_health = self._project_health.get(project_name)
        if not project_health:
            return None

        return project_health.services.get(service_name)

    def get_all_projects(self) -> list[str]:
        """
        Get all project names.

        Returns:
            List of project names
        """
        return list(self._project_health.keys())

    def get_healthy_services(
        self,
        project_name: str,
    ) -> list[ServiceHealth]:
        """
        Get all healthy services in a project.

        Args:
            project_name: Name of the project

        Returns:
            List of healthy services
        """
        project_health = self._project_health.get(project_name)
        if not project_health:
            return []

        return [
            service for service in project_health.services.values() if service.status == "healthy"
        ]

    def get_unhealthy_services(
        self,
        project_name: str,
    ) -> list[ServiceHealth]:
        """
        Get all unhealthy services in a project.

        Args:
            project_name: Name of the project

        Returns:
            List of unhealthy services
        """
        project_health = self._project_health.get(project_name)
        if not project_health:
            return []

        return [
            service
            for service in project_health.services.values()
            if service.status in ["unhealthy", "error"]
        ]

    def get_dashboard_data(
        self,
        project_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Get dashboard data for display.

        Args:
            project_name: Specific project name (None for all projects)

        Returns:
            Dashboard data
        """
        if project_name:
            project_health = self._project_health.get(project_name)
            if not project_health:
                return {"error": f"Project '{project_name}' not found"}

            return self._format_project_data(project_health)
        return {
            "projects": [
                self._format_project_data(project_health)
                for project_health in self._project_health.values()
            ],
            "summary": self._get_summary_data(),
        }

    def ingest_registry_snapshot(self, snapshot: dict[str, Any]) -> None:
        """Update dashboard state from a proxy registry snapshot."""

        collected_at = snapshot.get("collected_at", time.time())
        upstreams: list[dict[str, Any]] = snapshot.get("upstreams", [])  # type: ignore[assignment]
        seen_services: dict[str, set[str]] = {}

        for record in upstreams:
            project = record.get("project") or record.get("tenant") or "default"
            service = record.get("service") or (
                (record.get("path_prefix") or "/").strip("/") or "service"
            )
            status = "healthy" if record.get("healthy") else "unhealthy"

            seen_services.setdefault(project, set()).add(service)

            project_health = self._project_health.setdefault(
                project,
                ProjectHealth(project_name=project, overall_status="unknown"),
            )

            existing = project_health.services.get(service)
            previous_status = existing.status if existing else None

            metadata = dict(record.get("metadata") or {})
            metadata.setdefault("path_prefix", record.get("path_prefix"))
            metadata.setdefault("last_changed", record.get("last_changed"))

            if existing:
                existing.status = status
                existing.port = int(record.get("port", existing.port))
                existing.host = record.get("host", existing.host)
                existing.last_check = record.get("last_checked", existing.last_check)
                existing.metadata.update(metadata)
            else:
                existing = ServiceHealth(
                    service_name=service,
                    project_name=project,
                    status=status,
                    port=int(record.get("port", 0) or 0),
                    host=record.get("host", "localhost"),
                    last_check=record.get("last_checked", time.time()),
                    metadata=metadata,
                )
                project_health.services[service] = existing

            project_health.last_updated = collected_at
            project_health.metadata.update(metadata)

            if previous_status != status:
                self._notify_callbacks(project, service, status)

        # Remove services no longer present in snapshot
        for project, project_health in self._project_health.items():
            current = seen_services.get(project, set())
            stale_services = [name for name in project_health.services if name not in current]
            for service in stale_services:
                del project_health.services[service]

            project_health.last_updated = collected_at
            self._update_project_status(project)

    def export_health_data(
        self,
        project_name: str | None = None,
        format: str = "json",
    ) -> str:
        """
        Export health data.

        Args:
            project_name: Specific project name (None for all projects)
            format: Export format (json, yaml)

        Returns:
            Exported health data
        """
        data = self.get_dashboard_data(project_name)

        if format == "json":
            return json.dumps(data, indent=2, default=str)
        if format == "yaml":
            import yaml

            return yaml.dump(data, default_flow_style=False, default_style=str)
        raise ValueError(f"Unsupported format: {format}")

    # ========== Private helper methods ==========

    def _update_project_status(
        self,
        project_name: str,
    ) -> None:
        """
        Update overall project status based on service health.
        """
        project_health = self._project_health.get(project_name)
        if not project_health:
            return

        if project_health.maintenance_mode:
            project_health.overall_status = "maintenance"
            return

        if not project_health.services:
            project_health.overall_status = "unknown"
            return

        # Count service statuses
        status_counts = {}
        for service in project_health.services.values():
            status_counts[service.status] = status_counts.get(service.status, 0) + 1

        # Determine overall status
        if status_counts.get("healthy", 0) == len(project_health.services):
            project_health.overall_status = "healthy"
        elif status_counts.get("unhealthy", 0) > 0 or status_counts.get("error", 0) > 0:
            project_health.overall_status = "unhealthy"
        elif status_counts.get("starting", 0) > 0 or status_counts.get("stopping", 0) > 0:
            project_health.overall_status = "partial"
        else:
            project_health.overall_status = "unknown"

    def _format_project_data(
        self,
        project_health: ProjectHealth,
    ) -> dict[str, Any]:
        """
        Format project health data for display.
        """
        services_data = []
        for service in project_health.services.values():
            services_data.append(
                {
                    "name": service.service_name,
                    "status": service.status,
                    "port": service.port,
                    "host": service.host,
                    "last_check": service.last_check,
                    "response_time": service.response_time,
                    "error_message": service.error_message,
                    "uptime": service.uptime,
                    "dependencies": service.dependencies,
                    "metadata": service.metadata,
                },
            )

        return {
            "project_name": project_health.project_name,
            "overall_status": project_health.overall_status,
            "maintenance_mode": project_health.maintenance_mode,
            "last_updated": project_health.last_updated,
            "services": services_data,
            "metadata": project_health.metadata,
        }

    def _get_summary_data(self) -> dict[str, Any]:
        """
        Get summary data for all projects.
        """
        total_projects = len(self._project_health)
        total_services = sum(len(project.services) for project in self._project_health.values())

        status_counts = {"healthy": 0, "unhealthy": 0, "partial": 0, "maintenance": 0, "unknown": 0}
        for project in self._project_health.values():
            status_counts[project.overall_status] = status_counts.get(project.overall_status, 0) + 1

        return {
            "total_projects": total_projects,
            "total_services": total_services,
            "status_counts": status_counts,
        }

    def _notify_callbacks(
        self,
        project_name: str,
        service_name: str,
        status: str,
    ) -> None:
        """
        Notify all registered callbacks of health updates.
        """
        for callback in self._update_callbacks:
            try:
                callback(project_name, service_name, status)
            except Exception as e:
                logger.exception(f"Error in health update callback: {e}")

    async def _monitor_health(self) -> None:
        """
        Background task to monitor health.
        """
        while not self._shutdown:
            try:
                # Run health checks
                for service_name, checker in self._health_checkers.items():
                    try:
                        # Find the service in project health
                        for project_health in self._project_health.values():
                            if service_name in project_health.services:
                                service = project_health.services[service_name]

                                # Run health check
                                start_time = time.time()
                                is_healthy = await checker()
                                response_time = (time.time() - start_time) * 1000

                                # Update service health
                                new_status = "healthy" if is_healthy else "unhealthy"
                                service.status = new_status
                                service.last_check = time.time()
                                service.response_time = response_time

                                # Update project status
                                self._update_project_status(project_health.project_name)

                                break
                    except Exception as e:
                        logger.exception(f"Health check failed for service '{service_name}': {e}")

                # Sleep for monitoring interval
                await asyncio.sleep(30.0)  # Check every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error in health monitoring: {e}")
                await asyncio.sleep(30.0)

    async def shutdown(self) -> None:
        """
        Shutdown the health dashboard.
        """
        self._shutdown = True

        if self._monitoring_task:
            self._monitoring_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._monitoring_task

        logger.info("HealthDashboard shutdown complete")
