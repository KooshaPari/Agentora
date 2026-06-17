"""Core Monitoring Manager.

Unified monitoring manager that coordinates metrics, events, dashboards, and health
checks. Consolidates functionality from infra/monitoring, MCP QA, and observability
stacks.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Protocol

from ..logging import get_logger

logger = get_logger(__name__)


@dataclass
class MonitoringConfig:
    """
    Configuration for monitoring components.
    """

    # General settings
    service_name: str = "pheno-service"
    environment: str = "development"
    enable_metrics: bool = True
    enable_events: bool = True
    enable_dashboards: bool = True
    enable_health_checks: bool = True

    # Metrics settings
    metrics_port: int = 8000
    metrics_path: str = "/metrics"
    metrics_interval: float = 30.0

    # Events settings
    event_buffer_size: int = 1000
    event_flush_interval: float = 5.0

    # Dashboard settings
    dashboard_port: int = 8080
    dashboard_path: str = "/dashboard"
    refresh_interval: float = 1.0

    # Health check settings
    health_check_interval: float = 10.0
    health_timeout: float = 5.0

    # Logging
    log_level: str = "INFO"
    structured_logging: bool = True


class MonitoringProvider(Protocol):
    """
    Protocol for monitoring providers.
    """

    async def start(self) -> None:
        """
        Start the monitoring provider.
        """
        ...

    async def stop(self) -> None:
        """
        Stop the monitoring provider.
        """
        ...

    async def health_check(self) -> dict[str, Any]:
        """
        Perform health check.
        """
        ...


class MonitoringManager:
    """Unified monitoring manager.

    Coordinates all monitoring components including metrics, events, dashboards, and
    health checks. Provides a single interface for monitoring across the platform.
    """

    def __init__(
        self,
        config: MonitoringConfig,
        providers: list[MonitoringProvider] | None = None,
    ):
        """Initialize monitoring manager.

        Args:
            config: Monitoring configuration
            providers: Optional list of monitoring providers
        """
        self.config = config
        self.providers = providers or []
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

        # State tracking
        self._started = False
        self._tasks: list[asyncio.Task] = []
        self._metrics: dict[str, Any] = {}
        self._events: list[dict[str, Any]] = []

        # Initialize components
        self._setup_logging()

    def _setup_logging(self) -> None:
        """
        Setup logging configuration.
        """
        if self.config.structured_logging:
            self.logger.info(
                "Monitoring manager initialized",
                extra={
                    "service": self.config.service_name,
                    "environment": self.config.environment,
                    "metrics_enabled": self.config.enable_metrics,
                    "events_enabled": self.config.enable_events,
                    "dashboards_enabled": self.config.enable_dashboards,
                },
            )
        else:
            self.logger.info(
                f"Monitoring manager initialized for {self.config.service_name} "
                f"in {self.config.environment}",
            )

    async def start(self) -> None:
        """
        Start all monitoring components.
        """
        if self._started:
            self.logger.warning("Monitoring manager already started")
            return

        self.logger.info("Starting monitoring manager")

        try:
            await self._start_providers()
            await self._start_background_tasks()
            self._started = True
            self.logger.info("Monitoring manager started successfully")

        except Exception as e:
            self.logger.exception(f"Failed to start monitoring manager: {e}")
            await self.stop()
            raise

    async def _start_providers(self) -> None:
        """
        Start all monitoring providers.
        """
        for provider in self.providers:
            await provider.start()
            self.logger.debug(f"Started provider: {provider.__class__.__name__}")

    async def _start_background_tasks(self) -> None:
        """
        Start background monitoring tasks.
        """
        if self.config.enable_metrics:
            task = asyncio.create_task(self._metrics_loop())
            self._tasks.append(task)

        if self.config.enable_events:
            task = asyncio.create_task(self._events_loop())
            self._tasks.append(task)

        if self.config.enable_health_checks:
            task = asyncio.create_task(self._health_check_loop())
            self._tasks.append(task)

    async def stop(self) -> None:
        """
        Stop all monitoring components.
        """
        if not self._started:
            return

        self.logger.info("Stopping monitoring manager")

        # Cancel background tasks
        for task in self._tasks:
            task.cancel()

        # Wait for tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        # Stop providers
        for provider in self.providers:
            try:
                await provider.stop()
                self.logger.debug(f"Stopped provider: {provider.__class__.__name__}")
            except Exception as e:
                self.logger.exception(f"Error stopping provider {provider.__class__.__name__}: {e}")

        self._started = False
        self.logger.info("Monitoring manager stopped")

    async def _metrics_loop(self) -> None:
        """
        Background metrics collection loop.
        """
        while self._started:
            try:
                await self._collect_metrics()
                await asyncio.sleep(self.config.metrics_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.exception(f"Error in metrics loop: {e}")
                await asyncio.sleep(1.0)

    async def _events_loop(self) -> None:
        """
        Background events processing loop.
        """
        while self._started:
            try:
                await self._process_events()
                await asyncio.sleep(self.config.event_flush_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.exception(f"Error in events loop: {e}")
                await asyncio.sleep(1.0)

    async def _health_check_loop(self) -> None:
        """
        Background health check loop.
        """
        while self._started:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.config.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.exception(f"Error in health check loop: {e}")
                await asyncio.sleep(1.0)

    async def _collect_metrics(self) -> None:
        """
        Collect metrics from all providers.
        """
        for provider in self.providers:
            try:
                if hasattr(provider, "collect_metrics"):
                    metrics = await provider.collect_metrics()
                    self._metrics.update(metrics)
            except Exception as e:
                self.logger.exception(
                    f"Error collecting metrics from {provider.__class__.__name__}: {e}",
                )

    async def _process_events(self) -> None:
        """
        Process events from all providers.
        """
        for provider in self.providers:
            try:
                if hasattr(provider, "process_events"):
                    events = await provider.process_events()
                    self._events.extend(events)
            except Exception as e:
                self.logger.exception(
                    f"Error processing events from {provider.__class__.__name__}: {e}",
                )

    async def _perform_health_checks(self) -> None:
        """
        Perform health checks on all providers.
        """
        for provider in self.providers:
            try:
                health = await provider.health_check()
                if not health.get("healthy", False):
                    self.logger.warning(
                        f"Provider {provider.__class__.__name__} is unhealthy: {health}",
                    )
            except Exception as e:
                self.logger.exception(f"Health check failed for {provider.__class__.__name__}: {e}")

    def add_provider(self, provider: MonitoringProvider) -> None:
        """
        Add a monitoring provider.
        """
        self.providers.append(provider)
        self.logger.info(f"Added monitoring provider: {provider.__class__.__name__}")

    def remove_provider(self, provider: MonitoringProvider) -> None:
        """
        Remove a monitoring provider.
        """
        if provider in self.providers:
            self.providers.remove(provider)
            self.logger.info(f"Removed monitoring provider: {provider.__class__.__name__}")

    def get_metrics(self) -> dict[str, Any]:
        """
        Get current metrics.
        """
        return self._metrics.copy()

    def get_events(self) -> list[dict[str, Any]]:
        """
        Get current events.
        """
        return self._events.copy()

    def clear_events(self) -> None:
        """
        Clear events buffer.
        """
        self._events.clear()

    async def health_check(self) -> dict[str, Any]:
        """
        Perform overall health check.
        """
        health = {
            "healthy": True,
            "service": self.config.service_name,
            "environment": self.config.environment,
            "started": self._started,
            "providers": [],
            "timestamp": time.time(),
        }

        for provider in self.providers:
            try:
                provider_health = await provider.health_check()
                health["providers"].append(
                    {
                        "name": provider.__class__.__name__,
                        "healthy": provider_health.get("healthy", False),
                        "details": provider_health,
                    },
                )
                if not provider_health.get("healthy", False):
                    health["healthy"] = False
            except Exception as e:
                health["providers"].append(
                    {
                        "name": provider.__class__.__name__,
                        "healthy": False,
                        "error": str(e),
                    },
                )
                health["healthy"] = False

        return health
