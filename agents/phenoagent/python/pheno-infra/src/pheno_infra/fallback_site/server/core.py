"""
Core fallback server orchestration.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

try:  # pragma: no cover - optional dependency
    from aiohttp import web

    HAS_AIOHTTP = True
except ImportError:  # pragma: no cover - degrade gracefully
    HAS_AIOHTTP = False
    web = None  # type: ignore

from .admin import TenantAdminHandlers
from .render import TemplateManager
from .routes import FallbackRoutes
from .status import ServiceStatusRegistry

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


class FallbackServer:
    """
    Lightweight HTTP server for serving error, loading, and status pages.
    """

    def __init__(self, port: int = 9000, templates_dir: Path | None = None):
        if not HAS_AIOHTTP:
            raise ImportError(
                "aiohttp is required for FallbackServer. Install with: pip install aiohttp",
            )

        self.port = port
        self.templates_dir = templates_dir

        self.registry = ServiceStatusRegistry()
        self.template_manager = TemplateManager(templates_dir)
        self.tenant_admin = TenantAdminHandlers(self.registry)
        self.routes = FallbackRoutes(self.registry, self.template_manager)

        self.app = web.Application()
        self.runner: web.AppRunner | None = None
        self.site: web.TCPSite | None = None
        self.service_manager: Any | None = None

        self._register_routes()
        logger.info("FallbackServer initialized on port %s", port)

    def attach_service_manager(self, manager: Any) -> None:
        """
        Bind a service manager for restart/stop actions.
        """
        self.service_manager = manager
        self.routes.bind_service_manager(manager)

    async def start(self) -> None:
        """
        Start the aiohttp application.
        """
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            self.site = web.TCPSite(self.runner, "127.0.0.1", self.port)
            await self.site.start()
            logger.info("Fallback server started on http://127.0.0.1:%s", self.port)
        except Exception as exc:
            logger.exception("Failed to start fallback server: %s", exc)
            raise

    async def stop(self) -> None:
        """
        Stop the HTTP server and release resources.
        """
        if self.site:
            await self.site.stop()
            logger.info("Fallback server site stopped")
            self.site = None

        if self.runner:
            await self.runner.cleanup()
            logger.info("Fallback server runner cleaned up")
            self.runner = None

    def set_page(
        self,
        page_type: str = "loading",
        *,
        service_name: str = "Service",
        refresh_interval: int = 5,
        message: str | None = None,
    ) -> None:
        """
        Update the current fallback page metadata.
        """
        self.registry.set_page(
            page_type, service_name=service_name, refresh_interval=refresh_interval, message=message,
        )

    def update_service_status(self, service_name: str, **fields: Any) -> None:
        """
        Persist service status details for display.
        """
        self.registry.update_service_status(service_name, **fields)

    def remove_services_with_prefix(self, prefix: str) -> int:
        """
        Remove tracked services that match a prefix.
        """
        return self.registry.remove_services_with_prefix(prefix)

    def _register_routes(self) -> None:
        """
        Configure aiohttp routes for public and admin endpoints.
        """
        self.app.router.add_get("/kinfra", self.routes.handle_dashboard)
        self.app.router.add_get("/__status__", self.routes.handle_status_api)
        self.app.router.add_post("/__action__/restart/{service}", self.routes.handle_restart)
        self.app.router.add_post("/__action__/stop/{service}", self.routes.handle_stop)
        self.app.router.add_get("/__logs__/{service}", self.routes.handle_logs)

        self.app.router.add_post("/__admin__/tenant/status", self.tenant_admin.update_status)
        self.app.router.add_delete("/__admin__/tenant/status", self.tenant_admin.delete_status)
        self.app.router.add_get("/__admin__/tenant/status", self.tenant_admin.list_status)

        self.app.router.add_route("*", "/{path:.*}", self.routes.handle_request)


async def run_fallback_server(
    port: int = 9000,
    page_type: str = "loading",
    service_name: str = "Service",
    refresh_interval: int = 5,
) -> None:
    """
    Convenience helper to run the fallback server standalone.
    """
    server = FallbackServer(port=port)
    server.set_page(
        page_type=page_type, service_name=service_name, refresh_interval=refresh_interval,
    )
    await server.start()
    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutting down fallback server...")
        await server.stop()


__all__ = ["FallbackServer", "run_fallback_server"]
