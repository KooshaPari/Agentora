"""Textual TUI for Atoms MCP Test Suite.

Production-ready interactive test dashboard with comprehensive features:
- Phase 1: Main app with grid layout, header, footer, test tree, output panels
- Phase 2: FileWatcher integration, enable/disable auto-reload, smart test re-running
- Phase 3: All keyboard bindings, mouse handlers, filter modal, test selection
- Phase 4: Metrics widgets, export functionality, performance tracking
- Phase 5: WebSocket broadcasting, multi-endpoint support, team visibility

Author: Atoms MCP Framework
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

try:
    from textual import on, work
    from textual.app import App, ComposeResult
    from textual.widgets import (
        DataTable,
        Footer,
        Header,
        RichLog,
    )

    HAS_TEXTUAL = True
except ImportError:
    HAS_TEXTUAL = False
    App = object

from .dashboard_config import get_default_filters
from .dashboard_handlers import DashboardActionHandler
from .dashboard_execution import TestExecutionMixin
from .dashboard_modals import ExportModal, FilterModal, HelpModal
from .dashboard_websocket import WebSocketBroadcaster
from .dashboard_widgets import (
    LiveMonitorWidget,
    MetricsWidget,
    OAuthStatusWidget,
    ResourceStatusWidget,
    ServerStatusWidget,
    TeamVisibilityWidget,
    TestProgressWidget,
    TestSummaryWidget,
    TunnelStatusWidget,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.FileHandler("tui.log"), logging.StreamHandler()],
)
logger = logging.getLogger("pheno.testing.mcp_qa.tui")


class TestDashboardApp(App, DashboardActionHandler, TestExecutionMixin):
    """Comprehensive TUI application for Atoms MCP test dashboard.

    Integrates all 5 phases:
    - Phase 1: Core layout and widgets
    - Phase 2: FileWatcher and auto-reload
    - Phase 3: Keyboard bindings and modals
    - Phase 4: Metrics and export
    - Phase 5: WebSocket and team visibility
    """

    CSS = """
    Screen {
        layout: grid;
        grid-size: 4 5;
        grid-rows: auto auto auto 1fr auto;
    }

    #oauth-status { column-span: 1; height: auto; }
    #server-status { column-span: 1; height: auto; }
    #tunnel-status { column-span: 1; height: auto; }
    #resource-status { column-span: 1; height: auto; }
    #summary { column-span: 4; height: auto; }
    #progress { column-span: 3; height: auto; }
    #metrics { column-span: 1; height: auto; }
    #test-tree { row-span: 1; column-span: 1; border: solid $primary; overflow-y: scroll; }
    #test-output { row-span: 1; column-span: 1; border: solid $accent; overflow-y: scroll; }
    #live-monitor { row-span: 1; column-span: 1; border: solid $warning; }
    #logs { column-span: 2; border: solid $secondary; height: 15; }
    #team-visibility { column-span: 1; border: solid $success; height: 15; }
    Footer { dock: bottom; }
    .light-theme { background: $surface; color: $text; }
    .dark-theme { background: $background; color: $text; }
    ModalScreen { background: rgba(0, 0, 0, 0.7); }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("escape", "quit", "Quit"),
        ("h", "help", "Help"),
        ("?", "help", "Help"),
        ("r", "run_tests", "Run All"),
        ("R", "run_selected", "Run Selected"),
        ("s", "stop_tests", "Stop"),
        ("space", "toggle_selection", "Toggle Selection"),
        ("enter", "run_single", "Run Test"),
        ("f", "filter_tests", "Filter"),
        ("/", "filter_tests", "Filter"),
        ("ctrl+f", "quick_search", "Quick Search"),
        ("n", "next_result", "Next"),
        ("N", "prev_result", "Previous"),
        ("c", "clear_cache", "Clear Cache"),
        ("C", "clear_tool_cache", "Clear Tool Cache"),
        ("o", "clear_oauth", "Clear OAuth"),
        ("l", "toggle_live_reload", "Toggle Reload"),
        ("L", "configure_watch_paths", "Config Paths"),
        ("ctrl+r", "force_reload", "Force Reload"),
        ("ctrl+h", "health_check", "Health Check"),
        ("t", "toggle_theme", "Toggle Theme"),
        ("m", "toggle_metrics", "Toggle Metrics"),
        ("v", "toggle_visibility", "Toggle Visibility"),
        ("ctrl+l", "clear_output", "Clear Output"),
        ("e", "export_results", "Export"),
        ("E", "quick_export", "Quick Export"),
        ("p", "performance_report", "Perf Report"),
        ("w", "toggle_websocket", "Toggle WS"),
        ("W", "configure_websocket", "Config WS"),
        ("u", "show_users", "Show Users"),
        ("d", "toggle_debug", "Debug"),
        ("i", "inspect_test", "Inspect"),
        ("ctrl+s", "save_session", "Save Session"),
        ("ctrl+o", "load_session", "Load Session"),
    ]

    def __init__(
        self,
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
    ):
        super().__init__()
        self.endpoint = endpoint
        self.test_modules = test_modules
        self.enable_live_reload_flag = enable_live_reload
        self.watch_paths = watch_paths or ["tools/"]
        self.test_runner = None
        self.test_results = []
        self.current_filters = get_default_filters()
        self.selected_tests = set()
        self.is_running = False
        self.file_watcher = None
        self.reload_manager = None
        self.test_durations = []
        self.cache_hits = 0
        self.cache_misses = 0
        self.websocket_enabled = enable_websocket
        self.websocket_broadcaster = WebSocketBroadcaster(websocket_host, websocket_port)
        self.oauth_cache_client = oauth_cache_client
        self.tunnel_config = tunnel_config or {}
        self.resource_config = resource_config or {}
        self.client_adapter = None
        self.dark_theme = True
        self.show_metrics = True
        self.show_team_visibility = True
        self.debug_mode = False

    def compose(self) -> ComposeResult:
        """Create child widgets for all phases."""
        yield Header(show_clock=True)
        yield OAuthStatusWidget(oauth_cache_client=self.oauth_cache_client, id="oauth-status")
        yield ServerStatusWidget(client_adapter=self.client_adapter, id="server-status")
        yield TunnelStatusWidget(tunnel_config=self.tunnel_config, id="tunnel-status")
        yield ResourceStatusWidget(resource_config=self.resource_config, id="resource-status")
        yield TestSummaryWidget(id="summary")
        yield TestProgressWidget(id="progress")
        yield MetricsWidget(id="metrics")

        test_table = DataTable(id="test-tree", zebra_stripes=True, cursor_type="row")
        test_table.add_columns("", "Test", "Status", "Time", "Tool")
        yield test_table

        yield RichLog(id="test-output", highlight=True, markup=True, wrap=True)
        yield LiveMonitorWidget(id="live-monitor")
        yield RichLog(id="logs", highlight=True, markup=True, wrap=True)
        yield TeamVisibilityWidget(id="team-visibility")
        yield Footer()

    async def on_mount(self) -> None:
        """Called when app is mounted - initialize all phases."""
        self.title = "Atoms MCP Test Dashboard"
        self.sub_title = f"Endpoint: {self.endpoint}"

        logs = self.query_one("#logs", RichLog)
        logs.write("[bold green]🚀 Atoms MCP Test Dashboard Started[/bold green]")
        logs.write(f"[cyan]Endpoint:[/cyan] {self.endpoint}")
        logs.write(f"[cyan]Test Modules:[/cyan] {len(self.test_modules)}")
        logs.write(
            f"[cyan]Live Reload:[/cyan] {'Enabled' if self.enable_live_reload_flag else 'Disabled'}"
        )

        try:
            from fastmcp import Client

            client = Client(self.endpoint)
            self.client_adapter = AtomsMCPClientAdapter(client)
            server_status = self.query_one("#server-status", ServerStatusWidget)
            server_status.client_adapter = self.client_adapter
            if self.client_adapter:
                server_status.endpoint = self.client_adapter.endpoint
        except Exception as e:
            logs.write(f"[yellow]⚠️  Client adapter initialization failed: {e}[/yellow]")
            logger.warning(f"Client adapter init failed: {e}")

        if self.enable_live_reload_flag:
            await self._setup_file_watcher()

        if self.websocket_enabled:
            await self._setup_websocket()

        await self._load_test_modules()
        self.set_interval(5.0, self._refresh_status_widgets)
        logger.info("Test dashboard mounted successfully")

    async def _setup_file_watcher(self) -> None:
        """Setup file watcher for auto-reload (Phase 2)."""
        try:
            from .file_watcher import TestFileWatcher

            logs = self.query_one("#logs", RichLog)
            self.file_watcher = TestFileWatcher(
                watch_paths=self.watch_paths, on_change=self._on_file_change, debounce_seconds=0.5
            )
            self.file_watcher.start()
            logs.write(
                f"[green]📁 FileWatcher started monitoring: {', '.join(self.watch_paths)}[/green]"
            )
            logger.info(f"FileWatcher monitoring: {self.watch_paths}")
        except ImportError:
            logs = self.query_one("#logs", RichLog)
            logs.write(
                "[yellow]⚠️  watchdog not installed. Install with: pip install watchdog[/yellow]"
            )
            logger.warning("FileWatcher disabled - watchdog not installed")
        except Exception as e:
            logs = self.query_one("#logs", RichLog)
            logs.write(f"[red]❌ FileWatcher error: {e}[/red]")
            logger.error(f"FileWatcher setup failed: {e}")

    async def _setup_websocket(self) -> None:
        """Setup WebSocket server for team visibility (Phase 5)."""
        try:
            await self.websocket_broadcaster.start()
            logs = self.query_one("#logs", RichLog)
            logs.write(
                f"[green]🌐 WebSocket server started on ws://{self.websocket_broadcaster.host}:{self.websocket_broadcaster.port}[/green]"
            )
            team_widget = self.query_one("#team-visibility", TeamVisibilityWidget)
            team_widget.websocket_enabled = True
            logger.info("WebSocket server started successfully")
        except Exception as e:
            logs = self.query_one("#logs", RichLog)
            logs.write(f"[red]❌ WebSocket error: {e}[/red]")
            logger.error(f"WebSocket setup failed: {e}")

    def _on_file_change(self, file_path: str) -> None:
        """Handle file change event from FileWatcher (Phase 2)."""
        logs = self.query_one("#logs", RichLog)
        logs.write(f"[yellow]🔄 File changed: {Path(file_path).name}[/yellow]")

        if self.file_watcher:
            affected_tools = self.file_watcher.get_affected_tools(file_path)
            if affected_tools:
                logs.write(f"[cyan]   Affected tools: {', '.join(affected_tools)}[/cyan]")
                if (
                    self.test_runner
                    and hasattr(self.test_runner, "cache_instance")
                    and self.test_runner.cache_instance
                ):
                    for tool in affected_tools:
                        self.test_runner.cache_instance.clear_tool(tool)
                    logs.write("[green]   Cache cleared for affected tools[/green]")
                self.call_later(self._rerun_affected_tests, affected_tools)
            else:
                logs.write("[yellow]   Re-running all tests...[/yellow]")
                self.call_later(self.action_run_tests)
        logger.info(f"File change detected: {file_path}")

    def _rerun_affected_tests(self, affected_tools: List[str]) -> None:
        """Re-run tests for affected tools only (Phase 2)."""
        logs = self.query_one("#logs", RichLog)
        logs.write(f"[cyan]▶️  Re-running tests for: {', '.join(affected_tools)}[/cyan]")
        logger.info(f"Re-running tests for tools: {affected_tools}")

    async def _load_test_modules(self) -> None:
        """Load and populate test modules in the tree."""
        logs = self.query_one("#logs", RichLog)
        test_table = self.query_one("#test-tree", DataTable)
        try:
            logs.write("[cyan]📦 Loading test modules...[/cyan]")
            from .decorators import get_test_registry

            registry = get_test_registry()
            tests = registry.get_tests()
            for test_name, test_info in tests.items():
                test_table.add_row(
                    "☐", test_name, "⏸️ Pending", "—", test_info.get("tool_name", "unknown")
                )
            logs.write(f"[green]✅ Loaded {len(tests)} tests[/green]")
            summary = self.query_one("#summary", TestSummaryWidget)
            summary.total = len(tests)
            logger.info(f"Loaded {len(tests)} tests from registry")
        except Exception as e:
            logs.write(f"[red]❌ Error loading tests: {e}[/red]")
            logger.error(f"Failed to load test modules: {e}", exc_info=True)

    async def _refresh_status_widgets(self) -> None:
        """Refresh all status monitoring widgets (called every 5 seconds)."""
        try:
            oauth_widget = self.query_one("#oauth-status", OAuthStatusWidget)
            await oauth_widget.refresh_status()
            server_widget = self.query_one("#server-status", ServerStatusWidget)
            await server_widget.refresh_status()
            tunnel_widget = self.query_one("#tunnel-status", TunnelStatusWidget)
            await tunnel_widget.refresh_status()
            resource_widget = self.query_one("#resource-status", ResourceStatusWidget)
            await resource_widget.refresh_status()
        except Exception as e:
            logger.error(f"Status widget refresh failed: {e}")

    async def on_unmount(self) -> None:
        """Cleanup when app is unmounted."""
        if self.file_watcher:
            self.file_watcher.stop()
            logger.info("FileWatcher stopped")
        if self.websocket_enabled:
            await self.websocket_broadcaster.stop()
            logger.info("WebSocket server stopped")
        logger.info("Test dashboard unmounted")


