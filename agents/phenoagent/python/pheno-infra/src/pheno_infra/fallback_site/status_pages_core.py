"""
Status Pages - Core data structures and status management.

Provides:
- ServiceStatus, TunnelStatus, ProjectStatus dataclasses
- StatusPageManager for tracking and updates
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ServiceStatus:
    """Status information for a service."""

    service_name: str
    """Name of the service."""

    project_name: str
    """Name of the project."""

    status: str
    """Service status (running, starting, stopping, error, unknown)."""

    port: int
    """Port where the service is running."""

    host: str = "localhost"
    """Host where the service is running."""

    pid: int | None = None
    """Process ID of the service."""

    uptime: float = 0.0
    """Service uptime in seconds."""

    last_seen: float = field(default_factory=time.time)
    """Timestamp when service was last seen."""

    health_status: str = "unknown"
    """Health status of the service."""

    error_message: str | None = None
    """Error message if service is in error state."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional service metadata."""


@dataclass
class TunnelStatus:
    """Status information for a tunnel."""

    tunnel_id: str
    """Unique tunnel identifier."""

    project_name: str
    """Name of the project."""

    service_name: str
    """Name of the service."""

    hostname: str
    """Tunnel hostname."""

    port: int
    """Local port being tunneled."""

    status: str
    """Tunnel status (active, inactive, error, unknown)."""

    provider: str = "cloudflare"
    """Tunnel provider."""

    created_at: float = field(default_factory=time.time)
    """Timestamp when tunnel was created."""

    last_seen: float = field(default_factory=time.time)
    """Timestamp when tunnel was last seen."""

    health_status: str = "unknown"
    """Health status of the tunnel."""

    error_message: str | None = None
    """Error message if tunnel is in error state."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional tunnel metadata."""


@dataclass
class ProjectStatus:
    """Overall status for a project."""

    project_name: str
    """Name of the project."""

    overall_status: str = "unknown"
    """Overall project status (healthy, unhealthy, partial, maintenance, unknown)."""

    services: dict[str, ServiceStatus] = field(default_factory=dict)
    """Status of all services in the project."""

    tunnels: dict[str, TunnelStatus] = field(default_factory=dict)
    """Status of all tunnels in the project."""

    last_updated: float = field(default_factory=time.time)
    """Timestamp when project status was last updated."""

    maintenance_mode: bool = False
    """Whether the project is in maintenance mode."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional project metadata."""


