"""
HTTP health probe utilities for networking startup flows.
"""

from __future__ import annotations

import asyncio
import time

import aiohttp

from ..utils.aiohttp_otel import apply_aiohttp_otel_kwargs
from .options import DefaultLogger, Logger


async def wait_for_health(
    base_url: str, timeout_seconds: int = 20, logger: Logger | None = None,
) -> bool:
    """Poll base_url/healthz until 200 OK or timeout.

    Returns True on success, False on timeout.
    """
    if logger is None:
        logger = DefaultLogger()

    health_url = base_url.rstrip("/") + "/healthz"
    logger.info(f"Health check starting for: {health_url}")

    start_time = time.time()
    delay = 0.5
    timeout = aiohttp.ClientTimeout(total=4.0)

    while time.time() - start_time < timeout_seconds:
        try:
            async with aiohttp.ClientSession(
                **apply_aiohttp_otel_kwargs({"timeout": timeout}),
            ) as session, session.get(health_url) as response:
                if response.status == 200:
                    logger.info(f"Health check passed: {health_url}")
                    return True
        except Exception:
            pass

        await asyncio.sleep(delay)
        delay = min(delay * 1.5, 2.0)

    logger.warn(f"Health check timed out: {health_url}")
    return False
