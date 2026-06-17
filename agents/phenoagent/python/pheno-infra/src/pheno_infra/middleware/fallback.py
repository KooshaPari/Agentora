"""
Fallback and maintenance middleware.
"""

from __future__ import annotations

import logging
from datetime import datetime
from http import HTTPStatus

try:
    from aiohttp import web
except Exception:
    web = None  # type: ignore

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .templates import TemplateRenderer

logger = logging.getLogger(__name__)


class FallbackMiddleware:
    """
    Render error pages based on status codes.
    """

    def __init__(self, renderer: TemplateRenderer):
        self.renderer = renderer

    async def handle_error(
        self,
        status_code: int,
        service_name: str = "Service",
        message: str | None = None,
        refresh_interval: int = 10,
    ) -> web.Response:
        template_map = {403: "403", 404: "404", 500: "500", 502: "502", 503: "503"}
        template_name = template_map.get(status_code, "503")
        context = {
            "service_name": service_name,
            "message": message or "",
            "refresh_interval": refresh_interval,
            "timestamp": datetime.now().isoformat(),
        }
        html = self.renderer.render(template_name, context)
        return web.Response(text=html, content_type="text/html", status=status_code)


class MaintenanceMiddleware:
    """
    Show maintenance page while maintenance is enabled.
    """

    def __init__(self, renderer: TemplateRenderer):
        self.renderer = renderer
        self.maintenance_mode = False
        self.maintenance_message: str | None = None
        self.estimated_duration: str | None = None

    def enable(self, message: str | None = None, estimated_duration: str | None = None):
        self.maintenance_mode = True
        self.maintenance_message = message
        self.estimated_duration = estimated_duration
        logger.info("Maintenance mode enabled")

    def disable(self):
        self.maintenance_mode = False
        self.maintenance_message = None
        self.estimated_duration = None
        logger.info("Maintenance mode disabled")

    async def handle(self, service_name: str = "Service") -> web.Response | None:
        if not self.maintenance_mode:
            return None
        context = {
            "service_name": service_name,
            "message": self.maintenance_message or "We're performing scheduled maintenance.",
            "estimated_duration": self.estimated_duration or "shortly",
            "refresh_interval": 30,
            "timestamp": datetime.now().isoformat(),
        }
        html = self.renderer.render("maintenance", context)
        return web.Response(
            text=html, content_type="text/html", status=HTTPStatus.SERVICE_UNAVAILABLE,
        )
