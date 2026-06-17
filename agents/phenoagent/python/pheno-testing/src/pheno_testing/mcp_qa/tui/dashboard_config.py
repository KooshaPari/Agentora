"""Configuration and state management for dashboard.

Contains dashboard state, configuration dataclasses, and state management utilities.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import logging

logger = logging.getLogger("pheno.testing.mcp_qa.tui")


@dataclass
class DashboardConfig:
    """Main configuration for the test dashboard."""

    endpoint: str = ""
    test_modules: List[str] = field(default_factory=list)
    enable_live_reload: bool = True
    watch_paths: List[str] = field(default_factory=lambda: ["tools/"])
    enable_websocket: bool = False
    websocket_host: str = "localhost"
    websocket_port: int = 8765
    oauth_cache_client: Any = None
    tunnel_config: Dict[str, Any] = field(default_factory=dict)
    resource_config: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_args(
        cls,
        endpoint: str,
        test_modules: List[str],
        enable_live_reload: bool = True,
        watch_paths: Optional[List[str]] = None,
        enable_websocket: bool = False,
        websocket_host: str = "localhost",
        websocket_port: int = 8765,
        oauth_cache_client=None,
        tunnel_config: Optional[Dict[str, Any]] = None,
        resource_config: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> "DashboardConfig":
        """Create config from arguments."""
        return cls(
            endpoint=endpoint,
            test_modules=test_modules,
            enable_live_reload=enable_live_reload,
            watch_paths=watch_paths or ["tools/"],
            enable_websocket=enable_websocket,
            websocket_host=websocket_host,
            websocket_port=websocket_port,
            oauth_cache_client=oauth_cache_client,
            tunnel_config=tunnel_config or {},
            resource_config=resource_config or {},
        )


@dataclass
class FilterState:
    """Filter state for test results."""

    show_passed: bool = True
    show_failed: bool = True
    show_skipped: bool = True
    show_cached: bool = True
    search: str = ""
    tool: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "show_passed": self.show_passed,
            "show_failed": self.show_failed,
            "show_skipped": self.show_skipped,
            "show_cached": self.show_cached,
            "search": self.search,
            "tool": self.tool,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FilterState":
        """Create from dictionary."""
        return cls(
            show_passed=data.get("show_passed", True),
            show_failed=data.get("show_failed", True),
            show_skipped=data.get("show_skipped", True),
            show_cached=data.get("show_cached", True),
            search=data.get("search", ""),
            tool=data.get("tool", ""),
        )


@dataclass
class TestExecutionState:
    """State for test execution."""

    is_running: bool = False
    selected_tests: Set[str] = field(default_factory=set)
    test_results: List[Dict[str, Any]] = field(default_factory=list)
    test_durations: List[float] = field(default_factory=list)
    cache_hits: int = 0
    cache_misses: int = 0
    current_filters: FilterState = field(default_factory=FilterState)


@dataclass
class UIState:
    """UI state for dashboard."""

    dark_theme: bool = True
    show_metrics: bool = True
    show_team_visibility: bool = True
    debug_mode: bool = False


@dataclass
class DashboardState:
    """Complete dashboard state."""

    config: DashboardConfig = field(default_factory=DashboardConfig)
    execution: TestExecutionState = field(default_factory=TestExecutionState)
    ui: UIState = field(default_factory=UIState)
    client_adapter: Any = None
    test_runner: Any = None
    file_watcher: Any = None


def get_default_filters() -> Dict[str, Any]:
    """Get default filter configuration."""
    return {
        "show_passed": True,
        "show_failed": True,
        "show_skipped": True,
        "show_cached": True,
        "search": "",
        "tool": "",
    }


def get_default_config() -> DashboardConfig:
    """Get default dashboard configuration."""
    return DashboardConfig()


__all__ = [
    "DashboardConfig",
    "FilterState",
    "TestExecutionState",
    "UIState",
    "DashboardState",
    "get_default_filters",
    "get_default_config",
]
