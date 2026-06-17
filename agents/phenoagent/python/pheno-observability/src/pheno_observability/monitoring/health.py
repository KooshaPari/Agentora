"""Health Checking System.

Unified health checking system that consolidates functionality from infra/monitoring,
MCP QA, and observability stacks.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol
from uuid import uuid4

from ..logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

logger = get_logger(__name__)


class HealthStatus(Enum):
    """
    Health status enumeration.
    """

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """
    A health check definition.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    check_function: Callable[[], Any] | None = None
    timeout: float = 5.0
    interval: float = 30.0
    enabled: bool = True
    critical: bool = False  # If critical, overall health depends on this check


@dataclass
class HealthResult:
    """
    Result of a health check.
    """

    check_id: str
    name: str
    status: HealthStatus
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    duration: float = 0.0
    timestamp: float = field(default_factory=time.time)
    error: str | None = None


class HealthProvider(Protocol):
    """
    Protocol for health check providers.
    """

    async def health_check(self) -> HealthResult:
        """
        Perform health check.
        """
        ...


class HealthChecker:
    """Manages and executes health checks.

    Consolidates health checking from infra/monitoring, MCP QA, and observability stacks
    into a unified interface.
    """

    def __init__(self, default_timeout: float = 5.0):
        """Initialize health checker.

        Args:
            default_timeout: Default timeout for health checks
        """
        self.default_timeout = default_timeout
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

        # Health checks
        self._checks: dict[str, HealthCheck] = {}
        self._providers: dict[str, HealthProvider] = {}

        # State
        self._running = False
        self._check_tasks: list[asyncio.Task] = []
        self._last_results: dict[str, HealthResult] = {}

    async def start(self) -> None:
        """
        Start health checker.
        """
        if self._running:
            self.logger.warning("Health checker already started")
            return

        self._running = True

        # Start periodic health checks
        for check in self._checks.values():
            if check.enabled and check.interval > 0:
                task = asyncio.create_task(self._periodic_check(check))
                self._check_tasks.append(task)

        self.logger.info("Started health checker")

    async def stop(self) -> None:
        """
        Stop health checker.
        """
        if not self._running:
            return

        # Cancel check tasks
        for task in self._check_tasks:
            task.cancel()

        if self._check_tasks:
            await asyncio.gather(*self._check_tasks, return_exceptions=True)

        self._running = False
        self.logger.info("Stopped health checker")

    async def _periodic_check(self, check: HealthCheck) -> None:
        """
        Run a health check periodically.
        """
        while self._running and check.enabled:
            try:
                result = await self._run_check(check)
                self._last_results[check.id] = result

                # Log status changes
                if result.status == HealthStatus.UNHEALTHY:
                    self.logger.error(f"Health check failed: {check.name} - {result.message}")
                elif result.status == HealthStatus.DEGRADED:
                    self.logger.warning(f"Health check degraded: {check.name} - {result.message}")

                await asyncio.sleep(check.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.exception(f"Error in periodic check {check.name}: {e}")
                await asyncio.sleep(1.0)

    async def _run_check(self, check: HealthCheck) -> HealthResult:
        """
        Run a single health check.
        """
        start_time = time.time()

        try:
            if check.check_function:
                # Run custom check function
                result = await asyncio.wait_for(
                    self._run_check_function(check.check_function), timeout=check.timeout,
                )
            else:
                # Default healthy result
                result = HealthStatus.HEALTHY
                message = "Check passed"
                details = {}

            duration = time.time() - start_time

            return HealthResult(
                check_id=check.id,
                name=check.name,
                status=result if isinstance(result, HealthStatus) else HealthStatus.HEALTHY,
                message=message if "message" in locals() else "Check passed",
                details=details if "details" in locals() else {},
                duration=duration,
            )

        except TimeoutError:
            duration = time.time() - start_time
            return HealthResult(
                check_id=check.id,
                name=check.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check timed out after {check.timeout}s",
                duration=duration,
                error="timeout",
            )
        except Exception as e:
            duration = time.time() - start_time
            return HealthResult(
                check_id=check.id,
                name=check.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed: {e!s}",
                duration=duration,
                error=str(e),
            )

    async def _run_check_function(self, check_function: Callable[[], Any]) -> Any:
        """
        Run a check function, handling both sync and async functions.
        """
        if asyncio.iscoroutinefunction(check_function):
            return await check_function()
        return check_function()

    def add_check(
        self,
        name: str,
        check_function: Callable[[], Any] | None = None,
        description: str = "",
        timeout: float | None = None,
        interval: float = 30.0,
        enabled: bool = True,
        critical: bool = False,
    ) -> str:
        """Add a health check.

        Args:
            name: Check name
            check_function: Function to run for the check
            description: Check description
            timeout: Check timeout
            interval: Check interval (0 to disable periodic checks)
            enabled: Whether the check is enabled
            critical: Whether the check is critical

        Returns:
            Check ID
        """
        check = HealthCheck(
            name=name,
            description=description,
            check_function=check_function,
            timeout=timeout or self.default_timeout,
            interval=interval,
            enabled=enabled,
            critical=critical,
        )

        self._checks[check.id] = check
        self.logger.info(f"Added health check: {name}")

        # Start periodic check if manager is running
        if self._running and check.enabled and check.interval > 0:
            task = asyncio.create_task(self._periodic_check(check))
            self._check_tasks.append(task)

        return check.id

    def remove_check(self, check_id: str) -> bool:
        """
        Remove a health check.
        """
        if check_id in self._checks:
            check = self._checks[check_id]
            del self._checks[check_id]
            self._last_results.pop(check_id, None)
            self.logger.info(f"Removed health check: {check.name}")
            return True
        return False

    def enable_check(self, check_id: str) -> bool:
        """
        Enable a health check.
        """
        if check_id in self._checks:
            self._checks[check_id].enabled = True
            self.logger.info(f"Enabled health check: {self._checks[check_id].name}")
            return True
        return False

    def disable_check(self, check_id: str) -> bool:
        """
        Disable a health check.
        """
        if check_id in self._checks:
            self._checks[check_id].enabled = False
            self.logger.info(f"Disabled health check: {self._checks[check_id].name}")
            return True
        return False

    def register_provider(self, name: str, provider: HealthProvider) -> None:
        """
        Register a health check provider.
        """
        self._providers[name] = provider
        self.logger.info(f"Registered health provider: {name}")

    def unregister_provider(self, name: str) -> None:
        """
        Unregister a health check provider.
        """
        if name in self._providers:
            del self._providers[name]
            self.logger.info(f"Unregistered health provider: {name}")

    async def run_check(self, check_id: str) -> HealthResult | None:
        """
        Run a specific health check.
        """
        check = self._checks.get(check_id)
        if not check:
            return None

        result = await self._run_check(check)
        self._last_results[check_id] = result
        return result

    async def run_all_checks(self) -> list[HealthResult]:
        """
        Run all enabled health checks.
        """
        results = []

        for check in self._checks.values():
            if check.enabled:
                result = await self._run_check(check)
                self._last_results[check.id] = result
                results.append(result)

        return results

    def get_check_result(self, check_id: str) -> HealthResult | None:
        """
        Get the last result for a health check.
        """
        return self._last_results.get(check_id)

    def get_all_results(self) -> dict[str, HealthResult]:
        """
        Get all last results.
        """
        return self._last_results.copy()

    def get_overall_health(self) -> HealthStatus:
        """
        Get overall health status.
        """
        if not self._last_results:
            return HealthStatus.UNKNOWN

        # Check critical checks first
        critical_checks = [
            check for check in self._checks.values() if check.critical and check.enabled
        ]
        for check in critical_checks:
            result = self._last_results.get(check.id)
            if not result or result.status == HealthStatus.UNHEALTHY:
                return HealthStatus.UNHEALTHY

        # Check all enabled checks
        enabled_results = [
            result
            for check_id, result in self._last_results.items()
            if self._checks.get(check_id, HealthCheck()).enabled
        ]

        if not enabled_results:
            return HealthStatus.UNKNOWN

        # Determine overall status
        unhealthy_count = sum(1 for r in enabled_results if r.status == HealthStatus.UNHEALTHY)
        degraded_count = sum(1 for r in enabled_results if r.status == HealthStatus.DEGRADED)

        if unhealthy_count > 0:
            return HealthStatus.UNHEALTHY
        if degraded_count > 0:
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY

    async def health_check(self) -> dict[str, Any]:
        """
        Perform overall health check.
        """
        overall_status = self.get_overall_health()

        health = {
            "healthy": overall_status == HealthStatus.HEALTHY,
            "status": overall_status.value,
            "running": self._running,
            "checks": len(self._checks),
            "enabled_checks": len([c for c in self._checks.values() if c.enabled]),
            "providers": len(self._providers),
            "results": {},
        }

        # Add individual check results
        for check_id, result in self._last_results.items():
            check = self._checks.get(check_id)
            if check:
                health["results"][check.name] = {
                    "status": result.status.value,
                    "message": result.message,
                    "duration": result.duration,
                    "timestamp": result.timestamp,
                    "critical": check.critical,
                    "enabled": check.enabled,
                }

        return health
