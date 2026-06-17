"""
Smart Reverse Proxy Server - Health-aware reverse proxy with automatic fallback

Provides intelligent routing with health monitoring and automatic fallback to error pages
when upstream services are unavailable.
"""

import asyncio
import logging

try:
    from aiohttp import ClientSession, ClientTimeout, web

    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
    web = None
    ClientSession = None
    ClientTimeout = None


import contextlib

from aiohttp import ClientSession, web

from .utils.health import check_tcp_health

logger = logging.getLogger(__name__)


class UpstreamConfig:
    """
    Configuration for an upstream service.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8000,
        path_prefix: str = "",
        health_check_interval: float = 5.0,
        health_check_timeout: float = 2.0,
    ):
        self.host = host
        self.port = port
        self.path_prefix = path_prefix.rstrip("/")
        self.health_check_interval = health_check_interval
        self.health_check_timeout = health_check_timeout
        self.is_healthy = False
        self.last_health_check = 0.0


class SmartProxyServer:
    """Health-aware reverse proxy with automatic fallback.

    Features:
    - Routes requests to upstream service when healthy
    - Routes to fallback server when upstream is down
    - Continuous health monitoring
    - WebSocket support
    - Request/response logging
    - Path-based routing for multiple upstreams
    """

    def __init__(
        self,
        proxy_port: int = 9100,
        fallback_port: int = 9000,
        default_upstream_port: int = 8000,
        fallback_server: any | None = None,
    ):
        """Initialize smart proxy server.

        Args:
            proxy_port: Port for the proxy server (default: 9100)
            fallback_port: Port for the fallback error server (default: 9000)
            default_upstream_port: Default upstream service port (default: 8000)
            fallback_server: Optional FallbackServer instance for status updates
        """
        if not HAS_AIOHTTP:
            raise ImportError(
                "aiohttp is required for SmartProxyServer. Install with: pip install aiohttp",
            )

        self.proxy_port = proxy_port
        self.fallback_port = fallback_port
        self.default_upstream_port = default_upstream_port

        # Upstream configurations
        self.upstreams: dict[str, UpstreamConfig] = {}

        # Fallback configuration
        self.fallback_host = "localhost"
        self.fallback_server = fallback_server

        # HTTP client for proxying
        self.session: ClientSession | None = None

        # Web app
        self.app = web.Application()
        self.runner: web.AppRunner | None = None
        self.site: web.TCPSite | None = None

        # Health monitoring task
        self._health_monitor_task: asyncio.Task | None = None
        self._shutdown = False

        # Setup routes
        self.app.router.add_route("*", "/{path:.*}", self._handle_request)

        logger.info(f"SmartProxyServer initialized on port {proxy_port}")

    def add_upstream(self, path_prefix: str, port: int, host: str = "localhost"):
        """Add an upstream service to route to.

        Args:
            path_prefix: Path prefix for this upstream (e.g., "/api" or "/")
            port: Upstream service port
            host: Upstream service host (default: "localhost")
        """
        upstream = UpstreamConfig(host=host, port=port, path_prefix=path_prefix)
        self.upstreams[path_prefix] = upstream
        logger.info(f"Added upstream: {path_prefix} -> http://{host}:{port}")

    async def start(self):
        """
        Start the proxy server and health monitoring.
        """
        try:
            # Initialize HTTP client session
            timeout = ClientTimeout(total=30)
            self.session = ClientSession(timeout=timeout)

            # Start web server
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            self.site = web.TCPSite(self.runner, "127.0.0.1", self.proxy_port)
            await self.site.start()

            logger.info(f"Smart proxy server started on http://127.0.0.1:{self.proxy_port}")

            # Start health monitoring
            self._health_monitor_task = asyncio.create_task(self._monitor_health())

        except Exception as e:
            logger.exception(f"Failed to start proxy server: {e}")
            raise

    async def stop(self):
        """
        Stop the proxy server.
        """
        self._shutdown = True

        # Stop health monitoring
        if self._health_monitor_task:
            self._health_monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._health_monitor_task

        # Close client session
        if self.session:
            await self.session.close()

        # Stop web server
        if self.site:
            await self.site.stop()
            logger.info("Proxy server site stopped")

        if self.runner:
            await self.runner.cleanup()
            logger.info("Proxy server runner cleaned up")

    async def _monitor_health(self):
        """
        Continuously monitor upstream service health.
        """
        logger.info("Health monitoring started")

        try:
            while not self._shutdown:
                for path_prefix, upstream in self.upstreams.items():
                    # Check upstream health
                    healthy = await asyncio.get_event_loop().run_in_executor(
                        None,
                        check_tcp_health,
                        upstream.host,
                        upstream.port,
                        upstream.health_check_timeout,
                    )

                    if healthy != upstream.is_healthy:
                        status = "healthy" if healthy else "unhealthy"
                        logger.info(f"Upstream {path_prefix} is now {status}")
                        upstream.is_healthy = healthy

                        # Update fallback server with status
                        if self.fallback_server:
                            service_name = path_prefix.strip("/") or "service"
                            if healthy:
                                self.fallback_server.update_service_status(
                                    service_name=service_name,
                                    status_message="Service is ready",
                                    health_status="Healthy",
                                    state="running",
                                )
                            else:
                                self.fallback_server.update_service_status(
                                    service_name=service_name,
                                    status_message="Service is unhealthy, attempting restart...",
                                    health_status="Unhealthy",
                                    state="error",
                                )

                await asyncio.sleep(5.0)  # Check every 5 seconds

        except asyncio.CancelledError:
            logger.info("Health monitoring stopped")

    def _find_upstream(self, path: str) -> UpstreamConfig | None:
        """
        Find the appropriate upstream for a given path.
        """
        # Sort by path length (longest match first)
        sorted_upstreams = sorted(self.upstreams.items(), key=lambda x: len(x[0]), reverse=True)

        for path_prefix, upstream in sorted_upstreams:
            if path.startswith(path_prefix) or path_prefix == "/":
                return upstream

        return None

    async def _handle_request(self, request: "web.Request") -> "web.Response":
        """
        Handle incoming HTTP requests with health-aware routing.
        """
        path = request.path

        # Always route /kinfra and /__* to fallback server (dashboard/admin routes)
        if path.startswith(("/kinfra", "/__")):
            return await self._proxy_to_fallback(request)

        # Find appropriate upstream
        upstream = self._find_upstream(path)

        if not upstream:
            # No upstream configured, route to fallback
            logger.debug(f"No upstream found for {path}, routing to fallback")
            return await self._proxy_to_fallback(request)

        # Check if upstream is healthy
        if not upstream.is_healthy:
            logger.debug(f"Upstream {upstream.path_prefix} unhealthy, routing to fallback")
            return await self._proxy_to_fallback(request)

        # Proxy to healthy upstream
        try:
            return await self._proxy_to_upstream(request, upstream)
        except Exception as e:
            logger.warning(f"Failed to proxy to upstream: {e}, falling back")
            # Mark upstream as unhealthy
            upstream.is_healthy = False
            return await self._proxy_to_fallback(request)

    async def _proxy_to_upstream(
        self, request: "web.Request", upstream: UpstreamConfig,
    ) -> "web.Response":
        """
        Proxy request to upstream service.
        """
        # Build upstream URL
        upstream_url = f"http://{upstream.host}:{upstream.port}{request.path_qs}"

        # Forward request
        try:
            async with self.session.request(
                method=request.method,
                url=upstream_url,
                headers=request.headers,
                data=await request.read() if request.can_read_body else None,
                allow_redirects=False,
            ) as upstream_response:
                # Build response
                headers = dict(upstream_response.headers)
                # Remove hop-by-hop headers
                for header in ["Connection", "Keep-Alive", "Transfer-Encoding"]:
                    headers.pop(header, None)

                body = await upstream_response.read()

                return web.Response(body=body, status=upstream_response.status, headers=headers)

        except Exception as e:
            logger.exception(f"Upstream request failed: {e}")
            raise

    async def _proxy_to_fallback(self, request: "web.Request") -> "web.Response":
        """
        Proxy request to fallback server.
        """
        fallback_url = f"http://{self.fallback_host}:{self.fallback_port}{request.path_qs}"

        try:
            async with self.session.request(
                method=request.method,
                url=fallback_url,
                headers=request.headers,
                data=await request.read() if request.can_read_body else None,
                allow_redirects=False,
            ) as fallback_response:
                headers = dict(fallback_response.headers)
                # Remove hop-by-hop headers
                for header in ["Connection", "Keep-Alive", "Transfer-Encoding"]:
                    headers.pop(header, None)

                body = await fallback_response.read()

                return web.Response(body=body, status=fallback_response.status, headers=headers)

        except Exception as e:
            # If fallback also fails, return inline error
            logger.exception(f"Fallback request failed: {e}")
            return web.Response(text=self._get_inline_error(), content_type="text/html", status=503)

    def _get_inline_error(self) -> str:
        """
        Get minimal inline error page.
        """
        return """<!DOCTYPE html>
<html>
<head><title>Service Unavailable</title></head>
<body style="font-family: sans-serif; text-align: center; padding: 50px;">
    <h1>503 Service Unavailable</h1>
    <p>The service is temporarily unavailable. Please try again in a few moments.</p>
</body>
</html>"""


# Convenience function for standalone usage
async def run_smart_proxy(
    proxy_port: int = 9100, fallback_port: int = 9000, upstreams: dict[str, int] | None = None,
):
    """Run smart proxy server standalone.

    Args:
        proxy_port: Port for the proxy
        fallback_port: Port for the fallback server
        upstreams: Dict of path_prefix -> port mappings

    Example:
        >>> await run_smart_proxy(
        ...     proxy_port=9100,
        ...     fallback_port=9000,
        ...     upstreams={"/api": 8000, "/": 8001}
        ... )
    """
    proxy = SmartProxyServer(proxy_port=proxy_port, fallback_port=fallback_port)

    # Add upstreams
    if upstreams:
        for path_prefix, port in upstreams.items():
            proxy.add_upstream(path_prefix, port)

    await proxy.start()

    try:
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutting down proxy server...")
        await proxy.stop()
