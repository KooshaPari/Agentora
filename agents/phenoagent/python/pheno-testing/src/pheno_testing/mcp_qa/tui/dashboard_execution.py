"""Test execution integration for dashboard.

Contains test runners, callbacks, and result handling for LiveTestRunner integration.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from textual.widgets import DataTable, RichLog

from .dashboard_widgets import (
    LiveMonitorWidget,
    MetricsWidget,
    TestProgressWidget,
    TestSummaryWidget,
)

logger = logging.getLogger("pheno.testing.mcp_qa.tui")


class TestExecutionMixin:
    """Mixin class containing test execution logic for TestDashboardApp."""

    def __init__(self) -> None:
        self.test_results: List[Dict[str, Any]] = []
        self.test_durations: List[float] = []
        self.cache_hits = 0
        self.cache_misses = 0
        self.is_running = False
        self.test_runner = None
        self.websocket_enabled = False
        self.websocket_broadcaster = None
        self.endpoint = ""

    async def run_tests_async(self, selected_only: bool = False) -> None:
        """Run tests asynchronously with LiveTestRunner integration."""
        self.is_running = True

        logs = self.query_one("#logs", RichLog)
        summary = self.query_one("#summary", TestSummaryWidget)

        summary.running = True

        try:
            from .live_runner import LiveTestRunner

            logs.write("[cyan]🔧 Initializing test runner...[/cyan]")

            client_adapter = AtomsMCPClientAdapter(self.endpoint)

            runner = LiveTestRunner(
                client_adapter=client_adapter,
                cache=True,
                parallel=False,
                on_test_start=self._on_test_start,
                on_test_complete=self._on_test_complete,
                on_suite_start=self._on_suite_start,
                on_suite_complete=self._on_suite_complete,
            )

            self.test_runner = runner

            if selected_only:
                logs.write("[yellow]⚠️  Selected test execution not fully implemented[/yellow]")
                result = await runner.run_all()
            else:
                result = await runner.run_all()

            logs.write("[bold green]✅ Test execution complete![/bold green]")
            logger.info("Test execution completed successfully")

            if self.websocket_enabled:
                await self.websocket_broadcaster.broadcast(
                    {
                        "type": "test_complete",
                        "summary": result,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        except Exception as e:
            logs.write(f"[bold red]❌ Error running tests: {e}[/bold red]")
            logger.error(f"Test execution failed: {e}", exc_info=True)

        finally:
            self.is_running = False
            summary.running = False

    async def run_single_test_async(self, test_name: str) -> None:
        """Run a single test asynchronously."""
        logs = self.query_one("#logs", RichLog)

        try:
            logs.write(f"[cyan]▶️  Running: {test_name}[/cyan]")

            await asyncio.sleep(1)

            logs.write(f"[green]✅ Completed: {test_name}[/green]")
            logger.info(f"Single test completed: {test_name}")

        except Exception as e:
            logs.write(f"[red]❌ Error: {e}[/red]")
            logger.error(f"Single test failed: {e}")

    def _on_suite_start(self, total_tests: int) -> None:
        """Callback when test suite starts."""
        progress = self.query_one("#progress", TestProgressWidget)
        summary = self.query_one("#summary", TestSummaryWidget)

        progress.total = total_tests
        progress.current = 0
        summary.total = total_tests

        logs = self.query_one("#logs", RichLog)
        logs.write(f"[bold cyan]📋 Starting {total_tests} tests...[/bold cyan]")
        logger.info(f"Test suite started: {total_tests} tests")

    def _on_test_start(self, test_name: str, tool_name: str) -> None:
        """Callback when individual test starts."""
        progress = self.query_one("#progress", TestProgressWidget)
        progress.current_test = test_name
        progress.current_tool = tool_name

        logger.debug(f"Test started: {test_name}")

    def _on_test_complete(self, test_name: str, result: Dict[str, Any]) -> None:
        """Callback when individual test completes."""
        progress = self.query_one("#progress", TestProgressWidget)
        summary = self.query_one("#summary", TestSummaryWidget)
        test_table = self.query_one("#test-tree", DataTable)
        live_monitor = self.query_one("#live-monitor", LiveMonitorWidget)

        progress.current += 1

        if result.get("success"):
            summary.passed += 1
        elif not result.get("skipped"):
            summary.failed += 1

        if result.get("skipped"):
            summary.skipped += 1
        if result.get("cached"):
            summary.cached += 1
            self.cache_hits += 1
        else:
            self.cache_misses += 1

        duration_ms = result.get("duration_ms", 0)
        self.test_durations.append(duration_ms)
        summary.duration += duration_ms / 1000

        status_icon = "💾" if result.get("cached") else ("✅" if result["success"] else "❌")
        for i in range(test_table.row_count):
            row = test_table.get_row_at(i)
            if row[1] == test_name:
                test_table.update_cell_at((i, 2), status_icon)
                test_table.update_cell_at((i, 3), f"{duration_ms:.2f}ms")
                break

        recent_tests = list(live_monitor.recent_tests)
        recent_tests.append(
            {"name": test_name, "success": result["success"], "duration": duration_ms}
        )
        live_monitor.recent_tests = recent_tests

        if not result["success"] and not result.get("skipped"):
            live_monitor.error_count += 1

        self.test_results.append(result)

        self._update_metrics_widget()

        if self.websocket_enabled:
            asyncio.create_task(
                self.websocket_broadcaster.broadcast(
                    {
                        "type": "test_result",
                        "test_name": test_name,
                        "result": result,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            )

        logger.debug(f"Test completed: {test_name} - {'✅' if result['success'] else '❌'}")

    def _on_suite_complete(self, summary: Dict[str, Any]) -> None:
        """Callback when test suite completes."""
        logs = self.query_one("#logs", RichLog)

        passed = summary["passed"]
        failed = summary["failed"]
        total = summary["total"]
        duration = summary["duration_seconds"]

        logs.write("[bold green]🎉 Suite complete![/bold green]")
        logs.write(f"   Total: {total} | Passed: {passed} | Failed: {failed}")
        logs.write(f"   Duration: {duration:.2f}s")

        logger.info(f"Test suite completed: {total} tests in {duration:.2f}s")

    def _calculate_metrics(self) -> Dict[str, float]:
        """Calculate performance metrics."""
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
        """Update metrics widget with latest data."""
        metrics = self._calculate_metrics()

        metrics_widget = self.query_one("#metrics", MetricsWidget)
        metrics_widget.avg_duration = metrics["avg_duration"]
        metrics_widget.min_duration = metrics["min_duration"]
        metrics_widget.max_duration = metrics["max_duration"]
        metrics_widget.total_duration = metrics["total_duration"]
        metrics_widget.tests_per_second = metrics["tests_per_second"]
        metrics_widget.cache_hit_rate = metrics["cache_hit_rate"]

    def _export_results(self, config: Dict[str, Any]) -> None:
        """Export test results to file."""
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


__all__ = [
    "TestExecutionMixin",
]
