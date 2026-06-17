"""CLI Monitoring Adapter.

Bridges existing CLI monitoring components with the unified monitoring layer. Provides
compatibility for CLI monitors, progress displays, and status indicators.
"""

from __future__ import annotations

import time
from typing import Any

from pheno.observability.logging import get_logger
from pheno.observability.monitoring.core import MonitoringProvider
from pheno.observability.monitoring.events import EventEmitter
from pheno.observability.monitoring.health import HealthStatus
from pheno.observability.monitoring.metrics import MetricsCollector

logger = get_logger(__name__)


class CLIMonitoringAdapter(MonitoringProvider):
    """Adapter for CLI monitoring components.

    Bridges existing CLI monitoring with the unified monitoring layer.
    """

    def __init__(
        self,
        progress_displays: list[Any] | None = None,
        status_indicators: list[Any] | None = None,
        cli_components: list[Any] | None = None,
    ):
        """Initialize CLI monitoring adapter.

        Args:
            progress_displays: List of progress display components
            status_indicators: List of status indicator components
            cli_components: List of other CLI components
        """
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

        # CLI components
        self.progress_displays = progress_displays or []
        self.status_indicators = status_indicators or []
        self.cli_components = cli_components or []

        # Adapter state
        self._started = False
        self._metrics_collector = MetricsCollector()
        self._event_emitter = EventEmitter()

        # Health tracking
        self._last_health_check = time.time()
        self._health_status = HealthStatus.HEALTHY

    async def start(self) -> None:
        """
        Start the CLI monitoring adapter.
        """
        if self._started:
            self.logger.warning("CLI monitoring adapter already started")
            return

        self.logger.info("Starting CLI monitoring adapter")

        try:
            # Start progress displays
            for display in self.progress_displays:
                if hasattr(display, "start"):
                    await display.start()
                    self.logger.debug(f"Started progress display: {display.__class__.__name__}")

            # Start status indicators
            for indicator in self.status_indicators:
                if hasattr(indicator, "start"):
                    await indicator.start()
                    self.logger.debug(f"Started status indicator: {indicator.__class__.__name__}")

            # Start CLI components
            for component in self.cli_components:
                if hasattr(component, "start"):
                    await component.start()
                    self.logger.debug(f"Started CLI component: {component.__class__.__name__}")

            # Start metrics collection
            await self._metrics_collector.start()

            # Start event emission
            await self._event_emitter.start()

            self._started = True
            self.logger.info("CLI monitoring adapter started successfully")

        except Exception as e:
            self.logger.exception(f"Failed to start CLI monitoring adapter: {e}")
            await self.stop()
            raise

    async def stop(self) -> None:
        """
        Stop the CLI monitoring adapter.
        """
        if not self._started:
            return

        self.logger.info("Stopping CLI monitoring adapter")

        try:
            # Stop progress displays
            for display in self.progress_displays:
                if hasattr(display, "stop"):
                    await display.stop()
                    self.logger.debug(f"Stopped progress display: {display.__class__.__name__}")

            # Stop status indicators
            for indicator in self.status_indicators:
                if hasattr(indicator, "stop"):
                    await indicator.stop()
                    self.logger.debug(f"Stopped status indicator: {indicator.__class__.__name__}")

            # Stop CLI components
            for component in self.cli_components:
                if hasattr(component, "stop"):
                    await component.stop()
                    self.logger.debug(f"Stopped CLI component: {component.__class__.__name__}")

            # Stop metrics collection
            await self._metrics_collector.stop()

            # Stop event emission
            await self._event_emitter.stop()

            self._started = False
            self.logger.info("CLI monitoring adapter stopped")

        except Exception as e:
            self.logger.exception(f"Error stopping CLI monitoring adapter: {e}")

    async def collect_metrics(self) -> dict[str, Any]:
        """
        Collect metrics from CLI components.
        """
        metrics = {}

        try:
            # Collect progress display metrics
            for i, display in enumerate(self.progress_displays):
                if hasattr(display, "get_metrics"):
                    display_metrics = await display.get_metrics()
                    metrics[f"progress_display_{i}"] = display_metrics

            # Collect status indicator metrics
            for i, indicator in enumerate(self.status_indicators):
                if hasattr(indicator, "get_metrics"):
                    indicator_metrics = await indicator.get_metrics()
                    metrics[f"status_indicator_{i}"] = indicator_metrics

            # Collect CLI component metrics
            for i, component in enumerate(self.cli_components):
                if hasattr(component, "get_metrics"):
                    component_metrics = await component.get_metrics()
                    metrics[f"cli_component_{i}"] = component_metrics

            # Add adapter metrics
            metrics.update(
                {
                    "cli_adapter_started": self._started,
                    "cli_adapter_uptime": time.time() - self._last_health_check,
                    "progress_displays_count": len(self.progress_displays),
                    "status_indicators_count": len(self.status_indicators),
                    "cli_components_count": len(self.cli_components),
                },
            )

            # Record metrics
            self._metrics_collector.gauge(
                "cli_progress_displays_count", len(self.progress_displays),
            )
            self._metrics_collector.gauge(
                "cli_status_indicators_count", len(self.status_indicators),
            )
            self._metrics_collector.gauge("cli_components_count", len(self.cli_components))
            self._metrics_collector.gauge(
                "cli_adapter_uptime", time.time() - self._last_health_check,
            )

        except Exception as e:
            self.logger.exception(f"Error collecting CLI metrics: {e}")
            metrics["error"] = str(e)

        return metrics

    async def process_events(self) -> list[dict[str, Any]]:
        """
        Process events from CLI components.
        """
        events = []

        try:
            # Process progress display events
            for display in self.progress_displays:
                if hasattr(display, "get_events"):
                    display_events = await display.get_events()
                    events.extend(display_events)

            # Process status indicator events
            for indicator in self.status_indicators:
                if hasattr(indicator, "get_events"):
                    indicator_events = await indicator.get_events()
                    events.extend(indicator_events)

            # Process CLI component events
            for component in self.cli_components:
                if hasattr(component, "get_events"):
                    component_events = await component.get_events()
                    events.extend(component_events)

            # Emit adapter events
            if self._started:
                self._event_emitter.emit(
                    "cli_adapter_status",
                    {
                        "status": "running",
                        "progress_displays": len(self.progress_displays),
                        "status_indicators": len(self.status_indicators),
                        "cli_components": len(self.cli_components),
                    },
                    source="cli_adapter",
                    severity="info",
                )

        except Exception as e:
            self.logger.exception(f"Error processing CLI events: {e}")
            events.append(
                {
                    "type": "error",
                    "source": "cli_adapter",
                    "message": str(e),
                    "timestamp": time.time(),
                },
            )

        return events

    async def health_check(self) -> dict[str, Any]:
        """
        Perform health check on CLI components.
        """
        health = {
            "healthy": True,
            "adapter_started": self._started,
            "components": {},
            "timestamp": time.time(),
        }

        try:
            # Check progress displays
            for i, display in enumerate(self.progress_displays):
                display_name = f"progress_display_{i}_{display.__class__.__name__}"
                if hasattr(display, "health_check"):
                    display_health = await display.health_check()
                    health["components"][display_name] = display_health
                    if not display_health.get("healthy", True):
                        health["healthy"] = False
                else:
                    health["components"][display_name] = {
                        "healthy": True,
                        "status": "no_health_check",
                    }

            # Check status indicators
            for i, indicator in enumerate(self.status_indicators):
                indicator_name = f"status_indicator_{i}_{indicator.__class__.__name__}"
                if hasattr(indicator, "health_check"):
                    indicator_health = await indicator.health_check()
                    health["components"][indicator_name] = indicator_health
                    if not indicator_health.get("healthy", True):
                        health["healthy"] = False
                else:
                    health["components"][indicator_name] = {
                        "healthy": True,
                        "status": "no_health_check",
                    }

            # Check CLI components
            for i, component in enumerate(self.cli_components):
                component_name = f"cli_component_{i}_{component.__class__.__name__}"
                if hasattr(component, "health_check"):
                    component_health = await component.health_check()
                    health["components"][component_name] = component_health
                    if not component_health.get("healthy", True):
                        health["healthy"] = False
                else:
                    health["components"][component_name] = {
                        "healthy": True,
                        "status": "no_health_check",
                    }

            # Update health status
            self._health_status = (
                HealthStatus.HEALTHY if health["healthy"] else HealthStatus.UNHEALTHY
            )
            self._last_health_check = time.time()

        except Exception as e:
            self.logger.exception(f"Error in CLI health check: {e}")
            health["healthy"] = False
            health["error"] = str(e)
            self._health_status = HealthStatus.UNHEALTHY

        return health

    def get_metrics_collector(self) -> MetricsCollector:
        """
        Get the metrics collector.
        """
        return self._metrics_collector

    def get_event_emitter(self) -> EventEmitter:
        """
        Get the event emitter.
        """
        return self._event_emitter

    def add_progress_display(self, display: Any) -> None:
        """
        Add a progress display component.
        """
        if display not in self.progress_displays:
            self.progress_displays.append(display)
            self.logger.info(f"Added progress display: {display.__class__.__name__}")

    def add_status_indicator(self, indicator: Any) -> None:
        """
        Add a status indicator component.
        """
        if indicator not in self.status_indicators:
            self.status_indicators.append(indicator)
            self.logger.info(f"Added status indicator: {indicator.__class__.__name__}")

    def add_cli_component(self, component: Any) -> None:
        """
        Add a CLI component.
        """
        if component not in self.cli_components:
            self.cli_components.append(component)
            self.logger.info(f"Added CLI component: {component.__class__.__name__}")

    def remove_progress_display(self, display: Any) -> None:
        """
        Remove a progress display component.
        """
        if display in self.progress_displays:
            self.progress_displays.remove(display)
            self.logger.info(f"Removed progress display: {display.__class__.__name__}")

    def remove_status_indicator(self, indicator: Any) -> None:
        """
        Remove a status indicator component.
        """
        if indicator in self.status_indicators:
            self.status_indicators.remove(indicator)
            self.logger.info(f"Removed status indicator: {indicator.__class__.__name__}")

    def remove_cli_component(self, component: Any) -> None:
        """
        Remove a CLI component.
        """
        if component in self.cli_components:
            self.cli_components.remove(component)
            self.logger.info(f"Removed CLI component: {component.__class__.__name__}")

    async def update_progress(self, progress: float, message: str = "") -> None:
        """
        Update progress across all progress displays.
        """
        for display in self.progress_displays:
            if hasattr(display, "update_progress"):
                await display.update_progress(progress, message)

    async def update_status(self, status: str, message: str = "") -> None:
        """
        Update status across all status indicators.
        """
        for indicator in self.status_indicators:
            if hasattr(indicator, "update_status"):
                await indicator.update_status(status, message)