class StatusPageManager:
    """
    Manages status pages with service and tunnel information.

    Features:
    - Service status tracking per project
    - Tunnel status and health monitoring
    - Process status and metadata
    - Real-time status updates
    - Project-specific status dashboards
    """

    def __init__(self):
        """Initialize status page manager."""
        self._project_status: dict[str, ProjectStatus] = {}
        self._status_callbacks: list[callable] = []

        logger.info("StatusPageManager initialized")

    def register_status_callback(self, callback: callable) -> None:
        """
        Register a callback for status updates.

        Args:
            callback: Callback function
        """
        self._status_callbacks.append(callback)
        logger.info("Registered status update callback")

    def unregister_status_callback(self, callback: callable) -> None:
        """
        Unregister a status update callback.

        Args:
            callback: Callback function
        """
        if callback in self._status_callbacks:
            self._status_callbacks.remove(callback)
            logger.info("Unregistered status update callback")

    def update_service_status(
        self,
        project_name: str,
        service_name: str,
        status: str,
        port: int,
        host: str = "localhost",
        pid: int | None = None,
        uptime: float = 0.0,
        health_status: str = "unknown",
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Update service status.

        Args:
            project_name: Name of the project
            service_name: Name of the service
            status: Service status
            port: Port where service is running
            host: Host where service is running
            pid: Process ID
            uptime: Service uptime in seconds
            health_status: Health status
            error_message: Error message if any
            metadata: Additional metadata
        """
        if project_name not in self._project_status:
            self._project_status[project_name] = ProjectStatus(
                project_name=project_name,
                overall_status="unknown",
            )

        project_status = self._project_status[project_name]

        service_status = ServiceStatus(
            service_name=service_name,
            project_name=project_name,
            status=status,
            port=port,
            host=host,
            pid=pid,
            uptime=uptime,
            last_seen=time.time(),
            health_status=health_status,
            error_message=error_message,
            metadata=metadata or {},
        )

        project_status.services[service_name] = service_status
        project_status.last_updated = time.time()

        self._update_project_status(project_name)
        self._notify_callbacks(project_name, "service", service_name, status)

        logger.debug(
            f"Updated service status for {project_name}:{service_name} - {status}",
        )

    def update_tunnel_status(
        self,
        project_name: str,
        tunnel_id: str,
        service_name: str,
        hostname: str,
        port: int,
        status: str,
        provider: str = "cloudflare",
        health_status: str = "unknown",
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Update tunnel status.

        Args:
            project_name: Name of the project
            tunnel_id: Tunnel ID
            service_name: Name of the service
            hostname: Tunnel hostname
            port: Local port being tunneled
            status: Tunnel status
            provider: Tunnel provider
            health_status: Health status
            error_message: Error message if any
            metadata: Additional metadata
        """
        if project_name not in self._project_status:
            self._project_status[project_name] = ProjectStatus(
                project_name=project_name,
                overall_status="unknown",
            )

        project_status = self._project_status[project_name]

        tunnel_status = TunnelStatus(
            tunnel_id=tunnel_id,
            project_name=project_name,
            service_name=service_name,
            hostname=hostname,
            port=port,
            status=status,
            provider=provider,
            last_seen=time.time(),
            health_status=health_status,
            error_message=error_message,
            metadata=metadata or {},
        )

        project_status.tunnels[tunnel_id] = tunnel_status
        project_status.last_updated = time.time()

        self._update_project_status(project_name)
        self._notify_callbacks(project_name, "tunnel", tunnel_id, status)

        logger.debug(f"Updated tunnel status for {project_name}:{tunnel_id} - {status}")

    def set_maintenance_mode(
        self,
        project_name: str,
        enabled: bool,
        message: str | None = None,
    ) -> None:
        """
        Set maintenance mode for a project.

        Args:
            project_name: Name of the project
            enabled: Whether maintenance mode is enabled
            message: Maintenance message
        """
        if project_name not in self._project_status:
            self._project_status[project_name] = ProjectStatus(
                project_name=project_name,
                overall_status="unknown",
            )

        project_status = self._project_status[project_name]
        project_status.maintenance_mode = enabled

        if message:
            project_status.metadata["maintenance_message"] = message

        project_status.last_updated = time.time()
        self._update_project_status(project_name)

        logger.info(f"Set maintenance mode for project '{project_name}': {enabled}")

    def get_project_status(self, project_name: str) -> ProjectStatus | None:
        """
        Get status for a project.

        Args:
            project_name: Name of the project

        Returns:
            Project status or None
        """
        return self._project_status.get(project_name)

    def get_service_status(
        self,
        project_name: str,
        service_name: str,
    ) -> ServiceStatus | None:
        """
        Get status for a service.

        Args:
            project_name: Name of the project
            service_name: Name of the service

        Returns:
            Service status or None
        """
        project_status = self._project_status.get(project_name)
        if not project_status:
            return None
        return project_status.services.get(service_name)

    def get_tunnel_status(
        self,
        project_name: str,
        tunnel_id: str,
    ) -> TunnelStatus | None:
        """
        Get status for a tunnel.

        Args:
            project_name: Name of the project
            tunnel_id: Tunnel ID

        Returns:
            Tunnel status or None
        """
        project_status = self._project_status.get(project_name)
        if not project_status:
            return None
        return project_status.tunnels.get(tunnel_id)

    def get_all_projects(self) -> list[str]:
        """
        Get all project names.

        Returns:
            List of project names
        """
        return list(self._project_status.keys())

    def _update_project_status(self, project_name: str) -> None:
        """
        Update overall project status based on services and tunnels.
        """
        project_status = self._project_status.get(project_name)
        if not project_status:
            return

        if project_status.maintenance_mode:
            project_status.overall_status = "maintenance"
            return

        if not project_status.services and not project_status.tunnels:
            project_status.overall_status = "unknown"
            return

        service_statuses = [s.status for s in project_status.services.values()]
        tunnel_statuses = [t.status for t in project_status.tunnels.values()]
        all_statuses = service_statuses + tunnel_statuses

        if not all_statuses:
            project_status.overall_status = "unknown"
            return

        if all(s in {"running", "active"} for s in all_statuses):
            project_status.overall_status = "healthy"
        elif any(s in ["error", "stopped", "inactive"] for s in all_statuses):
            project_status.overall_status = "unhealthy"
        elif any(s in ["starting", "stopping"] for s in all_statuses):
            project_status.overall_status = "partial"
        else:
            project_status.overall_status = "unknown"

    def _notify_callbacks(
        self,
        project_name: str,
        resource_type: str,
        resource_name: str,
        status: str,
    ) -> None:
        """
        Notify all registered callbacks of status updates.
        """
        for callback in self._status_callbacks:
            try:
                callback(project_name, resource_type, resource_name, status)
            except Exception as e:
                logger.exception("Error in status update callback")
