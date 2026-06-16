"""
Health monitoring component.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .port_manager import PortManager

if TYPE_CHECKING:
    from ..base.health_check import HealthCheck


@dataclass
class HealthCheckResult:
    """
    Health check result.
    """

    name: str
    healthy: bool
    message: str
    response_time_ms: float | None = None


class HTTPHealthCheck:
    """
    HTTP endpoint health check.
    """

    def __init__(self, url: str, timeout: int = 5, interval: int = 10):
        """Initialize HTTP health check.

        Args:
            url: Health check URL
            timeout: Request timeout in seconds
            interval: Check interval in seconds
        """
        self.url = url
        self.timeout = timeout
        self.interval = interval

    async def check(self) -> bool:
        """Perform health check.

        Returns:
            True if healthy
        """
        try:
            import time

            import httpx

            start = time.time()
            async with httpx.AsyncClient() as client:
                response = await client.get(self.url, timeout=self.timeout)
                (time.time() - start) * 1000

                return 200 <= response.status_code < 300
        except Exception:
            return False

    def get_name(self) -> str:
        """
        Get health check name.
        """
        return f"HTTP:{self.url}"


class PortHealthCheck:
    """
    Port availability health check.
    """

    def __init__(self, port: int, interval: int = 5):
        """Initialize port health check.

        Args:
            port: Port number to check
            interval: Check interval in seconds
        """
        self.port = port
        self.interval = interval

    async def check(self) -> bool:
        """Check if port is occupied (healthy).

        Returns:
            True if port is in use
        """
        # Port being in use means service is running
        return not PortManager.is_port_available(self.port)

    def get_name(self) -> str:
        """
        Get health check name.
        """
        return f"Port:{self.port}"


class HealthMonitor:
    """
    Monitors health of multiple services.
    """

    def __init__(self):
        """
        Initialize health monitor.
        """
        self._checks: list[HealthCheck] = []
        self._results: dict[str, HealthCheckResult] = {}
        self._running = False

    def add_http_check(self, url: str, timeout: int = 5, interval: int = 10):
        """Add HTTP health check.

        Args:
            url: Health check URL
            timeout: Request timeout
            interval: Check interval
        """
        check = HTTPHealthCheck(url, timeout, interval)
        self._checks.append(check)

    def add_port_check(self, port: int, interval: int = 5):
        """Add port health check.

        Args:
            port: Port number
            interval: Check interval
        """
        check = PortHealthCheck(port, interval)
        self._checks.append(check)

    def add_custom_check(self, check: HealthCheck):
        """Add custom health check.

        Args:
            check: Health check implementation
        """
        self._checks.append(check)

    async def check_all(self) -> list[HealthCheckResult]:
        """Run all health checks.

        Returns:
            List of health check results
        """
        results = []

        for check in self._checks:
            import time

            start = time.time()

            try:
                healthy = await check.check()
                elapsed = (time.time() - start) * 1000

                result = HealthCheckResult(
                    name=check.get_name(),
                    healthy=healthy,
                    message="OK" if healthy else "FAILED",
                    response_time_ms=elapsed,
                )
            except Exception as e:
                result = HealthCheckResult(
                    name=check.get_name(), healthy=False, message=f"Error: {e}",
                )

            results.append(result)
            self._results[check.get_name()] = result

        return results

    async def start_monitoring(self):
        """
        Start continuous health monitoring.
        """
        self._running = True

        while self._running:
            await self.check_all()
            await asyncio.sleep(5)  # Check every 5 seconds

    def stop_monitoring(self):
        """
        Stop health monitoring.
        """
        self._running = False

    def get_status(self) -> dict[str, Any]:
        """Get current health status.

        Returns:
            Status dictionary
        """
        total = len(self._results)
        healthy = sum(1 for r in self._results.values() if r.healthy)

        return {
            "total_checks": total,
            "healthy": healthy,
            "unhealthy": total - healthy,
            "health_rate": healthy / total if total > 0 else 0.0,
            "checks": {name: r.healthy for name, r in self._results.items()},
        }
