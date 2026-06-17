"""
Loading middleware.
"""

from __future__ import annotations

import logging
from datetime import datetime
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

try:
    from aiohttp import web
except Exception:
    web = None  # type: ignore

from .types import ServiceState

if TYPE_CHECKING:
    from .templates import TemplateRenderer

logger = logging.getLogger(__name__)


class LoadingMiddleware:
    """
    Shows loading page while service starts.
    """

    def __init__(self, renderer: TemplateRenderer, timeout: int = 120):
        self.renderer = renderer
        self.timeout = timeout
        self.service_states: dict[str, dict[str, Any]] = {}
        self.start_times: dict[str, datetime] = {}

    def set_service_state(self, service_name: str, state: ServiceState, **kwargs):
        self.service_states[service_name] = {"state": state, "updated_at": datetime.now(), **kwargs}
        if state == ServiceState.STARTING and service_name not in self.start_times:
            self.start_times[service_name] = datetime.now()

    def should_show_loading(self, service_name: str) -> bool:
        state_data = self.service_states.get(service_name, {})
        state = state_data.get("state")
        if state != ServiceState.STARTING:
            return False
        start_time = self.start_times.get(service_name)
        if start_time:
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > self.timeout:
                logger.warning("Service %s loading timeout (%ss)", service_name, elapsed)
                return False
        return True

    async def handle(
        self, request: web.Request, service_name: str = "Service",
    ) -> web.Response | None:
        if not self.should_show_loading(service_name):
            return None
        state_data = self.service_states.get(service_name, {})
        start_time = self.start_times.get(service_name)
        elapsed = int((datetime.now() - start_time).total_seconds()) if start_time else 0
        context = {
            "service_name": service_name,
            "status_message": state_data.get("status_message", "Service is starting up..."),
            "port": state_data.get("port", "-"),
            "pid": state_data.get("pid", "-"),
            "uptime": f"{elapsed}s",
            "health_status": state_data.get("health_status", "Starting"),
            "state": state_data.get("state", ServiceState.STARTING).value,
            "refresh_interval": 5,
        }
        html = self.renderer.render("loading", context)
        return web.Response(text=html, content_type="text/html", status=HTTPStatus.OK)
