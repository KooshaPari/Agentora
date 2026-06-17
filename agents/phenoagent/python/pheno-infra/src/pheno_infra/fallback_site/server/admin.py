"""
Administrative endpoints for tenant-level status management.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiohttp import web

if TYPE_CHECKING:
    from .status import ServiceStatusRegistry

logger = logging.getLogger(__name__)


class TenantAdminHandlers:
    """
    Expose tenant management handlers for the fallback server.
    """

    def __init__(self, registry: ServiceStatusRegistry):
        self._registry = registry

    async def update_status(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
            tenant = (data.get("tenant") or "").strip()
            service = (data.get("service_name") or "").strip()
            if not tenant or not service:
                return web.json_response(
                    {"ok": False, "error": "tenant and service_name required"}, status=400,
                )

            key = f"{tenant}:{service}"
            fields = {
                "status_message": data.get("status_message"),
                "port": data.get("port"),
                "pid": data.get("pid"),
                "uptime": data.get("uptime"),
                "health_status": data.get("health_status"),
                "state": data.get("state"),
                "logs": data.get("logs"),
                "steps": data.get("steps"),
                "last_output": data.get("last_output"),
            }
            self._registry.update_service_status(key, **fields)
            return web.json_response({"ok": True, "service": key})
        except Exception as exc:
            logger.exception("Admin update tenant status failed: %s", exc)
            return web.json_response({"ok": False, "error": str(exc)}, status=400)

    async def delete_status(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
            tenant = (data.get("tenant") or "").strip()
            service = (data.get("service_name") or "").strip()

            if not tenant and not service:
                return web.json_response(
                    {"ok": False, "error": "Provide tenant or service_name"}, status=400,
                )

            if tenant and not service:
                removed = self._registry.remove_services_with_prefix(f"{tenant}:")
            else:
                key = service if ":" in service else (f"{tenant}:{service}" if tenant else service)
                removed = 1 if self._registry.remove_service(key) else 0

            return web.json_response({"ok": True, "removed": removed})
        except Exception as exc:
            logger.exception("Admin delete tenant status failed: %s", exc)
            return web.json_response({"ok": False, "error": str(exc)}, status=400)

    async def list_status(self, request: web.Request) -> web.Response:
        try:
            tenant = (request.query.get("tenant") or "").strip()
            services = (
                self._registry.list_services(f"{tenant}:")
                if tenant
                else self._registry.list_services()
            )
            return web.json_response({"ok": True, "services": services})
        except Exception as exc:
            logger.exception("Admin list tenant status failed: %s", exc)
            return web.json_response({"ok": False, "error": str(exc)}, status=400)


__all__ = ["TenantAdminHandlers"]
