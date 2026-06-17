"""
Request handlers for the fallback server.
"""

from __future__ import annotations

import json
import logging
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from aiohttp import web

from ..templates import get_inline_error_page, render_logs_html

if TYPE_CHECKING:
    from .render import TemplateManager
    from .status import ServiceStatusRegistry

logger = logging.getLogger(__name__)


class FallbackRoutes:
    """
    HTTP handlers for fallback server routes.
    """

    def __init__(
        self,
        registry: ServiceStatusRegistry,
        templates: TemplateManager,
        *,
        service_manager: Any | None = None,
    ):
        self._registry = registry
        self._templates = templates
        self.service_manager = service_manager

    def bind_service_manager(self, manager: Any) -> None:
        """
        Attach a service manager after initialization.
        """
        self.service_manager = manager

    async def handle_request(self, request: web.Request) -> web.Response:
        template = self._templates.load(self._registry.current_page)
        if not template:
            template = get_inline_error_page()
        rendered = self._templates.render(template, self._registry.page_config)
        status = (
            HTTPStatus.SERVICE_UNAVAILABLE
            if self._registry.current_page != "loading"
            else HTTPStatus.OK
        )
        return web.Response(text=rendered, content_type="text/html", status=status)

    async def handle_dashboard(self, request: web.Request) -> web.Response:
        template = self._templates.load("dashboard")
        rendered = self._templates.render(template, self._registry.page_config)
        return web.Response(text=rendered, content_type="text/html")

    async def handle_status_api(self, request: web.Request) -> web.Response:
        status_data = self._registry.as_status_payload()
        proxy_info, fallback_info = self._collect_manager_status()
        status_data["proxy"] = proxy_info
        status_data["fallback"] = fallback_info
        return web.Response(text=json.dumps(status_data), content_type="application/json")

    async def handle_restart(self, request: web.Request) -> web.Response:
        service_name = request.match_info.get("service")
        if not self.service_manager:
            return web.json_response({"success": False, "error": "Service manager not configured"})
        try:
            success = await self.service_manager.reload_service(service_name)
            return web.json_response({"success": success, "service": service_name})
        except Exception as exc:
            logger.exception("Restart action failed: %s", exc)
            return web.json_response({"success": False, "error": str(exc)}, status=500)

    async def handle_stop(self, request: web.Request) -> web.Response:
        service_name = request.match_info.get("service")
        if not self.service_manager:
            return web.json_response({"success": False, "error": "Service manager not configured"})
        try:
            success = await self.service_manager.stop_service(service_name)
            return web.json_response({"success": success, "service": service_name})
        except Exception as exc:
            logger.exception("Stop action failed: %s", exc)
            return web.json_response({"success": False, "error": str(exc)}, status=500)

    async def handle_logs(self, request: web.Request) -> web.Response:
        service_name = request.match_info.get("service", "")
        lines = int(request.query.get("lines", "50"))
        follow = request.query.get("follow", "false").lower() == "true"
        format_type = request.query.get("format", "json")

        logs = self._registry.get_logs(service_name)
        logs = logs[-lines:] if lines > 0 else logs

        if format_type == "json":
            payload = {"service": service_name, "logs": logs, "count": len(logs), "follow": follow}
            return web.json_response(payload)

        html = render_logs_html(service_name, logs, follow)
        return web.Response(text=html, content_type="text/html")

    def _collect_manager_status(self) -> tuple[dict[str, Any], dict[str, Any]]:
        proxy_info: dict[str, Any] = {}
        fallback_info: dict[str, Any] = {}

        if not self.service_manager:
            return proxy_info, fallback_info

        try:
            import psutil  # type: ignore

            proxy = getattr(self.service_manager, "proxy_server", None)
            if proxy and getattr(proxy, "process", None):
                proc = proxy.process  # type: ignore[attr-defined]
                try:
                    ps = psutil.Process(proc.pid)
                    proxy_info = {
                        "pid": proc.pid,
                        "port": getattr(proxy, "proxy_port", "-"),
                        "cmdline": ps.cmdline(),
                        "status": ps.status(),
                    }
                except Exception:
                    proxy_info = {
                        "pid": proc.pid,
                        "port": getattr(proxy, "proxy_port", "-"),
                        "status": "unknown",
                    }

            fallback = getattr(self.service_manager, "fallback_server", None)
            if fallback and getattr(fallback, "runner", None):
                try:
                    fallback_info = {
                        "pid": getattr(fallback.runner, "process_pid", None),
                        "port": fallback.port,
                    }
                except Exception:
                    fallback_info = {"pid": None, "port": getattr(fallback, "port", "-")}
        except Exception:
            proxy_info = {}
            fallback_info = {}

        return proxy_info, fallback_info


__all__ = ["FallbackRoutes"]
