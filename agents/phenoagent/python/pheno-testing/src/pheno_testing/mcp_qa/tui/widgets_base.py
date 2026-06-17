"""Base widget classes for MCP QA TUI.

Core widgets for test display and monitoring:
- TestTreeWidget: Hierarchical test organization with Tree view
- TestDetailWidget: Detailed test output with syntax highlighting
- SummaryStatsWidget: Real-time test statistics
- ProgressBarWidget: Multi-level progress tracking
- LogStreamWidget: Live log streaming
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static, Tree


class TestTreeWidget(Widget):
    """Collapsible tree view of tests organized by category with DataTable display.

    Features:
    - Hierarchical organization by category
    - Expandable/collapsible nodes
    - Color-coded by test status
    - Click to view details
    """

    DEFAULT_CSS = """
    TestTreeWidget {
        height: auto;
        border: solid $primary;
    }

    TestTreeWidget Tree {
        background: $surface;
    }
    """

    selected_test: reactive[Optional[str]] = reactive(None)
    test_data: reactive[Dict[str, Any]] = reactive(dict, layout=True)

    def __init__(
        self,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._test_results: Dict[str, Dict[str, Any]] = {}
        self._categories: Dict[str, List[str]] = defaultdict(list)

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Tree("Test Suite", id="test-tree")

    def update_tests(self, test_results: Dict[str, Dict[str, Any]]) -> None:
        """Update the tree with new test results.

        Args:
            test_results: Dictionary mapping test names to their results
        """
        self._test_results = test_results
        self._organize_by_category()
        self._rebuild_tree()

    def _organize_by_category(self) -> None:
        """Organize tests by category."""
        self._categories.clear()
        for test_name, result in self._test_results.items():
            category = result.get("category", "Uncategorized")
            self._categories[category].append(test_name)

    def _rebuild_tree(self) -> None:
        """Rebuild the entire tree structure."""
        tree = self.query_one("#test-tree", Tree)
        tree.clear()
        tree.label = f"Test Suite ({len(self._test_results)} tests)"

        for category, tests in sorted(self._categories.items()):
            category_node = tree.root.add(
                f"[bold]{category}[/bold] ({len(tests)} tests)",
                expand=True,
            )

            for test_name in sorted(tests):
                result = self._test_results[test_name]
                status = result.get("status", "pending")

                if status == "passed":
                    icon = "[green]✓[/green]"
                elif status == "failed":
                    icon = "[red]✗[/red]"
                elif status == "skipped":
                    icon = "[yellow]⊘[/yellow]"
                else:
                    icon = "[dim]○[/dim]"

                duration = result.get("duration", 0)
                label = f"{icon} {test_name} ({duration:.2f}s)"

                category_node.add_leaf(label, data={"test_name": test_name})

    @on(Tree.NodeSelected)
    def handle_selection(self, event: Tree.NodeSelected) -> None:
        """Handle tree node selection."""
        if event.node.data:
            test_name = event.node.data.get("test_name")
            if test_name:
                self.selected_test = test_name
                self.post_message(self.TestSelected(test_name))

    class TestSelected(Widget.Message):
        """Posted when a test is selected."""

        def __init__(self, test_name: str) -> None:
            super().__init__()
            self.test_name = test_name


class TestDetailWidget(Widget):
    """Detailed test output viewer with syntax highlighting.

    Features:
    - Syntax-highlighted output
    - Stack traces with line numbers
    - Test metadata display
    - Error highlighting
    """

    DEFAULT_CSS = """
    TestDetailWidget {
        height: auto;
        border: solid $primary;
        padding: 1;
    }

    TestDetailWidget VerticalScroll {
        height: 100%;
    }
    """

    test_data: reactive[Optional[Dict[str, Any]]] = reactive(None, layout=True)

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with VerticalScroll():
            yield Static(id="detail-content")

    def watch_test_data(self, test_data: Optional[Dict[str, Any]]) -> None:
        """React to test data changes."""
        if test_data:
            self._update_display(test_data)

    def _update_display(self, test_data: Dict[str, Any]) -> None:
        """Update the detail display with test data."""
        content = self.query_one("#detail-content", Static)

        renderables = []

        test_name = test_data.get("name", "Unknown Test")
        status = test_data.get("status", "pending")

        if status == "passed":
            status_text = "[green]PASSED[/green]"
        elif status == "failed":
            status_text = "[red]FAILED[/red]"
        elif status == "skipped":
            status_text = "[yellow]SKIPPED[/yellow]"
        else:
            status_text = "[dim]PENDING[/dim]"

        header = Text()
        header.append(f"{test_name}\n", style="bold")
        header.append(f"Status: {status_text}\n")
        header.append(f"Duration: {test_data.get('duration', 0):.3f}s\n")
        header.append(f"Category: {test_data.get('category', 'N/A')}\n")

        renderables.append(Panel(header, title="Test Info"))

        if output := test_data.get("output"):
            renderables.append(
                Panel(
                    Syntax(output, "python", theme="monokai", line_numbers=True),
                    title="Output",
                )
            )

        if error := test_data.get("error"):
            error_text = Text()
            error_text.append(f"Error Type: {error.get('type', 'Unknown')}\n", style="bold red")
            error_text.append(f"Message: {error.get('message', 'No message')}\n", style="red")

            if traceback := error.get("traceback"):
                error_text.append("\nTraceback:\n", style="bold")
                renderables.append(Panel(error_text, title="Error", border_style="red"))
                renderables.append(
                    Panel(
                        Syntax(traceback, "python", theme="monokai", line_numbers=True),
                        title="Stack Trace",
                        border_style="red",
                    )
                )
            else:
                renderables.append(Panel(error_text, title="Error", border_style="red"))

        if metadata := test_data.get("metadata"):
            meta_table = Table(show_header=False)
            meta_table.add_column("Key", style="cyan")
            meta_table.add_column("Value")

            for key, value in metadata.items():
                meta_table.add_row(str(key), str(value))

            renderables.append(Panel(meta_table, title="Metadata"))

        content.update("\n".join(str(r) for r in renderables))


class SummaryStatsWidget(Widget):
    """Live-updating summary statistics with reactive attributes.

    Features:
    - Real-time test counts
    - Pass/fail rates
    - Average duration
    - Color-coded metrics
    """

    DEFAULT_CSS = """
    SummaryStatsWidget {
        height: auto;
        border: solid $primary;
        padding: 1;
    }
    """

    total_tests: reactive[int] = reactive(0)
    passed: reactive[int] = reactive(0)
    failed: reactive[int] = reactive(0)
    skipped: reactive[int] = reactive(0)
    running: reactive[int] = reactive(0)
    avg_duration: reactive[float] = reactive(0.0)

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Static(id="stats-content")

    def watch_total_tests(self, total: int) -> None:
        """React to total tests change."""
        self._update_display()

    def watch_passed(self, passed: int) -> None:
        """React to passed tests change."""
        self._update_display()

    def watch_failed(self, failed: int) -> None:
        """React to failed tests change."""
        self._update_display()

    def watch_skipped(self, skipped: int) -> None:
        """React to skipped tests change."""
        self._update_display()

    def watch_running(self, running: int) -> None:
        """React to running tests change."""
        self._update_display()

    def watch_avg_duration(self, avg: float) -> None:
        """React to average duration change."""
        self._update_display()

    def _update_display(self) -> None:
        """Update the statistics display."""
        content = self.query_one("#stats-content", Static)

        total = self.total_tests or 1
        pass_rate = (self.passed / total) * 100
        fail_rate = (self.failed / total) * 100

        table = Table(show_header=False, box=None)
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        table.add_row("Total Tests", str(self.total_tests))
        table.add_row("Passed", f"[green]{self.passed}[/green] ({pass_rate:.1f}%)")
        table.add_row("Failed", f"[red]{self.failed}[/red] ({fail_rate:.1f}%)")
        table.add_row("Skipped", f"[yellow]{self.skipped}[/yellow]")
        table.add_row("Running", f"[blue]{self.running}[/blue]")
        table.add_row("Avg Duration", f"{self.avg_duration:.3f}s")

        content.update(table)


class ProgressBarWidget(Widget):
    """Multi-level progress tracking (overall + per-category).

    Features:
    - Overall progress bar
    - Per-category progress
    - Real-time updates
    - Color-coded by status
    """

    DEFAULT_CSS = """
    ProgressBarWidget {
        height: auto;
        border: solid $primary;
        padding: 1;
    }
    """

    total: reactive[int] = reactive(0)
    completed: reactive[int] = reactive(0)
    category_progress: reactive[Dict[str, Tuple[int, int]]] = reactive(dict, layout=True)

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Static(id="progress-content")

    def watch_total(self, total: int) -> None:
        """React to total change."""
        self._update_display()

    def watch_completed(self, completed: int) -> None:
        """React to completed change."""
        self._update_display()

    def watch_category_progress(self, progress: Dict[str, Tuple[int, int]]) -> None:
        """React to category progress change."""
        self._update_display()

    def _update_display(self) -> None:
        """Update the progress display."""
        content = self.query_one("#progress-content", Static)

        progress_display = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        )

        progress_display.add_task(
            "Overall",
            total=self.total or 1,
            completed=self.completed,
        )

        for category, (completed, total) in sorted(self.category_progress.items()):
            progress_display.add_task(
                f"  {category}",
                total=total or 1,
                completed=completed,
            )

        content.update(progress_display)


class LogStreamWidget(Widget):
    """Live log output stream with auto-scroll.

    Features:
    - Real-time log streaming
    - Auto-scroll to latest
    - Log level filtering
    - Color-coded by level
    """

    DEFAULT_CSS = """
    LogStreamWidget {
        height: auto;
        border: solid $primary;
    }

    LogStreamWidget VerticalScroll {
        height: 100%;
    }
    """

    max_lines: int = 1000
    auto_scroll: reactive[bool] = reactive(True)

    def __init__(
        self,
        max_lines: int = 1000,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self.max_lines = max_lines
        self._logs: List[Tuple[datetime, str, str]] = []

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with VerticalScroll(id="log-scroll"):
            yield Static(id="log-content")

    def add_log(self, level: str, message: str) -> None:
        """Add a log message.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
        """
        timestamp = datetime.now()
        self._logs.append((timestamp, level, message))

        if len(self._logs) > self.max_lines:
            self._logs = self._logs[-self.max_lines :]

        self._update_display()

    def clear_logs(self) -> None:
        """Clear all logs."""
        self._logs.clear()
        self._update_display()

    def _update_display(self) -> None:
        """Update the log display."""
        content = self.query_one("#log-content", Static)

        log_text = Text()

        for timestamp, level, message in self._logs:
            time_str = timestamp.strftime("%H:%M:%S.%f")[:-3]

            if level == "ERROR" or level == "CRITICAL":
                style = "red"
            elif level == "WARNING":
                style = "yellow"
            elif level == "INFO":
                style = "green"
            else:
                style = "dim"

            log_text.append(f"[{time_str}] ", style="dim")
            log_text.append(f"{level:8} ", style=style)
            log_text.append(f"{message}\n")

        content.update(log_text)

        if self.auto_scroll:
            scroll = self.query_one("#log-scroll", VerticalScroll)
            scroll.scroll_end(animate=False)
