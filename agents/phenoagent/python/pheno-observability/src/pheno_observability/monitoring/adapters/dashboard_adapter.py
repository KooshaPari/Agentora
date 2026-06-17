"""Dashboard Adapter.

Bridges existing dashboard components with the unified monitoring layer. Provides
compatibility for various dashboard systems and UI components.
"""

from __future__ import annotations

import time
from typing import Any

from pheno.observability.logging import get_logger
from pheno.observability.monitoring.core import MonitoringProvider
from pheno.observability.monitoring.dashboards import (
    Dashboard,
    DashboardPanel,
    DashboardProvider,
)
from pheno.observability.monitoring.events import EventEmitter
from pheno.observability.monitoring.health import HealthStatus
from pheno.observability.monitoring.metrics import MetricsCollector

logger = get_logger(__name__)


class DashboardAdapter(MonitoringProvider, DashboardProvider):
    """Adapter for dashboard components.

    Bridges existing dashboard systems with the unified monitoring layer.
    """

    def __init__(
        self,
        dashboard_components: list[Any] | None = None,
        ui_components: list[Any] | None = None,
        tui_components: list[Any] | None = None,
    ):
        """Initialize dashboard adapter.

        Args:
            dashboard_components: List of dashboard components
            ui_components: List of UI components
            tui_components: List of TUI components
        """
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

        # Dashboard components
        self.dashboard_components = dashboard_components or []
        self.ui_components = ui_components or []
        self.tui_components = tui_components or []

        # Adapter state
        self._started = False
        self._metrics_collector = MetricsCollector()
        self._event_emitter = EventEmitter()

        # Dashboard state
        self._dashboards: dict[str, Dashboard] = {}
        self._panels: dict[str, DashboardPanel] = {}

        # Health tracking
        self._last_health_check = time.time()
        self._health_status = HealthStatus.HEALTHY

    async def start(self) -> None:
        """
        Start the dashboard adapter.
        """
        if self._started:
            self.logger.warning("Dashboard adapter already started")
            return

        self.logger.info("Starting dashboard adapter")

        try:
            # Start dashboard components
            for component in self.dashboard_components:
                if hasattr(component, "start"):
                    await component.start()
                    self.logger.debug(
                        f"Started dashboard component: {component.__class__.__name__}",
                    )

            # Start UI components
            for component in self.ui_components:
                if hasattr(component, "start"):
                    await component.start()
                    self.logger.debug(f"Started UI component: {component.__class__.__name__}")

            # Start TUI components
            for component in self.tui_components:
                if hasattr(component, "start"):
                    await component.start()
                    self.logger.debug(f"Started TUI component: {component.__class__.__name__}")

            # Start metrics collection
            await self._metrics_collector.start()

            # Start event emission
            await self._event_emitter.start()

            self._started = True
            self.logger.info("Dashboard adapter started successfully")

        except Exception as e:
            self.logger.exception(f"Failed to start dashboard adapter: {e}")
            await self.stop()
            raise

    async def stop(self) -> None:
        """
        Stop the dashboard adapter.
        """
        if not self._started:
            return

        self.logger.info("Stopping dashboard adapter")

        try:
            # Stop dashboard components
            for component in self.dashboard_components:
                if hasattr(component, "stop"):
                    await component.stop()
                    self.logger.debug(
                        f"Stopped dashboard component: {component.__class__.__name__}",
                    )

            # Stop UI components
            for component in self.ui_components:
                if hasattr(component, "stop"):
                    await component.stop()
                    self.logger.debug(f"Stopped UI component: {component.__class__.__name__}")

            # Stop TUI components
            for component in self.tui_components:
                if hasattr(component, "stop"):
                    await component.stop()
                    self.logger.debug(f"Stopped TUI component: {component.__class__.__name__}")

            # Stop metrics collection
            await self._metrics_collector.stop()

            # Stop event emission
            await self._event_emitter.stop()

            self._started = False
            self.logger.info("Dashboard adapter stopped")

        except Exception as e:
            self.logger.exception(f"Error stopping dashboard adapter: {e}")

    async def collect_metrics(self) -> dict[str, Any]:
        """
        Collect metrics from dashboard components.
        """
        metrics = {}

        try:
            # Collect dashboard component metrics
            for i, component in enumerate(self.dashboard_components):
                if hasattr(component, "get_metrics"):
                    component_metrics = await component.get_metrics()
                    metrics[f"dashboard_component_{i}"] = component_metrics

            # Collect UI component metrics
            for i, component in enumerate(self.ui_components):
                if hasattr(component, "get_metrics"):
                    component_metrics = await component.get_metrics()
                    metrics[f"ui_component_{i}"] = component_metrics

            # Collect TUI component metrics
            for i, component in enumerate(self.tui_components):
                if hasattr(component, "get_metrics"):
                    component_metrics = await component.get_metrics()
                    metrics[f"tui_component_{i}"] = component_metrics

            # Add adapter metrics
            metrics.update(
                {
                    "dashboard_adapter_started": self._started,
                    "dashboard_adapter_uptime": time.time() - self._last_health_check,
                    "dashboards_count": len(self._dashboards),
                    "panels_count": len(self._panels),
                    "dashboard_components_count": len(self.dashboard_components),
                    "ui_components_count": len(self.ui_components),
                    "tui_components_count": len(self.tui_components),
                },
            )

            # Record metrics
            self._metrics_collector.gauge("dashboard_dashboards_count", len(self._dashboards))
            self._metrics_collector.gauge("dashboard_panels_count", len(self._panels))
            self._metrics_collector.gauge(
                "dashboard_components_count", len(self.dashboard_components),
            )
            self._metrics_collector.gauge(
                "dashboard_adapter_uptime", time.time() - self._last_health_check,
            )

        except Exception as e:
            self.logger.exception(f"Error collecting dashboard metrics: {e}")
            metrics["error"] = str(e)

        return metrics

    async def process_events(self) -> list[dict[str, Any]]:
        """
        Process events from dashboard components.
        """
        events = []

        try:
            # Process dashboard component events
            for component in self.dashboard_components:
                if hasattr(component, "get_events"):
                    component_events = await component.get_events()
                    events.extend(component_events)

            # Process UI component events
            for component in self.ui_components:
                if hasattr(component, "get_events"):
                    component_events = await component.get_events()
                    events.extend(component_events)

            # Process TUI component events
            for component in self.tui_components:
                if hasattr(component, "get_events"):
                    component_events = await component.get_events()
                    events.extend(component_events)

            # Emit adapter events
            if self._started:
                self._event_emitter.emit(
                    "dashboard_adapter_status",
                    {
                        "status": "running",
                        "dashboards": len(self._dashboards),
                        "panels": len(self._panels),
                        "components": len(
                            self.dashboard_components + self.ui_components + self.tui_components,
                        ),
                    },
                    source="dashboard_adapter",
                    severity="info",
                )

        except Exception as e:
            self.logger.exception(f"Error processing dashboard events: {e}")
            events.append(
                {
                    "type": "error",
                    "source": "dashboard_adapter",
                    "message": str(e),
                    "timestamp": time.time(),
                },
            )

        return events

    async def health_check(self) -> dict[str, Any]:
        """
        Perform health check on dashboard components.
        """
        health = {
            "healthy": True,
            "adapter_started": self._started,
            "components": {},
            "timestamp": time.time(),
        }

        try:
            # Check dashboard components
            for i, component in enumerate(self.dashboard_components):
                component_name = f"dashboard_component_{i}_{component.__class__.__name__}"
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

            # Check UI components
            for i, component in enumerate(self.ui_components):
                component_name = f"ui_component_{i}_{component.__class__.__name__}"
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

            # Check TUI components
            for i, component in enumerate(self.tui_components):
                component_name = f"tui_component_{i}_{component.__class__.__name__}"
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
            self.logger.exception(f"Error in dashboard health check: {e}")
            health["healthy"] = False
            health["error"] = str(e)
            self._health_status = HealthStatus.UNHEALTHY

        return health

    # DashboardProvider implementation
    async def get_data(self, panel: DashboardPanel) -> dict[str, Any]:
        """
        Get data for a dashboard panel.
        """
        try:
            # Try to get data from dashboard components
            for component in self.dashboard_components:
                if hasattr(component, "get_panel_data"):
                    data = await component.get_panel_data(panel)
                    if data:
                        return data

            # Default data based on panel type
            return {
                "panel_id": panel.id,
                "panel_type": panel.panel_type,
                "title": panel.title,
                "data": panel.config.get("data", {}),
                "last_updated": time.time(),
            }
        except Exception as e:
            self.logger.exception(f"Error getting panel data: {e}")
            return {
                "panel_id": panel.id,
                "error": str(e),
                "timestamp": time.time(),
            }

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

    def add_dashboard_component(self, component: Any) -> None:
        """
        Add a dashboard component.
        """
        if component not in self.dashboard_components:
            self.dashboard_components.append(component)
            self.logger.info(f"Added dashboard component: {component.__class__.__name__}")

    def add_ui_component(self, component: Any) -> None:
        """
        Add a UI component.
        """
        if component not in self.ui_components:
            self.ui_components.append(component)
            self.logger.info(f"Added UI component: {component.__class__.__name__}")

    def add_tui_component(self, component: Any) -> None:
        """
        Add a TUI component.
        """
        if component not in self.tui_components:
            self.tui_components.append(component)
            self.logger.info(f"Added TUI component: {component.__class__.__name__}")

    def create_dashboard(self, name: str, description: str = "") -> Dashboard:
        """
        Create a new dashboard.
        """
        dashboard = Dashboard(name=name, description=description)
        self._dashboards[dashboard.id] = dashboard
        self.logger.info(f"Created dashboard: {name}")
        return dashboard

    def add_panel(self, dashboard_id: str, panel: DashboardPanel) -> bool:
        """
        Add a panel to a dashboard.
        """
        if dashboard_id in self._dashboards:
            self._dashboards[dashboard_id].panels.append(panel)
            self._panels[panel.id] = panel
            self.logger.info(f"Added panel {panel.title} to dashboard {dashboard_id}")
            return True
        return False

    def get_dashboard(self, dashboard_id: str) -> Dashboard | None:
        """
        Get a dashboard by ID.
        """
        return self._dashboards.get(dashboard_id)

    def list_dashboards(self) -> list[Dashboard]:
        """
        List all dashboards.
        """
        return list(self._dashboards.values())
