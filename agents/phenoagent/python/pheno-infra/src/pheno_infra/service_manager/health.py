"""
Health checks and tunnel readiness utilities.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime

from pheno.infra.utils.health import check_http_health

logger = logging.getLogger(__name__)


class HealthMixin:
    async def _await_tunnel_ready(
        self, hostname: str, health_endpoint: str = "/healthz", timeout: int = 45,
    ) -> bool:
        import urllib.error
        import urllib.request

        url = f"https://{hostname}{health_endpoint}"
        start = time.time()
        attempts = 0

        tunnel_mgr = getattr(self, "tunnel_manager", None)

        def _tunnel_log(
            message: str, *args, level: int = logging.INFO, verbose: bool = False,
        ) -> None:
            if tunnel_mgr and hasattr(tunnel_mgr, "_log_tunnel"):
                tunnel_mgr._log_tunnel(message, *args, level=level, verbose=verbose)
            elif verbose:
                logger.debug(message, *args)
            else:
                logger.log(level, message, *args)

        _tunnel_log(
            "Waiting for tunnel readiness: %s (timeout: %ss)", hostname, timeout, verbose=True,
        )
        while time.time() - start < timeout:
            attempts += 1
            try:
                request = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(request, timeout=5) as response:
                    if response.status == 200:
                        elapsed = time.time() - start
                        _tunnel_log(
                            "\u2713 Tunnel ready: %s (%.1fs, %d attempts)",
                            hostname,
                            elapsed,
                            attempts,
                            verbose=True,
                        )
                        return True
            except urllib.error.HTTPError as e:
                if e.code in (401, 403, 404):
                    elapsed = time.time() - start
                    _tunnel_log(
                        "\u2713 Tunnel connected: %s (HTTP %d after %.1fs)",
                        hostname,
                        e.code,
                        elapsed,
                        verbose=True,
                    )
                    return True
            except (urllib.error.URLError, ConnectionError, OSError):
                if attempts == 1:
                    _tunnel_log(
                        "Tunnel not yet ready (attempt %d)",
                        attempts,
                        level=logging.DEBUG,
                        verbose=True,
                    )
            except asyncio.CancelledError:  # propagate cancels
                _tunnel_log("Tunnel readiness check cancelled", level=logging.INFO, verbose=True)
                raise
            await asyncio.sleep(2)
        logger.warning("Tunnel not ready after %ss: %s", timeout, hostname)
        return False

    async def _check_service_health(self, name: str) -> bool:
        config = self.services.get(name)  # type: ignore[attr-defined]
        status = self.service_status[name]  # type: ignore[attr-defined]
        if not getattr(config, "health_check_url", None):
            return True
        loop = asyncio.get_event_loop()
        url = config.health_check_url.format(port=status.port)
        localhost_healthy = await loop.run_in_executor(
            None, check_http_health, url, 2.0, 200, "GET",
        )
        tunnel_healthy = False
        if status.tunnel_url:
            tunnel_url = f"{status.tunnel_url}/health"
            tunnel_healthy = await loop.run_in_executor(
                None, check_http_health, tunnel_url, 5.0, 200, "GET",
            )
        status.last_health_check = datetime.now()
        if localhost_healthy:
            status.health_status = (
                "healthy" if (tunnel_healthy or not status.tunnel_url) else "degraded"
            )
        else:
            status.health_status = "unhealthy"
        return localhost_healthy
