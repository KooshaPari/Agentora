"""TUI components for MCP test dashboards.

New modular structure from decomposed dashboard.py:
- dashboard: Main app (TestDashboardApp)
- dashboard_widgets: Status display widgets (OAuth, Server, Tunnel, Resources, etc.)
- dashboard_modals: Dialogs (Filter, Export, Help)
- dashboard_handlers: Action handlers for keyboard bindings
- dashboard_config: Configuration and state management
- dashboard_websocket: WebSocket broadcasting for team visibility

Legacy structure:
- base/: Base classes (BaseDashboard, BaseWidget)
- factories/: Factory classes for creating components
- components/: Generic reusable components
"""

from typing import Any, Dict, List

from .base import BaseDashboard, BaseWidget
from .components import GenericStatusPanel
from .factories import DashboardFactory, WidgetFactory

from .widgets_base import (
    LogStreamWidget,
    ProgressBarWidget,
    SummaryStatsWidget,
    TestDetailWidget,
    TestTreeWidget,
)
from .widgets_filters import FilterDialogWidget
from .widgets_oauth import OAuthStatusWidget as OAuthStatusWidgetBase
from .widgets_results import (
    BroadcastWidget,
    CacheStatsWidget,
    ExportDialogWidget,
    MetricsDashboardWidget,
    MultiEndpointWidget,
    TeamViewWidget,
    TimelineWidget,
)
from .widgets_test import (
    CommandPaletteWidget,
    FileWatcherWidget,
    ReloadIndicatorWidget,
    TestSelectorWidget,
)

from .dashboard import TestDashboardApp, run_tui_dashboard
from .dashboard_config import (
    DashboardConfig,
    FilterState,
    TestExecutionState,
    UIState,
    DashboardState,
    get_default_filters,
    get_default_config,
)
from .dashboard_handlers import DashboardActionHandler
from .dashboard_modals import ExportModal, FilterModal, HelpModal
from .dashboard_websocket import WebSocketBroadcaster, HAS_WEBSOCKETS
from .dashboard_execution import TestExecutionMixin
from .dashboard_widgets import (
    OAuthStatusWidget,
    ServerStatusWidget,
    TunnelStatusWidget,
    ResourceStatusWidget,
    TestSummaryWidget,
    TestProgressWidget,
    MetricsWidget,
    LiveMonitorWidget,
    TeamVisibilityWidget,
)

__all__ = [
    "BaseDashboard",
    "BaseWidget",
    "DashboardFactory",
    "WidgetFactory",
    "GenericStatusPanel",
    "TestDashboardApp",
    "run_tui_dashboard",
    "DashboardConfig",
    "FilterState",
    "TestExecutionState",
    "UIState",
    "DashboardState",
    "get_default_filters",
    "get_default_config",
    "DashboardActionHandler",
    "TestExecutionMixin",
    "ExportModal",
    "FilterModal",
    "HelpModal",
    "WebSocketBroadcaster",
    "HAS_WEBSOCKETS",
    "OAuthStatusWidget",
    "ServerStatusWidget",
    "TunnelStatusWidget",
    "ResourceStatusWidget",
    "TestSummaryWidget",
    "TestProgressWidget",
    "MetricsWidget",
    "LiveMonitorWidget",
    "TeamVisibilityWidget",
    "TestTreeWidget",
    "TestDetailWidget",
    "SummaryStatsWidget",
    "ProgressBarWidget",
    "LogStreamWidget",
    "FileWatcherWidget",
    "ReloadIndicatorWidget",
    "TestSelectorWidget",
    "CommandPaletteWidget",
    "FilterDialogWidget",
    "MetricsDashboardWidget",
    "TimelineWidget",
    "CacheStatsWidget",
    "ExportDialogWidget",
    "MultiEndpointWidget",
    "TeamViewWidget",
    "BroadcastWidget",
    "create_default_commands",
]

__version__ = "2.2.0"


def create_default_commands() -> List[Dict[str, Any]]:
    """Create default command palette commands."""
    return [
        {
            "name": "run_all",
            "description": "Run all tests",
            "shortcut": "Ctrl+R",
            "category": "test",
        },
        {
            "name": "run_selected",
            "description": "Run selected tests",
            "shortcut": "Ctrl+Shift+R",
            "category": "test",
        },
        {
            "name": "filter_tests",
            "description": "Filter tests",
            "shortcut": "Ctrl+F",
            "category": "view",
        },
        {
            "name": "clear_logs",
            "description": "Clear log output",
            "shortcut": "Ctrl+L",
            "category": "view",
        },
        {
            "name": "export_results",
            "description": "Export test results",
            "shortcut": "Ctrl+E",
            "category": "file",
        },
        {
            "name": "toggle_reload",
            "description": "Toggle auto-reload",
            "shortcut": "Ctrl+W",
            "category": "test",
        },
        {
            "name": "show_metrics",
            "description": "Show metrics dashboard",
            "shortcut": "Ctrl+M",
            "category": "view",
        },
        {
            "name": "quit",
            "description": "Quit application",
            "shortcut": "Ctrl+Q",
            "category": "app",
        },
    ]
