"""
Request routing utilities for the proxy server.
"""

from __future__ import annotations

import logging
from http import HTTPStatus
from typing import TYPE_CHECKING

from aiohttp import web

logger = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable

    from aiohttp import ClientSession

    from .registry import UpstreamRegistry


class RequestRouter:
    """
    Dispatch inbound requests to upstream services or the fallback server.
    """

    def __init__(
        self,
        registry: UpstreamRegistry,
        *,
        session_getter: Callable[[], ClientSession | None],
        fallback_port: int,
        fallback_server: object | None,
        middleware,
    ):
        self._registry = registry
        self._session_getter = session_getter
        self._fallback_port = fallback_port
        self._fallback_server = fallback_server
        self._middleware = middleware

    async def handle_request(self, request: web.Request) -> web.Response:
        path = request.path
        if path.startswith(("/kinfra", "/__")):
            return await self._proxy_to_fallback(request)

        upstream = self._registry.find_upstream(path)
        if not upstream:
            return await self._render_fallback(request, "Service")

        service_name = upstream.path_prefix.strip("/") or "service"

        async def upstream_handler(req: web.Request) -> web.Response:
            return await self._proxy_to_upstream(req, upstream)

        try:
            return await self._middleware.handle_request(
                request, upstream_handler, service_name=service_name,
            )
        except Exception as exc:
            logger.exception("Middleware error: %s, falling back", exc)
            upstream.is_healthy = False
            return await self._render_fallback(request, service_name, error=str(exc))

    async def _proxy_to_upstream(self, request: web.Request, upstream) -> web.Response:
        session = self._require_session()
        upstream_url = f"http://{upstream.host}:{upstream.port}{request.path_qs}"
        try:
            payload = await request.read() if request.can_read_body else None
            async with session.request(
                method=request.method,
                url=upstream_url,
                headers=request.headers,
                data=payload,
                allow_redirects=False,
            ) as upstream_response:
                headers = self._filtered_headers(upstream_response.headers)
                body = await upstream_response.read()
                return web.Response(body=body, status=upstream_response.status, headers=headers)
        except Exception as exc:
            logger.exception("Upstream request failed: %s", exc)
            raise

    async def _proxy_to_fallback(self, request: web.Request) -> web.Response:
        session = self._require_session()
        fallback_url = f"http://localhost:{self._fallback_port}{request.path_qs}"
        try:
            payload = await request.read() if request.can_read_body else None
            async with session.request(
                method=request.method,
                url=fallback_url,
                headers=request.headers,
                data=payload,
                allow_redirects=False,
            ) as fallback_response:
                headers = self._filtered_headers(fallback_response.headers)
                body = await fallback_response.read()
                return web.Response(body=body, status=fallback_response.status, headers=headers)
        except Exception as exc:
            logger.exception("Fallback request failed: %s", exc)
            return web.Response(
                text=self._inline_error_page(), content_type="text/html", status=503,
            )

    async def _render_fallback(
        self,
        request: web.Request,
        service_name: str,
        error: str | None = None,
    ) -> web.Response:
        if self._fallback_server and hasattr(self._fallback_server, "_render_template"):
            try:
                template = self._fallback_server._load_template(self._fallback_server.current_page)
                if template is None:
                    from pheno.infra.fallback_site.templates import (
                        get_inline_error_page,
                    )

                    template = get_inline_error_page()
                html = self._fallback_server._render_template(
                    template, self._fallback_server.page_config,
                )
                state = getattr(self._fallback_server, "current_page", "loading")
                status_code = (
                    HTTPStatus.OK if state == "loading" else HTTPStatus.SERVICE_UNAVAILABLE
                )
                return web.Response(text=html, content_type="text/html", status=status_code)
            except Exception:
                logger.debug(
                    "FallbackServer render failed; using middleware fallback", exc_info=True,
                )

        if self._middleware and self._middleware.fallback:
            status = 502 if error else 404
            message = (
                f"Gateway error: {error}"
                if error
                else f"No service configured for path: {request.path}"
            )
            return await self._middleware.fallback.handle_error(
                status, service_name=service_name, message=message,
            )

        return await self._proxy_to_fallback(request)

    @staticmethod
    def _filtered_headers(headers) -> dict:
        cleaned = dict(headers)
        for header in ["Connection", "Keep-Alive", "Transfer-Encoding"]:
            cleaned.pop(header, None)
        return cleaned

    @staticmethod
    def _inline_error_page() -> str:
        return """<!DOCTYPE html>
<html>
<head><title>Service Unavailable</title></head>
<body style="font-family: sans-serif; text-align: center; padding: 50px;">
    <h1>503 Service Unavailable</h1>
    <p>The service is temporarily unavailable. Please try again in a few moments.</p>
</body>
</html>"""

    def _require_session(self):
        session = self._session_getter()
        if session is None:
            raise RuntimeError("Proxy session is not initialized")
        return session


__all__ = ["RequestRouter"]
