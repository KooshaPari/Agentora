"""Background health monitoring for proxy upstreams."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any

from pheno.infra.utils.health import check_tcp_health

if TYPE_CHECKING:
    from collections.abc import Callable

    from .registry import UpstreamRegistry

logger = logging.getLogger(__name__)


class HealthMonitor:
    """
    Poll upstream health and notify fallback servers of status changes.
    """

    def __init__(
        self,
        registry: UpstreamRegistry,
        fallback_server: object | None = None,
        interval: float = 5.0,
        on_transition: Callable[[dict[str, Any], bool | None], None] | None = None,
    ):
        self._registry = registry
        self._fallback_server = fallback_server
        self._interval = interval
        self._shutdown = False
        self._task: asyncio.Task | None = None
        self._on_transition = on_transition

    def start(self) -> None:
        """
        Spawn the health monitoring coroutine.
        """
        if self._task:
            return
        self._task = asyncio.create_task(self._run())
        logger.info("Health monitoring started")

    async def stop(self) -> None:
        """
        Stop the monitor and wait for shutdown.
        """
        self._shutdown = True
        if not self._task:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            logger.info("Health monitoring stopped")
        finally:
            self._task = None

    async def _run(self) -> None:
        try:
            while not self._shutdown:
                await self._poll_upstreams()
                await asyncio.sleep(self._interval)
        except asyncio.CancelledError:
            logger.info("Health monitoring cancelled")

    async def _poll_upstreams(self) -> None:
        loop = asyncio.get_event_loop()
        for path_prefix, upstream in self._registry.iter_upstreams():
            healthy = await loop.run_in_executor(
                None,
                check_tcp_health,
                upstream.host,
                upstream.port,
                upstream.health_check_timeout,
            )
            transition = self._registry.update_health_state(
                path_prefix,
                healthy,
                checked_at=time.time(),
            )

            if not transition["changed"]:
                continue

            state = transition["state"]
            previous = transition["previous"]
            status = "healthy" if healthy else "unhealthy"
            logger.info("Upstream %s is now %s", path_prefix, status)

            if self._on_transition:
                try:
                    self._on_transition(state, previous)
                except Exception:  # pragma: no cover - defensive logging
                    logger.exception("Health transition callback failed")

            if not self._fallback_server:
                continue

            service_name = state.get("service") or path_prefix.strip("/") or "service"
            try:
                if healthy:
                    self._fallback_server.update_service_status(  # type: ignore[attr-defined]
                        service_name=service_name,
                        status_message="Service is ready",
                        health_status="Healthy",
                        state="running",
                    )
                else:
                    self._fallback_server.update_service_status(  # type: ignore[attr-defined]
                        service_name=service_name,
                        status_message="Service is unhealthy, attempting restart...",
                        health_status="Unhealthy",
                        state="error",
                    )
            except Exception:  # pragma: no cover - defensive logging
                logger.exception("Failed to report health status to fallback server")


__all__ = ["HealthMonitor"]
