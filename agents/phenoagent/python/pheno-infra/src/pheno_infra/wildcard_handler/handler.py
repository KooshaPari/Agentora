"""
Wildcard route handler package: core handler class.
"""

from __future__ import annotations

import json
import logging
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

try:
    from aiohttp import web

    HAS_AIOHTTP = True
except Exception:
    HAS_AIOHTTP = False
    web = None  # type: ignore

if TYPE_CHECKING:  # pragma: no cover

    from ..status_page import StatusPageGenerator

from aiohttp import web

from .html import generate_404_html
from .suggest import get_route_suggestions

logger = logging.getLogger(__name__)


class WildcardStatusHandler:
    """
    Wildcard route handler for unmatched routes.
    """

    def __init__(
        self,
        status_generator: StatusPageGenerator,
        available_routes: list[dict[str, str]] | None = None,
        health_status: dict[str, Any] | None = None,
        environment: str = "production",
        uptime: str | None = None,
        metrics: dict[str, Any] | None = None,
        enable_suggestions: bool = True,
    ):
        if not HAS_AIOHTTP:
            raise ImportError("aiohttp is required for WildcardStatusHandler")
        self.status_generator = status_generator
        self.available_routes = available_routes or []
        self.health_status = health_status or {"status": "healthy", "checks": {}}
        self.environment = environment
        self.uptime = uptime
        self.metrics = metrics
        self.enable_suggestions = enable_suggestions

    async def handle_request(
        self, request: web.Request, available_routes: list[dict[str, str]] | None = None,
    ) -> web.Response:
        routes = available_routes or self.available_routes
        requested_path = request.path
        requested_method = request.method
        accept_header = request.headers.get("Accept", "")
        wants_json = ("application/json" in accept_header) or request.path.startswith("/api/")
        if wants_json:
            return self._handle_json_request(requested_path, requested_method, routes)
        return self._handle_html_request(requested_path, requested_method, routes)

    def _handle_json_request(
        self, requested_path: str, requested_method: str, routes: list[dict[str, str]],
    ) -> web.Response:
        response_data: dict[str, Any] = {
            "error": "Route not found",
            "message": f"The route {requested_method} {requested_path} does not exist",
            "requested": {"path": requested_path, "method": requested_method},
            "available_routes": routes,
        }
        if self.enable_suggestions:
            suggestions = get_route_suggestions(requested_path, routes)
            if suggestions:
                response_data["suggestions"] = suggestions
        return web.Response(
            text=json.dumps(response_data, indent=2),
            content_type="application/json",
            status=HTTPStatus.NOT_FOUND,
        )

    def _handle_html_request(
        self, requested_path: str, requested_method: str, routes: list[dict[str, str]],
    ) -> web.Response:
        suggestions: list[dict[str, str]] = []
        if self.enable_suggestions:
            suggestions = get_route_suggestions(requested_path, routes)
        html = generate_404_html(
            self.status_generator, requested_path, requested_method, routes, suggestions,
        )
        return web.Response(text=html, content_type="text/html", status=HTTPStatus.NOT_FOUND)

    def update_routes(self, routes: list[dict[str, str]]):
        self.available_routes = routes

    def update_health_status(self, health_status: dict[str, Any]):
        self.health_status = health_status

    def update_metrics(self, metrics: dict[str, Any]):
        self.metrics = metrics

    def update_uptime(self, uptime: str):
        self.uptime = uptime
