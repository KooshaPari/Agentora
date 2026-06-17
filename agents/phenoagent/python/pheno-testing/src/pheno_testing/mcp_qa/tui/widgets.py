"""Comprehensive Textual TUI widgets for Atoms MCP test suite.

DEPRECATED: This module is kept for backward compatibility.
All widgets have been decomposed into:
- widgets_base: Core widgets (TestTreeWidget, TestDetailWidget, etc.)
- widgets_test: Test selection widgets (TestSelectorWidget, CommandPaletteWidget, etc.)
- widgets_oauth: OAuth widgets (OAuthStatusWidget)
- widgets_results: Results display (MetricsDashboardWidget, ExportDialogWidget, etc.)
- widgets_filters: Filter dialogs (FilterDialogWidget)

New code should import directly from the specific modules or from the package __init__.

This module traces to: FR-QA-TUI-001
"""

from __future__ import annotations

from typing import Any, Dict, List

# Re-export all widgets from decomposed modules for backward compatibility
from pheno.testing.mcp_qa.tui.widgets_base import (
    LogStreamWidget,
    ProgressBarWidget,
    SummaryStatsWidget,
    TestDetailWidget,
    TestTreeWidget,
)
from pheno.testing.mcp_qa.tui.widgets_filters import FilterDialogWidget
from pheno.testing.mcp_qa.tui.widgets_oauth import OAuthStatusWidget
from pheno.testing.mcp_qa.tui.widgets_results import (
    BroadcastWidget,
    CacheStatsWidget,
    ExportDialogWidget,
    MetricsDashboardWidget,
    MultiEndpointWidget,
    TeamViewWidget,
    TimelineWidget,
)
from pheno.testing.mcp_qa.tui.widgets_test import (
    CommandPaletteWidget,
    FileWatcherWidget,
    ReloadIndicatorWidget,
    TestSelectorWidget,
)

__all__ = [
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
    "OAuthStatusWidget",
    "create_default_commands",
]


def create_default_commands() -> List[Dict[str, Any]]:
    """Create default command palette commands.

    Returns:
        List of command dictionaries
    """
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
