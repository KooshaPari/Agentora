"""
Admin API handlers for runtime upstream management.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from aiohttp import web

if TYPE_CHECKING:
    from .registry import UpstreamRegistry

logger = logging.getLogger(__name__)


class AdminAPI:
    """
    Expose dynamic upstream management endpoints.
    """

    def __init__(self, registry: UpstreamRegistry):
        self._registry = registry

    async def add_upstream(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
            path_prefix = data.get("path_prefix", "/")
            port = int(data["port"])
            host = data.get("host", "localhost")
            service_name = data.get("service_name")
            tenant = data.get("tenant")
            metadata: dict[str, Any] | None = data.get("metadata")
            if metadata is not None and not isinstance(metadata, dict):
                raise ValueError("metadata must be a dictionary when provided")

            self._registry.add_upstream(
                path_prefix,
                host=host,
                port=port,
                service_name=service_name,
                tenant=tenant,
                metadata=metadata,
            )
            logger.info(
                "Added upstream via admin API: %s -> %s:%s tenant=%s",
                path_prefix,
                host,
                port,
                tenant,
            )
            return web.json_response(
                {"ok": True, "path_prefix": path_prefix, "port": port, "tenant": tenant},
            )
        except Exception as exc:
            logger.exception("Admin add_upstream failed: %s", exc)
            return web.json_response({"ok": False, "error": str(exc)}, status=400)

    async def remove_upstream(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
            path_prefix = data.get("path_prefix", "/")
            removed = self._registry.remove_upstream(path_prefix)
            return web.json_response({"ok": bool(removed), "path_prefix": path_prefix})
        except Exception as exc:
            logger.exception("Admin remove_upstream failed: %s", exc)
            return web.json_response({"ok": False, "error": str(exc)}, status=400)

    async def list_upstreams(self, request: web.Request) -> web.Response:
        try:
            tenant_filter: str | None = request.query.get("tenant")
            items = self._registry.list_upstreams(tenant_filter)
            return web.json_response({"ok": True, "upstreams": items})
        except Exception as exc:
            logger.exception("Admin list_upstreams failed: %s", exc)
            return web.json_response({"ok": False, "error": str(exc)}, status=400)

    async def deregister_tenant(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
            tenant = data.get("tenant")
            prefixes = data.get("path_prefixes") or []
            if not tenant and not prefixes:
                return web.json_response(
                    {"ok": False, "error": "Provide 'tenant' or 'path_prefixes'"}, status=400,
                )

            removed = self._registry.deregister_tenant(tenant, prefixes)
            return web.json_response({"ok": True, "removed": removed})
        except Exception as exc:
            logger.exception("Admin deregister_tenant failed: %s", exc)
            return web.json_response({"ok": False, "error": str(exc)}, status=400)


__all__ = ["AdminAPI"]
