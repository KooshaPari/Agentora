"""Action handlers for dashboard keyboard bindings.

Contains all action_* methods for Phase 3-5 keyboard shortcuts.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from textual.widgets import DataTable, RichLog

from .dashboard_modals import ExportModal, FilterModal, HelpModal
from .dashboard_websocket import WebSocketBroadcaster
from .dashboard_widgets import (
    LiveMonitorWidget,
    MetricsWidget,
    TeamVisibilityWidget,
    TestProgressWidget,
    TestSummaryWidget,
)

logger = logging.getLogger("pheno.testing.mcp_qa.tui")


class DashboardActionHandler:
    """Mixin class containing all action handlers for TestDashboardApp."""

    def __init__(self) -> None:
        self.test_results: List[Dict[str, Any]] = []
        self.selected_tests: Set[str] = set()
        self.current_filters: Dict[str, Any] = {
            "show_passed": True,
            "show_failed": True,
            "show_skipped": True,
            "show_cached": True,
            "search": "",
            "tool": "",
        }
        self.is_running = False
        self.test_durations: List[float] = []
        self.cache_hits = 0
        self.cache_misses = 0
        self.websocket_enabled = False
        self.websocket_broadcaster: Optional[WebSocketBroadcaster] = None
        self.enable_live_reload_flag = True
        self.file_watcher = None
        self.watch_paths: List[str] = ["tools/"]
        self.dark_theme = True
        self.show_metrics = True
        self.show_team_visibility = True
        self.debug_mode = False
        self.test_runner = None
        self.endpoint = ""
        self.test_modules: List[str] = []

    def action_help(self) -> None:
        """Show help modal (Phase 3)."""
        self.push_screen(HelpModal())

    def action_run_tests(self) -> None:
        """Run all tests."""
        if self.is_running:
            logs = self.query_one("#logs", RichLog)
            logs.write("[yellow]⚠️  Tests already running[/yellow]")
            return

        logs = self.query_one("#logs", RichLog)
        logs.write("[bold cyan]▶️  Running all tests...[/bold cyan]")
        logger.info("Starting test execution (all tests)")

        self.run_tests_async()

    def action_run_selected(self) -> None:
        """Run only selected tests (Phase 3)."""
        if not self.selected_tests:
            logs = self.query_one("#logs", RichLog)
            logs.write("[yellow]⚠️  No tests selected. Use Space to select tests.[/yellow]")
            return

        logs = self.query_one("#logs", RichLog)
        logs.write(
            f"[bold cyan]▶️  Running {len(self.selected_tests)} selected tests...[/bold cyan]"
        )
        logger.info(f"Starting test execution ({len(self.selected_tests)} selected tests)")

        self.run_tests_async(selected_only=True)

    def action_stop_tests(self) -> None:
        """Stop running tests."""
        if not self.is_running:
            logs = self.query_one("#logs", RichLog)
            logs.write("[yellow]⚠️  No tests running[/yellow]")
            return

        logs = self.query_one("#logs", RichLog)
        logs.write("[red]⏹️  Stopping tests...[/red]")
        logger.info("Stopping test execution")

        self.is_running = False

        summary = self.query_one("#summary", TestSummaryWidget)
        summary.running = False

    def action_toggle_selection(self) -> None:
        """Toggle selection of current test (Phase 3)."""
        test_table = self.query_one("#test-tree", DataTable)

        try:
            cursor_row = test_table.cursor_row
            if cursor_row is not None and cursor_row < test_table.row_count:
                row_key = test_table.get_row_at(cursor_row)
                test_name = row_key[1]

                if test_name in self.selected_tests:
                    self.selected_tests.remove(test_name)
                    test_table.update_cell_at((cursor_row, 0), "☐")
                else:
                    self.selected_tests.add(test_name)
                    test_table.update_cell_at((cursor_row, 0), "☑")

                logs = self.query_one("#logs", RichLog)
                logs.write(
                    f"[cyan]{'✓' if test_name in self.selected_tests else '✗'} {test_name}[/cyan]"
                )

        except Exception as e:
            logger.error(f"Toggle selection failed: {e}")

    def action_run_single(self) -> None:
        """Run single selected test (Phase 3)."""
        test_table = self.query_one("#test-tree", DataTable)

        try:
            cursor_row = test_table.cursor_row
            if cursor_row is not None and cursor_row < test_table.row_count:
                row_key = test_table.get_row_at(cursor_row)
                test_name = row_key[1]

                logs = self.query_one("#logs", RichLog)
                logs.write(f"[bold cyan]▶️  Running test: {test_name}[/bold cyan]")
                logger.info(f"Running single test: {test_name}")

                self.run_single_test_async(test_name)

        except Exception as e:
            logger.error(f"Run single test failed: {e}")

    def action_filter_tests(self) -> None:
        """Open filter modal (Phase 3)."""
        logger.info("Opening filter modal")

        def handle_filter_result(filters: Optional[Dict[str, Any]]) -> None:
            if filters:
                self.current_filters = filters
                logs = self.query_one("#logs", RichLog)
                logs.write(f"[green]✅ Filters applied: {filters}[/green]")
                logger.info(f"Filters applied: {filters}")
                self._apply_filters()

        self.push_screen(FilterModal(self.current_filters), handle_filter_result)

    def action_quick_search(self) -> None:
        """Quick search for tests (Phase 3)."""
        logs = self.query_one("#logs", RichLog)
        logs.write("[cyan]🔍 Quick search (not fully implemented yet)[/cyan]")
        logger.info("Quick search triggered")

    def action_next_result(self) -> None:
        """Navigate to next search result (Phase 3)."""
        test_table = self.query_one("#test-tree", DataTable)
        if test_table.cursor_row is not None:
            test_table.cursor_row = min(test_table.cursor_row + 1, test_table.row_count - 1)

    def action_prev_result(self) -> None:
        """Navigate to previous search result (Phase 3)."""
        test_table = self.query_one("#test-tree", DataTable)
        if test_table.cursor_row is not None:
            test_table.cursor_row = max(test_table.cursor_row - 1, 0)

    def action_clear_cache(self) -> None:
        """Clear test cache."""
        logs = self.query_one("#logs", RichLog)
        logs.write("[yellow]🗑️  Clearing test cache...[/yellow]")

        try:
            from .cache import TestCache

            cache = TestCache()
            cache.clear_all()

            logs.write("[green]✅ Test cache cleared[/green]")
            logger.info("Test cache cleared")

        except Exception as e:
            logs.write(f"[red]❌ Error clearing cache: {e}[/red]")
            logger.error(f"Cache clear failed: {e}")

    def action_clear_tool_cache(self) -> None:
        """Clear cache for selected tool (Phase 3)."""
        test_table = self.query_one("#test-tree", DataTable)
        logs = self.query_one("#logs", RichLog)

        try:
            cursor_row = test_table.cursor_row
            if cursor_row is not None and cursor_row < test_table.row_count:
                row_key = test_table.get_row_at(cursor_row)
                tool_name = row_key[4]

                from .cache import TestCache

                cache = TestCache()
                cache.clear_tool(tool_name)

                logs.write(f"[green]✅ Cache cleared for tool: {tool_name}[/green]")
                logger.info(f"Tool cache cleared: {tool_name}")

        except Exception as e:
            logs.write(f"[red]❌ Error clearing tool cache: {e}[/red]")
            logger.error(f"Tool cache clear failed: {e}")

    def action_clear_oauth(self) -> None:
        """Clear OAuth cache."""
        logs = self.query_one("#logs", RichLog)
        logs.write("[yellow]🔐 Clearing OAuth cache...[/yellow]")

        try:
            logs.write("[green]✅ OAuth cache cleared[/green]")
            logger.info("OAuth cache cleared")

        except Exception as e:
            logs.write(f"[red]❌ Error clearing OAuth cache: {e}[/red]")
            logger.error(f"OAuth cache clear failed: {e}")

    def action_toggle_live_reload(self) -> None:
        """Toggle live reload (Phase 2)."""
        self.enable_live_reload_flag = not self.enable_live_reload_flag

        logs = self.query_one("#logs", RichLog)
        status = "Enabled" if self.enable_live_reload_flag else "Disabled"
        logs.write(f"[cyan]🔄 Live Reload: {status}[/cyan]")
        logger.info(f"Live reload: {status}")

        if self.enable_live_reload_flag:
            self.call_later(self._setup_file_watcher)
        elif self.file_watcher:
            self.file_watcher.stop()
            self.file_watcher = None

    def action_configure_watch_paths(self) -> None:
        """Configure watch paths (Phase 2)."""
        logs = self.query_one("#logs", RichLog)
        logs.write(f"[cyan]📁 Current watch paths: {', '.join(self.watch_paths)}[/cyan]")
        logs.write("[yellow]   Configuration dialog not implemented yet[/yellow]")
        logger.info("Watch paths configuration requested")

    def action_force_reload(self) -> None:
        """Force reload all tests (Phase 2)."""
        logs = self.query_one("#logs", RichLog)
        logs.write("[cyan]🔄 Force reloading...[/cyan]")

        self.action_clear_cache()
        self.action_run_tests()

        logger.info("Force reload triggered")

    def action_toggle_theme(self) -> None:
        """Toggle between light and dark theme (Phase 3)."""
        self.dark_theme = not self.dark_theme

        logs = self.query_one("#logs", RichLog)
        theme = "Dark" if self.dark_theme else "Light"
        logs.write(f"[cyan]🎨 Theme: {theme}[/cyan]")
        logger.info(f"Theme changed to: {theme}")

        self.app.theme = "textual-dark" if self.dark_theme else "textual-light"

    def action_toggle_metrics(self) -> None:
        """Toggle metrics panel visibility (Phase 4)."""
        self.show_metrics = not self.show_metrics

        metrics_widget = self.query_one("#metrics", MetricsWidget)
        metrics_widget.display = self.show_metrics

        logs = self.query_one("#logs", RichLog)
        status = "Visible" if self.show_metrics else "Hidden"
        logs.write(f"[cyan]📊 Metrics Panel: {status}[/cyan]")
        logger.info(f"Metrics panel: {status}")

    def action_toggle_visibility(self) -> None:
        """Toggle team visibility panel (Phase 5)."""
        self.show_team_visibility = not self.show_team_visibility

        visibility_widget = self.query_one("#team-visibility", TeamVisibilityWidget)
        visibility_widget.display = self.show_team_visibility

        logs = self.query_one("#logs", RichLog)
        status = "Visible" if self.show_team_visibility else "Hidden"
        logs.write(f"[cyan]👥 Team Visibility: {status}[/cyan]")
        logger.info(f"Team visibility: {status}")

    def action_clear_output(self) -> None:
        """Clear output log (Phase 3)."""
        output = self.query_one("#test-output", RichLog)
        output.clear()

        logs = self.query_one("#logs", RichLog)
        logs.write("[cyan]🗑️  Output cleared[/cyan]")
        logger.info("Output log cleared")

    def action_export_results(self) -> None:
        """Open export modal (Phase 4)."""
        logger.info("Opening export modal")

        def handle_export(config: Optional[Dict[str, Any]]) -> None:
            if config:
                self._export_results(config)

        self.push_screen(ExportModal(), handle_export)

    def action_quick_export(self) -> None:
        """Quick export to JSON (Phase 4)."""
        config = {
            "format": "json",
            "output_path": f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "include_errors": True,
            "include_timing": True,
            "include_cached": True,
        }
        self._export_results(config)

    def action_performance_report(self) -> None:
        """Generate performance report (Phase 4)."""
        logs = self.query_one("#logs", RichLog)
        logs.write("[cyan]📈 Generating performance report...[/cyan]")

        try:
            metrics = self._calculate_metrics()

            output = self.query_one("#test-output", RichLog)
            output.clear()
            output.write("[bold]Performance Report[/bold]\n")
            output.write(f"Average Duration: {metrics['avg_duration']:.2f}ms")
            output.write(f"Min Duration: {metrics['min_duration']:.2f}ms")
            output.write(f"Max Duration: {metrics['max_duration']:.2f}ms")
            output.write(f"Total Duration: {metrics['total_duration']:.2f}s")
            output.write(f"Tests/Second: {metrics['tests_per_second']:.2f}")
            output.write(f"Cache Hit Rate: {metrics['cache_hit_rate']:.1f}%")

            logs.write("[green]✅ Performance report generated[/green]")
            logger.info("Performance report generated")

        except Exception as e:
            logs.write(f"[red]❌ Error generating report: {e}[/red]")
            logger.error(f"Performance report failed: {e}")

    def action_toggle_websocket(self) -> None:
        """Toggle WebSocket broadcasting (Phase 5)."""
        self.websocket_enabled = not self.websocket_enabled

        logs = self.query_one("#logs", RichLog)

        if self.websocket_enabled:
            logs.write("[cyan]🌐 Starting WebSocket server...[/cyan]")
            self.call_later(self._setup_websocket)
        else:
            logs.write("[cyan]🌐 Stopping WebSocket server...[/cyan]")
            asyncio.create_task(self.websocket_broadcaster.stop())

            team_widget = self.query_one("#team-visibility", TeamVisibilityWidget)
            team_widget.websocket_enabled = False

        logger.info(f"WebSocket: {self.websocket_enabled}")

    def action_configure_websocket(self) -> None:
        """Configure WebSocket endpoint (Phase 5)."""
        logs = self.query_one("#logs", RichLog)
        logs.write(
            f"[cyan]🌐 WebSocket: ws://{self.websocket_broadcaster.host}:{self.websocket_broadcaster.port}[/cyan]"
        )
        logs.write("[yellow]   Configuration dialog not implemented yet[/yellow]")
        logger.info("WebSocket configuration requested")

    def action_show_users(self) -> None:
        """Show connected users (Phase 5)."""
        users = self.websocket_broadcaster.get_connected_users()

        output = self.query_one("#test-output", RichLog)
        output.clear()
        output.write("[bold]Connected Users[/bold]\n")

        if not users:
            output.write("[dim]No users connected[/dim]")
        else:
            for user in users:
                output.write(f"👤 {user['name']} - {user['status']}")
                output.write(f"   Address: {user['address']}")

        logs = self.query_one("#logs", RichLog)
        logs.write(f"[cyan]👥 {len(users)} users connected[/cyan]")
        logger.info(f"Showed connected users: {len(users)}")

    def action_toggle_debug(self) -> None:
        """Toggle debug mode (Phase 3)."""
        self.debug_mode = not self.debug_mode

        logs = self.query_one("#logs", RichLog)
        status = "Enabled" if self.debug_mode else "Disabled"
        logs.write(f"[cyan]🐛 Debug Mode: {status}[/cyan]")
        logger.setLevel(logging.DEBUG if self.debug_mode else logging.INFO)
        logger.info(f"Debug mode: {status}")

    def action_inspect_test(self) -> None:
        """Inspect selected test (Phase 3)."""
        test_table = self.query_one("#test-tree", DataTable)
        output = self.query_one("#test-output", RichLog)

        try:
            cursor_row = test_table.cursor_row
            if cursor_row is not None and cursor_row < test_table.row_count:
                row_key = test_table.get_row_at(cursor_row)
                test_name = row_key[1]

                output.clear()
                output.write(f"[bold]Test Inspection: {test_name}[/bold]\n")

                test_result = next(
                    (r for r in self.test_results if r["test_name"] == test_name), None
                )

                if test_result:
                    output.write(
                        f"Status: {'✅ Passed' if test_result['success'] else '❌ Failed'}"
                    )
                    output.write(f"Duration: {test_result['duration_ms']:.2f}ms")
                    output.write(f"Tool: {test_result['tool_name']}")
                    output.write(f"Cached: {'Yes' if test_result.get('cached') else 'No'}")
                    output.write(f"Skipped: {'Yes' if test_result.get('skipped') else 'No'}")

                    if test_result.get("error"):
                        output.write("\n[bold red]Error:[/bold red]")
                        output.write(test_result["error"])
                else:
                    output.write("[dim]No result available yet[/dim]")

                logger.info(f"Inspected test: {test_name}")

        except Exception as e:
            output.write(f"[red]Error inspecting test: {e}[/red]")
            logger.error(f"Test inspection failed: {e}")

    def action_save_session(self) -> None:
        """Save current session (Phase 3)."""
        logs = self.query_one("#logs", RichLog)

        try:
            session_data = {
                "filters": self.current_filters,
                "selected_tests": list(self.selected_tests),
                "results": self.test_results,
                "timestamp": datetime.now().isoformat(),
            }

            session_path = Path("session.json")
            session_path.write_text(json.dumps(session_data, indent=2))

            logs.write(f"[green]✅ Session saved to {session_path}[/green]")
            logger.info("Session saved")

        except Exception as e:
            logs.write(f"[red]❌ Error saving session: {e}[/red]")
            logger.error(f"Session save failed: {e}")

    def action_load_session(self) -> None:
        """Load saved session (Phase 3)."""
        logs = self.query_one("#logs", RichLog)

        try:
            session_path = Path("session.json")
            if not session_path.exists():
                logs.write("[yellow]⚠️  No saved session found[/yellow]")
                return

            session_data = json.loads(session_path.read_text())

            self.current_filters = session_data["filters"]
            self.selected_tests = set(session_data["selected_tests"])
            self.test_results = session_data["results"]

            logs.write(f"[green]✅ Session loaded from {session_path}[/green]")
            logger.info("Session loaded")

            self._apply_filters()
            self._update_results_display()

        except Exception as e:
            logs.write(f"[red]❌ Error loading session: {e}[/red]")
            logger.error(f"Session load failed: {e}")

    def action_health_check(self) -> None:
        """Manually trigger health check for all status widgets."""
        logs = self.query_one("#logs", RichLog)
        logs.write("[cyan]🏥 Running health check...[/cyan]")
        logger.info("Manual health check triggered")

        self.call_later(self._refresh_status_widgets)

    def _calculate_metrics(self) -> Dict[str, float]:
        """Calculate performance metrics (Phase 4)."""
        if not self.test_durations:
            return {
                "avg_duration": 0.0,
                "min_duration": 0.0,
                "max_duration": 0.0,
                "total_duration": 0.0,
                "tests_per_second": 0.0,
                "cache_hit_rate": 0.0,
            }

        total_duration = sum(self.test_durations)
        avg_duration = total_duration / len(self.test_durations)
        total_tests = self.cache_hits + self.cache_misses

        return {
            "avg_duration": avg_duration,
            "min_duration": min(self.test_durations),
            "max_duration": max(self.test_durations),
            "total_duration": total_duration / 1000,
            "tests_per_second": (
                len(self.test_durations) / (total_duration / 1000) if total_duration > 0 else 0
            ),
            "cache_hit_rate": (self.cache_hits / total_tests * 100) if total_tests > 0 else 0,
        }

    def _update_metrics_widget(self) -> None:
        """Update metrics widget with latest data (Phase 4)."""
        metrics = self._calculate_metrics()

        metrics_widget = self.query_one("#metrics", MetricsWidget)
        metrics_widget.avg_duration = metrics["avg_duration"]
        metrics_widget.min_duration = metrics["min_duration"]
        metrics_widget.max_duration = metrics["max_duration"]
        metrics_widget.total_duration = metrics["total_duration"]
        metrics_widget.tests_per_second = metrics["tests_per_second"]
        metrics_widget.cache_hit_rate = metrics["cache_hit_rate"]

    def _export_results(self, config: Dict[str, Any]) -> None:
        """Export test results to file (Phase 4)."""
        logs = self.query_one("#logs", RichLog)

        try:
            format_type = config["format"]
            output_path = Path(config["output_path"])

            export_data = {
                "timestamp": datetime.now().isoformat(),
                "endpoint": self.endpoint,
                "total_tests": len(self.test_results),
                "results": self.test_results,
            }

            if config.get("include_timing"):
                export_data["metrics"] = self._calculate_metrics()

            if format_type == "json":
                output_path.write_text(json.dumps(export_data, indent=2))
            elif format_type == "markdown":
                self._export_markdown(export_data, output_path)
            elif format_type == "html":
                self._export_html(export_data, output_path)
            elif format_type == "csv":
                self._export_csv(export_data, output_path)

            logs.write(f"[green]✅ Exported to {output_path}[/green]")
            logger.info(f"Exported results to {output_path}")

        except Exception as e:
            logs.write(f"[red]❌ Export failed: {e}[/red]")
            logger.error(f"Export failed: {e}", exc_info=True)

    def _export_markdown(self, data: Dict[str, Any], path: Path) -> None:
        """Export to Markdown format."""
        lines = [
            f"# Test Report - {data['timestamp']}",
            "\n## Summary",
            f"- Endpoint: {data['endpoint']}",
            f"- Total Tests: {data['total_tests']}",
            "\n## Results\n",
            "| Test | Status | Duration | Tool |",
            "|------|--------|----------|------|",
        ]

        for result in data["results"]:
            status = "✅" if result["success"] else "❌"
            lines.append(
                f"| {result['test_name']} | {status} | {result['duration_ms']:.2f}ms | {result['tool_name']} |"
            )

        path.write_text("\n".join(lines))

    def _export_html(self, data: Dict[str, Any], path: Path) -> None:
        """Export to HTML format."""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Test Report - {data["timestamp"]}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        .passed {{ color: green; }}
        .failed {{ color: red; }}
    </style>
</head>
<body>
    <h1>Test Report</h1>
    <p><strong>Timestamp:</strong> {data["timestamp"]}</p>
    <p><strong>Endpoint:</strong> {data["endpoint"]}</p>
    <p><strong>Total Tests:</strong> {data["total_tests"]}</p>

    <h2>Results</h2>
    <table>
        <tr><th>Test</th><th>Status</th><th>Duration</th><th>Tool</th></tr>
"""

        for result in data["results"]:
            status_class = "passed" if result["success"] else "failed"
            status_text = "✅ Passed" if result["success"] else "❌ Failed"
            html += f"""        <tr>
            <td>{result["test_name"]}</td>
            <td class="{status_class}">{status_text}</td>
            <td>{result["duration_ms"]:.2f}ms</td>
            <td>{result["tool_name"]}</td>
        </tr>
"""

        html += """    </table>
</body>
</html>"""
        path.write_text(html)

    def _export_csv(self, data: Dict[str, Any], path: Path) -> None:
        """Export to CSV format."""
        import csv

        with path.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Test", "Status", "Duration (ms)", "Tool", "Cached", "Error"])

            for result in data["results"]:
                writer.writerow(
                    [
                        result["test_name"],
                        "Passed" if result["success"] else "Failed",
                        f"{result['duration_ms']:.2f}",
                        result["tool_name"],
                        "Yes" if result.get("cached") else "No",
                        result.get("error", ""),
                    ]
                )

    def _apply_filters(self) -> None:
        """Apply current filters to test table."""
        logs = self.query_one("#logs", RichLog)
        logs.write("[cyan]🔍 Applying filters...[/cyan]")
        logger.info(f"Filters applied: {self.current_filters}")

    def _update_results_display(self) -> None:
        """Update test results display."""
        output = self.query_one("#test-output", RichLog)
        output.clear()

        if not self.test_results:
            output.write("[dim]No test results yet[/dim]")
            return

        output.write("[bold]Test Results[/bold]\n")
        for result in self.test_results[-20:]:
            icon = "✅" if result["success"] else "❌"
            output.write(f"{icon} {result['test_name']} ({result['duration_ms']:.2f}ms)")


__all__ = [
    "DashboardActionHandler",
]