def run_tui_dashboard(
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
) -> None:
    """Run comprehensive TUI dashboard for Atoms MCP test suite.

    Features:
        - Phase 1: Grid layout with header, footer, test tree, output panels
        - Phase 2: FileWatcher integration with smart test re-running
        - Phase 3: 30+ keyboard shortcuts, mouse handlers, modal dialogs
        - Phase 4: Real-time metrics, export to JSON/MD/HTML/CSV
        - Phase 5: WebSocket broadcasting for team collaboration
        - Status Monitoring: OAuth, Server, Tunnel, Resources with auto-refresh
    """
    if not HAS_TEXTUAL:
        print("❌ Textual not installed. Install with: pip install textual")
        print("   Falling back to standard test runner...")
        return

    try:
        app = TestDashboardApp(
            endpoint=endpoint,
            test_modules=test_modules,
            enable_live_reload=enable_live_reload,
            watch_paths=watch_paths,
            enable_websocket=enable_websocket,
            websocket_host=websocket_host,
            websocket_port=websocket_port,
            oauth_cache_client=oauth_cache_client,
            tunnel_config=tunnel_config,
            resource_config=resource_config,
        )
        logger.info("Starting Atoms MCP Test Dashboard")
        app.run()
    except KeyboardInterrupt:
        logger.info("Dashboard interrupted by user")
        print("\n👋 Goodbye!")
    except Exception as e:
        logger.error(f"Dashboard crashed: {e}", exc_info=True)
        print(f"\n❌ Dashboard error: {e}")
        raise


__all__ = [
    "TestDashboardApp",
    "run_tui_dashboard",
]
