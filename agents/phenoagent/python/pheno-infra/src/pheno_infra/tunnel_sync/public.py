"""
Public API surface for TunnelManager.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..utils.health import check_tunnel_health

if TYPE_CHECKING:
    from .models import TunnelInfo

logger = logging.getLogger(__name__)


class PublicMixin:
    def start_tunnel(self, service_name: str, port: int, path: str = "/") -> TunnelInfo:
        self._log_tunnel(
            "Starting tunnel for service '%s' on port %s, path '%s'",
            service_name,
            port,
            path,
            verbose=True,
        )
        if self.config.use_unified_tunnel:
            return self._start_unified_tunnel_service(service_name, port, path)  # type: ignore[misc]
        return self._start_separate_tunnel(service_name, port)  # type: ignore[misc]

    def stop_tunnel(self, service_name: str) -> bool:
        self._log_tunnel("Stopping tunnel for service '%s'", service_name, verbose=True)
        success = self._stop_tunnel_process(service_name)  # type: ignore[misc]
        if self.config.use_unified_tunnel:
            try:
                self._unregister_unified_service(service_name)  # type: ignore[misc]
            except Exception as exc:
                logger.debug("Unified tunnel cleanup for '%s' failed: %s", service_name, exc)
        self.registry.update_service(service_name, tunnel_id=None, tunnel_hostname=None, config_path=None, pid=None)  # type: ignore[attr-defined]
        return success

    def get_service_url(self, service_name: str) -> str | None:
        service_info = self.registry.get_service(service_name)  # type: ignore[attr-defined]
        if service_info and service_info.tunnel_hostname:
            return f"https://{service_info.tunnel_hostname}"
        return None

    def get_tunnel_status(self, service_name: str) -> dict:
        service_info = self.registry.get_service(service_name)  # type: ignore[attr-defined]
        if not service_info:
            return {"status": "not_found", "message": f"Service '{service_name}' not found"}
        status = {
            "service_name": service_name,
            "port": service_info.assigned_port,
            "tunnel_id": service_info.tunnel_id,
            "hostname": service_info.tunnel_hostname,
            "url": (
                f"https://{service_info.tunnel_hostname}" if service_info.tunnel_hostname else None
            ),
            "process_running": service_name in self._running_processes,  # type: ignore[attr-defined]
            "last_seen": service_info.last_seen,
        }
        if service_info.tunnel_id:
            status["tunnel_running"] = self._is_tunnel_running(service_info.tunnel_id, service_info.tunnel_hostname)  # type: ignore[misc]
            if status["tunnel_running"]:
                status["tunnel_healthy"] = check_tunnel_health(
                    service_info.tunnel_hostname, service_info.assigned_port,
                )
        return status
