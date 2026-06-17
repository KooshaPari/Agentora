"""Infrastructure Monitoring Adapter.

Bridges existing infra/monitoring components with the unified monitoring layer. Provides
compatibility for ServiceMonitor, ProcessPanel, ResourcePanel, etc.
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


class InfraMonitoringAdapter(MonitoringProvider):
    """Adapter for infrastructure monitoring components.

    Bridges existing infra/monitoring components with the unified monitoring layer.
    """

    def __init__(
        self,
        service_monitor: Any | None = None,
        process_panels: list[Any] | None = None,
        resource_panels: list[Any] | None = None,
        endpoint_panels: list[Any] | None = None,
    ):
        """Initialize infrastructure monitoring adapter.

        Args:
            service_monitor: ServiceMonitor instance
            process_panels: List of ProcessPanel instances
            resource_panels: List of ResourcePanel instances
            endpoint_panels: List of EndpointPanel instances
        """
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

        # Infrastructure components
        self.service_monitor = service_monitor
        self.process_panels = process_panels or []
        self.resource_panels = resource_panels or []
        self.endpoint_panels = endpoint_panels or []

        # Adapter state
        self._started = False
        self._metrics_collector = MetricsCollector()
        self._event_emitter = EventEmitter()

        # Health tracking
        self._last_health_check = time.time()
        self._health_status = HealthStatus.HEALTHY

    async def start(self) -> None:
        """
        Start the infrastructure monitoring adapter.
        """
        if self._started:
            self.logger.warning("Infra monitoring adapter already started")
            return

        self.logger.info("Starting infrastructure monitoring adapter")

        try:
            # Start service monitor if available
            if self.service_monitor and hasattr(self.service_monitor, "start"):
                await self.service_monitor.start()
                self.logger.info("Started service monitor")

            # Start panels
            for panel in self.process_panels + self.resource_panels + self.endpoint_panels:
                if hasattr(panel, "start"):
                    await panel.start()
                    self.logger.debug(f"Started panel: {panel.__class__.__name__}")

            # Start metrics collection
            await self._metrics_collector.start()

            # Start event emission
            await self._event_emitter.start()

            self._started = True
            self.logger.info("Infrastructure monitoring adapter started successfully")

        except Exception as e:
            self.logger.exception(f"Failed to start infrastructure monitoring adapter: {e}")
            await self.stop()
            raise

    async def stop(self) -> None:
        """
        Stop the infrastructure monitoring adapter.
        """
        if not self._started:
            return

        self.logger.info("Stopping infrastructure monitoring adapter")

        try:
            # Stop service monitor
            if self.service_monitor and hasattr(self.service_monitor, "stop"):
                await self.service_monitor.stop()
                self.logger.info("Stopped service monitor")

            # Stop panels
            for panel in self.process_panels + self.resource_panels + self.endpoint_panels:
                if hasattr(panel, "stop"):
                    await panel.stop()
                    self.logger.debug(f"Stopped panel: {panel.__class__.__name__}")

            # Stop metrics collection
            await self._metrics_collector.stop()

            # Stop event emission
            await self._event_emitter.stop()

            self._started = False
            self.logger.info("Infrastructure monitoring adapter stopped")

        except Exception as e:
            self.logger.exception(f"Error stopping infrastructure monitoring adapter: {e}")

    async def collect_metrics(self) -> dict[str, Any]:
        """
        Collect metrics from infrastructure components.
        """
        metrics = {}

        try:
            # Collect service monitor metrics
            if self.service_monitor and hasattr(self.service_monitor, "get_metrics"):
                service_metrics = await self.service_monitor.get_metrics()
                metrics.update(service_metrics)

            # Collect panel metrics
            for panel in self.process_panels + self.resource_panels + self.endpoint_panels:
                if hasattr(panel, "get_metrics"):
                    panel_metrics = await panel.get_metrics()
                    metrics.update(panel_metrics)

            # Add adapter metrics
            metrics.update(
                {
                    "infra_adapter_started": self._started,
                    "infra_adapter_uptime": time.time() - self._last_health_check,
                    "panels_count": len(
                        self.process_panels + self.resource_panels + self.endpoint_panels,
                    ),
                },
            )

            # Record metrics
            self._metrics_collector.gauge(
                "infra_panels_count",
                len(self.process_panels + self.resource_panels + self.endpoint_panels),
            )
            self._metrics_collector.gauge(
                "infra_adapter_uptime", time.time() - self._last_health_check,
            )

        except Exception as e:
            self.logger.exception(f"Error collecting infrastructure metrics: {e}")
            metrics["error"] = str(e)

        return metrics

    async def process_events(self) -> list[dict[str, Any]]:
        """
        Process events from infrastructure components.
        """
        events = []

        try:
            # Process service monitor events
            if self.service_monitor and hasattr(self.service_monitor, "get_events"):
                service_events = await self.service_monitor.get_events()
                events.extend(service_events)

            # Process panel events
            for panel in self.process_panels + self.resource_panels + self.endpoint_panels:
                if hasattr(panel, "get_events"):
                    panel_events = await panel.get_events()
                    events.extend(panel_events)

            # Emit adapter events
            if self._started:
                self._event_emitter.emit(
                    "infra_adapter_status",
                    {
                        "status": "running",
                        "panels": len(
                            self.process_panels + self.resource_panels + self.endpoint_panels,
                        ),
                    },
                    source="infra_adapter",
                    severity="info",
                )

        except Exception as e:
            self.logger.exception(f"Error processing infrastructure events: {e}")
            events.append(
                {
                    "type": "error",
                    "source": "infra_adapter",
                    "message": str(e),
                    "timestamp": time.time(),
                },
            )

        return events

    async def health_check(self) -> dict[str, Any]:
        """
        Perform health check on infrastructure components.
        """
        health = {
            "healthy": True,
            "adapter_started": self._started,
            "components": {},
            "timestamp": time.time(),
        }

        try:
            # Check service monitor health
            if self.service_monitor:
                if hasattr(self.service_monitor, "health_check"):
                    service_health = await self.service_monitor.health_check()
                    health["components"]["service_monitor"] = service_health
                    if not service_health.get("healthy", True):
                        health["healthy"] = False
                else:
                    health["components"]["service_monitor"] = {
                        "healthy": True,
                        "status": "no_health_check",
                    }

            # Check panel health
            for i, panel in enumerate(
                self.process_panels + self.resource_panels + self.endpoint_panels,
            ):
                panel_name = f"panel_{i}_{panel.__class__.__name__}"
                if hasattr(panel, "health_check"):
                    panel_health = await panel.health_check()
                    health["components"][panel_name] = panel_health
                    if not panel_health.get("healthy", True):
                        health["healthy"] = False
                else:
                    health["components"][panel_name] = {
                        "healthy": True,
                        "status": "no_health_check",
                    }

            # Update health status
            self._health_status = (
                HealthStatus.HEALTHY if health["healthy"] else HealthStatus.UNHEALTHY
            )
            self._last_health_check = time.time()

        except Exception as e:
            self.logger.exception(f"Error in infrastructure health check: {e}")
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

    def add_panel(self, panel: Any) -> None:
        """
        Add a monitoring panel.
        """
        if panel not in (self.process_panels + self.resource_panels + self.endpoint_panels):
            if hasattr(panel, "panel_type"):
                if panel.panel_type == "process":
                    self.process_panels.append(panel)
                elif panel.panel_type == "resource":
                    self.resource_panels.append(panel)
                elif panel.panel_type == "endpoint":
                    self.endpoint_panels.append(panel)
                else:
                    self.process_panels.append(panel)  # Default
            else:
                self.process_panels.append(panel)  # Default

            self.logger.info(f"Added panel: {panel.__class__.__name__}")

    def remove_panel(self, panel: Any) -> None:
        """
        Remove a monitoring panel.
        """
        for panel_list in [self.process_panels, self.resource_panels, self.endpoint_panels]:
            if panel in panel_list:
                panel_list.remove(panel)
                self.logger.info(f"Removed panel: {panel.__class__.__name__}")
                break
