"""
Service info and health APIs (split from kinfra/kinfra.py).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..utils.process import is_port_free

if TYPE_CHECKING:
    from ..port_registry import ServiceInfo


class InfoMixin:
    def get_port(self, service_name: str) -> int | None:
        return self.allocator.get_service_port(service_name)  # type: ignore[attr-defined]

    def get_info(self, service_name: str) -> ServiceInfo | None:
        return self.registry.get_service(service_name)  # type: ignore[attr-defined]

    def list_services(self) -> dict[str, dict[str, Any]]:
        services: dict[str, dict[str, Any]] = {}
        for name, info in self.registry.get_all_services().items():  # type: ignore[attr-defined]
            services[name] = {
                "port": info.assigned_port,
                "pid": info.pid,
                "tunnel_id": info.tunnel_id,
                "hostname": info.tunnel_hostname,
                "url": f"https://{info.tunnel_hostname}" if info.tunnel_hostname else None,
                "last_seen": info.last_seen,
                "created_at": info.created_at,
            }
        return services

    def check_health(self, service_name: str) -> dict[str, Any]:
        service_info = self.registry.get_service(service_name)  # type: ignore[attr-defined]
        if not service_info:
            return {
                "service_name": service_name,
                "status": "not_found",
                "healthy": False,
                "message": f"Service '{service_name}' not found",
            }

        health: dict[str, Any] = {
            "service_name": service_name,
            "port": service_info.assigned_port,
            "status": "unknown",
            "healthy": False,
            "checks": {},
        }

        port_free = is_port_free(service_info.assigned_port)
        health["checks"]["port_bound"] = not port_free

        tunnel_status = self.tunnel_manager.get_tunnel_status(service_name)  # type: ignore[attr-defined]
        health["checks"]["tunnel"] = tunnel_status

        if health["checks"]["port_bound"] and tunnel_status.get("tunnel_running"):
            health["status"] = "healthy"
            health["healthy"] = True
            health["message"] = "Service is running and tunnel is active"
        elif health["checks"]["port_bound"]:
            health["status"] = "degraded"
            health["healthy"] = False
            health["message"] = "Service is running but tunnel may be down"
        else:
            health["status"] = "unhealthy"
            health["healthy"] = False
            health["message"] = "Service does not appear to be running"

        return health
