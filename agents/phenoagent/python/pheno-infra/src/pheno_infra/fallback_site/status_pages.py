"""Status Pages - Enhanced fallback pages with service/tunnel status.

Provides enhanced fallback pages with:
- Service status per project
- Tunnel status and health
- Process status and metadata
- Real-time status updates
- Project-specific status dashboards
"""

from __future__ import annotations

from typing import Any

from .status_pages_core import (
    ProjectStatus,
    ServiceStatus,
    StatusPageManager,
    TunnelStatus,
)
from .status_pages_templates import (
    generate_error_page,
    generate_loading_page,
    generate_maintenance_page,
    generate_status_dashboard,
)

__all__ = [
    "ProjectStatus",
    "ServiceStatus",
    "StatusPageManager",
    "TunnelStatus",
    "generate_error_page",
    "generate_loading_page",
    "generate_maintenance_page",
    "generate_status_dashboard",
]


class StatusPageManagerWithRendering(StatusPageManager):
    """StatusPageManager with HTML rendering capabilities."""

    def generate_status_page(
        self,
        project_name: str,
        page_type: str = "status",
    ) -> str:
        """
        Generate a status page for a project.

        Args:
            project_name: Name of the project
            page_type: Type of page (status, loading, error, maintenance)

        Returns:
            HTML content for the status page
        """
        project_status = self.get_project_status(project_name)
        if not project_status:
            return generate_error_page(f"Project '{project_name}' not found")

        if page_type == "status":
            return generate_status_dashboard(project_status)
        if page_type == "loading":
            return generate_loading_page(project_status)
        if page_type == "error":
            return generate_error_page(
                "Service temporarily unavailable",
                project_status,
            )
        if page_type == "maintenance":
            return generate_maintenance_page(project_status)
        return generate_error_page(f"Unknown page type: {page_type}")

    def generate_project_summary(
        self,
        project_name: str,
    ) -> dict[str, Any]:
        """
        Generate a project summary.

        Args:
            project_name: Name of the project

        Returns:
            Project summary data
        """
        project_status = self.get_project_status(project_name)
        if not project_status:
            return {"error": f"Project '{project_name}' not found"}

        service_counts = {}
        for service in project_status.services.values():
            status = service.status
            service_counts[status] = service_counts.get(status, 0) + 1

        tunnel_counts = {}
        for tunnel in project_status.tunnels.values():
            status = tunnel.status
            tunnel_counts[status] = tunnel_counts.get(status, 0) + 1

        return {
            "project_name": project_name,
            "overall_status": project_status.overall_status,
            "maintenance_mode": project_status.maintenance_mode,
            "last_updated": project_status.last_updated,
            "services": {
                "total": len(project_status.services),
                "by_status": service_counts,
            },
            "tunnels": {
                "total": len(project_status.tunnels),
                "by_status": tunnel_counts,
            },
            "metadata": project_status.metadata,
        }
