"""Dashboard Management.

Unified dashboard system that consolidates functionality from infra/monitoring, MCP QA,
and observability stacks.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import uuid4

from ..logging import get_logger

logger = get_logger(__name__)


@dataclass
class DashboardPanel:
    """
    A dashboard panel configuration.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    panel_type: str = "metric"  # metric, chart, table, log, status
    position: dict[str, int] = field(default_factory=lambda: {"x": 0, "y": 0, "w": 6, "h": 4})
    config: dict[str, Any] = field(default_factory=dict)
    refresh_interval: float = 5.0
    enabled: bool = True


@dataclass
class Dashboard:
    """
    A dashboard configuration.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    panels: list[DashboardPanel] = field(default_factory=list)
    refresh_interval: float = 1.0
    auto_refresh: bool = True
    enabled: bool = True
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class DashboardProvider(Protocol):
    """
    Protocol for dashboard data providers.
    """

    async def get_data(self, panel: DashboardPanel) -> dict[str, Any]:
        """
        Get data for a dashboard panel.
        """
        ...

    async def health_check(self) -> dict[str, Any]:
        """
        Check provider health.
        """
        ...


class DashboardManager:
    """Manages dashboards and their data providers.

    Consolidates dashboard functionality from infra/monitoring, MCP QA, and
    observability stacks into a unified interface.
    """

    def __init__(self, refresh_interval: float = 1.0):
        """Initialize dashboard manager.

        Args:
            refresh_interval: Default refresh interval for dashboards
        """
        self.refresh_interval = refresh_interval
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

        # Dashboard storage
        self._dashboards: dict[str, Dashboard] = {}
        self._providers: dict[str, DashboardProvider] = {}

        # State
        self._running = False
        self._refresh_tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        """
        Start dashboard manager.
        """
        if self._running:
            self.logger.warning("Dashboard manager already started")
            return

        self._running = True

        # Start refresh tasks for enabled dashboards
        for dashboard in self._dashboards.values():
            if dashboard.enabled and dashboard.auto_refresh:
                task = asyncio.create_task(self._refresh_dashboard(dashboard))
                self._refresh_tasks.append(task)

        self.logger.info("Started dashboard manager")

    async def stop(self) -> None:
        """
        Stop dashboard manager.
        """
        if not self._running:
            return

        # Cancel refresh tasks
        for task in self._refresh_tasks:
            task.cancel()

        if self._refresh_tasks:
            await asyncio.gather(*self._refresh_tasks, return_exceptions=True)

        self._running = False
        self.logger.info("Stopped dashboard manager")

    async def _refresh_dashboard(self, dashboard: Dashboard) -> None:
        """
        Refresh a dashboard periodically.
        """
        while self._running and dashboard.enabled:
            try:
                await self._update_dashboard_data(dashboard)
                await self._wait_for_next_refresh(dashboard)
            except asyncio.CancelledError:
                break
            except Exception as e:
                await self._handle_refresh_error(dashboard, e)

    async def _wait_for_next_refresh(self, dashboard: Dashboard) -> None:
        """
        Wait for the next refresh cycle.
        """
        await asyncio.sleep(dashboard.refresh_interval)

    async def _handle_refresh_error(self, dashboard: Dashboard, error: Exception) -> None:
        """
        Handle errors during dashboard refresh.
        """
        self.logger.error(f"Error refreshing dashboard {dashboard.name}: {error}")
        await asyncio.sleep(1.0)

    async def _update_dashboard_data(self, dashboard: Dashboard) -> None:
        """
        Update data for all panels in a dashboard.
        """
        for panel in dashboard.panels:
            if not panel.enabled:
                continue

            try:
                # Find provider for this panel
                provider = self._find_provider_for_panel(panel)
                if provider:
                    data = await provider.get_data(panel)
                    panel.config["data"] = data
                    panel.config["last_updated"] = time.time()
                else:
                    self.logger.warning(f"No provider found for panel {panel.id}")
            except Exception as e:
                self.logger.exception(f"Error updating panel {panel.id}: {e}")

    def _find_provider_for_panel(self, panel: DashboardPanel) -> DashboardProvider | None:
        """
        Find a provider for a panel based on panel type or configuration.
        """
        # Simple provider selection based on panel type
        provider_mapping = {
            "metric": "metrics",
            "chart": "metrics",
            "table": "events",
            "log": "events",
            "status": "health",
        }

        provider_name = provider_mapping.get(panel.panel_type, "default")
        return self._providers.get(provider_name)

    def create_dashboard(
        self,
        name: str,
        description: str = "",
        panels: list[DashboardPanel] | None = None,
        refresh_interval: float | None = None,
    ) -> Dashboard:
        """Create a new dashboard.

        Args:
            name: Dashboard name
            description: Dashboard description
            panels: List of panels
            refresh_interval: Refresh interval

        Returns:
            The created dashboard
        """
        dashboard = Dashboard(
            name=name,
            description=description,
            panels=panels or [],
            refresh_interval=refresh_interval or self.refresh_interval,
        )

        self._dashboards[dashboard.id] = dashboard
        self.logger.info(f"Created dashboard: {name}")

        # Start refresh task if manager is running
        if self._running and dashboard.enabled and dashboard.auto_refresh:
            task = asyncio.create_task(self._refresh_dashboard(dashboard))
            self._refresh_tasks.append(task)

        return dashboard

    def get_dashboard(self, dashboard_id: str) -> Dashboard | None:
        """
        Get a dashboard by ID.
        """
        return self._dashboards.get(dashboard_id)

    def get_dashboard_by_name(self, name: str) -> Dashboard | None:
        """
        Get a dashboard by name.
        """
        for dashboard in self._dashboards.values():
            if dashboard.name == name:
                return dashboard
        return None

    def list_dashboards(self) -> list[Dashboard]:
        """
        List all dashboards.
        """
        return list(self._dashboards.values())

    def update_dashboard(self, dashboard_id: str, **updates: Any) -> Dashboard | None:
        """
        Update a dashboard.
        """
        dashboard = self._dashboards.get(dashboard_id)
        if not dashboard:
            return None

        # Update fields
        for key, value in updates.items():
            if hasattr(dashboard, key):
                setattr(dashboard, key, value)

        dashboard.updated_at = time.time()
        self.logger.info(f"Updated dashboard: {dashboard.name}")
        return dashboard

    def delete_dashboard(self, dashboard_id: str) -> bool:
        """
        Delete a dashboard.
        """
        if dashboard_id in self._dashboards:
            dashboard = self._dashboards[dashboard_id]
            del self._dashboards[dashboard_id]
            self.logger.info(f"Deleted dashboard: {dashboard.name}")
            return True
        return False

    def add_panel(
        self,
        dashboard_id: str,
        panel: DashboardPanel,
    ) -> Dashboard | None:
        """
        Add a panel to a dashboard.
        """
        dashboard = self._dashboards.get(dashboard_id)
        if not dashboard:
            return None

        dashboard.panels.append(panel)
        dashboard.updated_at = time.time()
        self.logger.info(f"Added panel {panel.title} to dashboard {dashboard.name}")
        return dashboard

    def remove_panel(self, dashboard_id: str, panel_id: str) -> Dashboard | None:
        """
        Remove a panel from a dashboard.
        """
        dashboard = self._dashboards.get(dashboard_id)
        if not dashboard:
            return None

        dashboard.panels = [p for p in dashboard.panels if p.id != panel_id]
        dashboard.updated_at = time.time()
        self.logger.info(f"Removed panel {panel_id} from dashboard {dashboard.name}")
        return dashboard

    def register_provider(self, name: str, provider: DashboardProvider) -> None:
        """
        Register a dashboard data provider.
        """
        self._providers[name] = provider
        self.logger.info(f"Registered dashboard provider: {name}")

    def unregister_provider(self, name: str) -> None:
        """
        Unregister a dashboard data provider.
        """
        if name in self._providers:
            del self._providers[name]
            self.logger.info(f"Unregistered dashboard provider: {name}")

    def get_dashboard_data(self, dashboard_id: str) -> dict[str, Any] | None:
        """
        Get current data for a dashboard.
        """
        dashboard = self._dashboards.get(dashboard_id)
        if not dashboard:
            return None

        data = {
            "dashboard": {
                "id": dashboard.id,
                "name": dashboard.name,
                "description": dashboard.description,
                "refresh_interval": dashboard.refresh_interval,
                "auto_refresh": dashboard.auto_refresh,
                "enabled": dashboard.enabled,
                "created_at": dashboard.created_at,
                "updated_at": dashboard.updated_at,
            },
            "panels": [],
        }

        for panel in dashboard.panels:
            panel_data = {
                "id": panel.id,
                "title": panel.title,
                "type": panel.panel_type,
                "position": panel.position,
                "config": panel.config,
                "refresh_interval": panel.refresh_interval,
                "enabled": panel.enabled,
            }
            data["panels"].append(panel_data)

        return data

    async def refresh_dashboard(self, dashboard_id: str) -> bool:
        """
        Manually refresh a dashboard.
        """
        dashboard = self._dashboards.get(dashboard_id)
        if not dashboard:
            return False

        try:
            await self._update_dashboard_data(dashboard)
            self.logger.info(f"Manually refreshed dashboard: {dashboard.name}")
            return True
        except Exception as e:
            self.logger.exception(f"Error refreshing dashboard {dashboard.name}: {e}")
            return False

    async def health_check(self) -> dict[str, Any]:
        """
        Check dashboard manager health.
        """
        health = {
            "healthy": True,
            "running": self._running,
            "dashboards": len(self._dashboards),
            "providers": len(self._providers),
            "refresh_tasks": len(self._refresh_tasks),
            "provider_health": {},
        }

        # Check provider health
        for name, provider in self._providers.items():
            try:
                provider_health = await provider.health_check()
                health["provider_health"][name] = provider_health
                if not provider_health.get("healthy", False):
                    health["healthy"] = False
            except Exception as e:
                health["provider_health"][name] = {"healthy": False, "error": str(e)}
                health["healthy"] = False

        return health
