"""
Service status tracking for the fallback server.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class ServiceStatusRegistry:
    """
    Maintain fallback page configuration and per-service status.
    """

    def __init__(self):
        self.current_page = "loading"
        self.page_config: dict[str, Any] = {
            "service_name": "Service",
            "refresh_interval": 5,
            "message": None,
            "status_message": "Service is starting up...",
            "port": "-",
            "pid": "-",
            "uptime": "0s",
            "health_status": "Starting",
            "state": "starting",
            "logs": [],
            "steps": [],
        }
        self.service_status: dict[str, dict[str, Any]] = {}

    def set_page(
        self, page_type: str, *, service_name: str, refresh_interval: int, message: str | None,
    ) -> None:
        """
        Update the currently displayed fallback page metadata.
        """
        self.current_page = page_type
        self.page_config.update(
            {
                "service_name": service_name,
                "refresh_interval": refresh_interval,
                "message": message,
            },
        )
        logger.debug("Fallback page configured: %s for %s", page_type, service_name)

    def update_service_status(self, service_name: str, **fields: Any) -> None:
        """
        Update the status metadata for a service and mirror to the page config.
        """
        normalized = self._normalize_fields(fields)
        if not normalized:
            return

        self.service_status[service_name] = normalized
        self.page_config.update(normalized)
        logger.debug("Updated status for %s: %s", service_name, normalized.get("state", "unknown"))

    def remove_services_with_prefix(self, prefix: str) -> int:
        """
        Remove all services whose names share the provided prefix.
        """
        to_remove = [name for name in self.service_status if name.startswith(prefix)]
        for name in to_remove:
            self.service_status.pop(name, None)
        if to_remove:
            logger.info(
                "Removed %d services with prefix '%s' from fallback status", len(to_remove), prefix,
            )
        return len(to_remove)

    def remove_service(self, name: str) -> bool:
        """
        Remove a single tracked service by name.
        """
        removed = self.service_status.pop(name, None) is not None
        if removed:
            logger.info("Removed service '%s' from fallback status", name)
        return removed

    def as_status_payload(self) -> dict[str, Any]:
        """
        Return a serializable representation of the current status.
        """
        return {
            "service_name": self.page_config.get("service_name", "Service"),
            "status_message": self.page_config.get("status_message", "Service is starting up..."),
            "port": self.page_config.get("port", "-"),
            "pid": self.page_config.get("pid", "-"),
            "uptime": self.page_config.get("uptime", "0s"),
            "health_status": self.page_config.get("health_status", "Starting"),
            "state": self.page_config.get("state", "starting"),
            "timestamp": datetime.now().isoformat(),
            "services": self.service_status,
            "error_message": self.page_config.get("error_message"),
            "restart_count": self.page_config.get("restart_count", 0),
            "max_restart_attempts": self.page_config.get("max_restart_attempts", 3),
            "exception": self.page_config.get("exception"),
            "logs": self.page_config.get("logs", []),
        }

    def get_logs(self, service_name: str) -> list[dict[str, Any]]:
        """
        Retrieve log entries for a service.
        """
        service_data = self.service_status.get(service_name, {})
        logs_obj = service_data.get("logs", [])
        return logs_obj if isinstance(logs_obj, list) else []

    def list_services(self, tenant_prefix: str | None = None) -> dict[str, dict[str, Any]]:
        """
        Return a mapping of service status, optionally filtered by prefix.
        """
        if tenant_prefix:
            return {k: v for k, v in self.service_status.items() if k.startswith(tenant_prefix)}
        return dict(self.service_status)

    @staticmethod
    def _normalize_fields(fields: dict[str, Any]) -> dict[str, Any]:
        allowed_keys = {
            "status_message",
            "port",
            "pid",
            "uptime",
            "health_status",
            "state",
            "logs",
            "steps",
            "last_output",
        }
        normalized: dict[str, Any] = {}
        for key in allowed_keys:
            if key not in fields or fields[key] is None:
                continue
            value = fields[key]
            if key in {"port", "pid"}:
                normalized[key] = str(value)
            else:
                normalized[key] = value
        return normalized


__all__ = ["ServiceStatusRegistry"]
