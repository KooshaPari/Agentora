"""Results and display widgets for MCP QA TUI.

Advanced widgets for metrics, results display, and collaboration:
- MetricsDashboardWidget: CPU/memory/network metrics with sparklines
- TimelineWidget: Test execution timeline visualization
- CacheStatsWidget: Cache hit rates and performance
- ExportDialogWidget: Export options for test results
- MultiEndpointWidget: Multi-endpoint comparison
- TeamViewWidget: Team member activity display
- BroadcastWidget: WebSocket status and events
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import (
    Button,
    Checkbox,
    Input,
    Label,
    OptionList,
    Static,
)
from textual.widgets.option_list import Option


class MetricsDashboardWidget(Widget):
    """CPU/memory/network metrics dashboard with sparklines.

    Features:
    - Real-time metric tracking
    - Sparkline charts
    - Threshold alerts
    - Historical data
    """

    DEFAULT_CSS = """
    MetricsDashboardWidget {
        height: auto;
        border: solid $primary;
        padding: 1;
    }
    """

    cpu_usage: reactive[float] = reactive(0.0)
    memory_usage: reactive[float] = reactive(0.0)
    network_sent: reactive[int] = reactive(0)
    network_recv: reactive[int] = reactive(0)

    def __init__(
        self,
        history_size: int = 50,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self.history_size = history_size
        self._cpu_history: List[float] = []
        self._memory_history: List[float] = []

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Static(id="metrics-content")

    def watch_cpu_usage(self, usage: float) -> None:
        """React to CPU usage change."""
        self._cpu_history.append(usage)
        if len(self._cpu_history) > self.history_size:
            self._cpu_history.pop(0)
        self._update_display()

    def watch_memory_usage(self, usage: float) -> None:
        """React to memory usage change."""
        self._memory_history.append(usage)
        if len(self._memory_history) > self.history_size:
            self._memory_history.pop(0)
        self._update_display()

    def watch_network_sent(self, sent: int) -> None:
        """React to network sent change."""
        self._update_display()

    def watch_network_recv(self, recv: int) -> None:
        """React to network received change."""
        self._update_display()

    def _update_display(self) -> None:
        """Update the metrics display."""
        content = self.query_one("#metrics-content", Static)

        table = Table(title="System Metrics", show_header=True)
        table.add_column("Metric", style="bold")
        table.add_column("Current", justify="right")
        table.add_column("Trend", justify="center")

        cpu_sparkline = self._generate_sparkline(self._cpu_history)
        cpu_color = "red" if self.cpu_usage > 80 else "yellow" if self.cpu_usage > 50 else "green"
        table.add_row(
            "CPU Usage",
            f"[{cpu_color}]{self.cpu_usage:.1f}%[/{cpu_color}]",
            cpu_sparkline,
        )

        mem_sparkline = self._generate_sparkline(self._memory_history)
        mem_color = (
            "red" if self.memory_usage > 80 else "yellow" if self.memory_usage > 50 else "green"
        )
        table.add_row(
            "Memory Usage",
            f"[{mem_color}]{self.memory_usage:.1f}%[/{mem_color}]",
            mem_sparkline,
        )

        table.add_row("Network Sent", self._format_bytes(self.network_sent), "")
        table.add_row("Network Recv", self._format_bytes(self.network_recv), "")

        content.update(table)

    def _generate_sparkline(self, data: List[float]) -> str:
        """Generate a simple ASCII sparkline."""
        if not data:
            return ""

        chars = "▁▂▃▄▅▆▇█"

        min_val = min(data)
        max_val = max(data)
        range_val = max_val - min_val or 1

        sparkline = ""
        for value in data[-20:]:
            normalized = (value - min_val) / range_val
            index = int(normalized * (len(chars) - 1))
            sparkline += chars[index]

        return sparkline

    def _format_bytes(self, bytes_val: int) -> str:
        """Format bytes to human-readable string."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if bytes_val < 1024:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024
        return f"{bytes_val:.2f} PB"


class TimelineWidget(Widget):
    """Test execution timeline visualization.

    Features:
    - Chronological test execution
    - Duration bars
    - Parallel execution tracking
    - Interactive timeline
    """

    DEFAULT_CSS = """
    TimelineWidget {
        height: auto;
        border: solid $primary;
        padding: 1;
    }

    TimelineWidget VerticalScroll {
        height: 100%;
    }
    """

    test_events: reactive[List[Dict[str, Any]]] = reactive(list, layout=True)

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with VerticalScroll():
            yield Static(id="timeline-content")

    def watch_test_events(self, events: List[Dict[str, Any]]) -> None:
        """React to test events change."""
        self._update_display()

    def add_event(self, test_name: str, event_type: str, timestamp: datetime) -> None:
        """Add a timeline event.

        Args:
            test_name: Name of the test
            event_type: Type of event (start, end, error)
            timestamp: Event timestamp
        """
        self.test_events = self.test_events + [
            {
                "test_name": test_name,
                "event_type": event_type,
                "timestamp": timestamp,
            }
        ]

    def _update_display(self) -> None:
        """Update the timeline display."""
        content = self.query_one("#timeline-content", Static)

        if not self.test_events:
            content.update("No test events yet")
            return

        test_timelines: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for event in self.test_events:
            test_timelines[event["test_name"]].append(event)

        text = Text()

        for test_name, events in sorted(test_timelines.items()):
            start_event = next((e for e in events if e["event_type"] == "start"), None)
            end_event = next((e for e in events if e["event_type"] == "end"), None)

            if start_event and end_event:
                duration = (end_event["timestamp"] - start_event["timestamp"]).total_seconds()
                bar_length = int(duration * 10)

                time_str = start_event["timestamp"].strftime("%H:%M:%S")
                text.append(f"[{time_str}] ", style="dim")
                text.append(test_name, style="bold")
                text.append(" ")
                text.append("█" * min(bar_length, 50), style="cyan")
                text.append(f" {duration:.2f}s\n")

        content.update(Panel(text, title="Timeline"))


class CacheStatsWidget(Widget):
    """Cache hit rates and performance statistics.

    Features:
    - Hit/miss ratios
    - Cache size tracking
    - Performance metrics
    - Eviction statistics
    """

    DEFAULT_CSS = """
    CacheStatsWidget {
        height: auto;
        border: solid $primary;
        padding: 1;
    }
    """

    cache_hits: reactive[int] = reactive(0)
    cache_misses: reactive[int] = reactive(0)
    cache_size: reactive[int] = reactive(0)
    cache_max_size: reactive[int] = reactive(1000)
    evictions: reactive[int] = reactive(0)

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Static(id="cache-content")

    def watch_cache_hits(self, hits: int) -> None:
        """React to cache hits change."""
        self._update_display()

    def watch_cache_misses(self, misses: int) -> None:
        """React to cache misses change."""
        self._update_display()

    def watch_cache_size(self, size: int) -> None:
        """React to cache size change."""
        self._update_display()

    def watch_evictions(self, evictions: int) -> None:
        """React to evictions change."""
        self._update_display()

    def _update_display(self) -> None:
        """Update the cache stats display."""
        content = self.query_one("#cache-content", Static)

        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0
        fill_rate = (self.cache_size / self.cache_max_size * 100) if self.cache_max_size > 0 else 0

        table = Table(title="Cache Statistics", show_header=False)
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        table.add_row("Cache Hits", f"[green]{self.cache_hits}[/green]")
        table.add_row("Cache Misses", f"[red]{self.cache_misses}[/red]")
        table.add_row("Hit Rate", f"{hit_rate:.2f}%")
        table.add_row("Cache Size", f"{self.cache_size} / {self.cache_max_size}")
        table.add_row("Fill Rate", f"{fill_rate:.1f}%")
        table.add_row("Evictions", str(self.evictions))

        content.update(table)


class ExportDialogWidget(Widget):
    """Export options dialog for test results.

    Features:
    - Multiple export formats
    - Output destination selection
    - Format-specific options
    - Preview capability
    """

    DEFAULT_CSS = """
    ExportDialogWidget {
        align: center middle;
        width: 60;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1;
    }

    ExportDialogWidget Input {
        margin: 1 0;
    }

    ExportDialogWidget Button {
        margin: 1 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Static("Export Test Results", classes="dialog-title")

        yield Label("Format:")
        yield OptionList(
            Option("HTML Report", id="html"),
            Option("JSON Data", id="json"),
            Option("CSV Summary", id="csv"),
            Option("Screenshot", id="screenshot"),
            id="format-list",
        )

        yield Label("Output Path:")
        yield Input(
            placeholder="Path to save export",
            id="output-path",
            value="./test-results",
        )

        yield Label("Options:")
        yield Checkbox("Include logs", id="include-logs", value=True)
        yield Checkbox("Include screenshots", id="include-screenshots", value=False)
        yield Checkbox("Include metrics", id="include-metrics", value=True)

        with Horizontal():
            yield Button("Export", variant="primary", id="export-button")
            yield Button("Cancel", variant="default", id="cancel-export")

    @on(Button.Pressed, "#export-button")
    def handle_export(self) -> None:
        """Handle export button press."""
        selected_format = None
        format_list = self.query_one("#format-list", OptionList)
        if format_list.highlighted is not None:
            option = format_list.get_option_at_index(format_list.highlighted)
            selected_format = option.id if option else None

        export_options = {
            "format_type": selected_format,
            "output_path": self.query_one("#output-path", Input).value,
            "include_logs": self.query_one("#include-logs", Checkbox).value,
            "include_screenshots": self.query_one("#include-screenshots", Checkbox).value,
            "include_metrics": self.query_one("#include-metrics", Checkbox).value,
        }
        self.post_message(self.ExportRequested(export_options))

    @on(Button.Pressed, "#cancel-export")
    def handle_cancel(self) -> None:
        """Handle cancel button press."""
        self.post_message(self.ExportCancelled())

    class ExportRequested(Widget.Message):
        """Posted when export is requested."""

        def __init__(self, options: Dict[str, Any]) -> None:
            super().__init__()
            self.options = options

    class ExportCancelled(Widget.Message):
        """Posted when export is cancelled."""

        pass


class MultiEndpointWidget(Widget):
    """Compare test results across multiple endpoints.

    Features:
    - Side-by-side comparison
    - Diff highlighting
    - Per-endpoint statistics
    - Sync/async execution
    """

    DEFAULT_CSS = """
    MultiEndpointWidget {
        height: auto;
        border: solid $primary;
        padding: 1;
    }

    MultiEndpointWidget VerticalScroll {
        height: 100%;
    }
    """

    endpoint_results: reactive[Dict[str, Dict[str, Any]]] = reactive(dict, layout=True)

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with VerticalScroll():
            yield Static(id="endpoint-content")

    def watch_endpoint_results(self, results: Dict[str, Dict[str, Any]]) -> None:
        """React to endpoint results change."""
        self._update_display()

    def update_endpoint(self, endpoint: str, results: Dict[str, Any]) -> None:
        """Update results for a specific endpoint.

        Args:
            endpoint: Endpoint identifier
            results: Test results for this endpoint
        """
        current = self.endpoint_results.copy()
        current[endpoint] = results
        self.endpoint_results = current

    def _update_display(self) -> None:
        """Update the multi-endpoint display."""
        content = self.query_one("#endpoint-content", Static)

        if not self.endpoint_results:
            content.update("No endpoint results yet")
            return

        table = Table(title="Multi-Endpoint Comparison", show_header=True)
        table.add_column("Metric", style="bold")

        for endpoint in sorted(self.endpoint_results.keys()):
            table.add_column(endpoint, justify="center")

        metrics = ["total", "passed", "failed", "skipped", "avg_duration"]

        for metric in metrics:
            row = [metric.replace("_", " ").title()]

            for endpoint in sorted(self.endpoint_results.keys()):
                results = self.endpoint_results[endpoint]
                value = results.get(metric, 0)

                if metric == "avg_duration":
                    row.append(f"{value:.3f}s")
                elif metric == "passed":
                    row.append(f"[green]{value}[/green]")
                elif metric == "failed":
                    row.append(f"[red]{value}[/red]")
                elif metric == "skipped":
                    row.append(f"[yellow]{value}[/yellow]")
                else:
                    row.append(str(value))

            table.add_row(*row)

        content.update(table)


class TeamViewWidget(Widget):
    """Show active team members and their test sessions.

    Features:
    - Online user list
    - Current test activity
    - User avatars/indicators
    - Real-time updates
    """

    DEFAULT_CSS = """
    TeamViewWidget {
        height: auto;
        border: solid $primary;
        padding: 1;
    }
    """

    team_members: reactive[List[Dict[str, Any]]] = reactive(list, layout=True)

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Static(id="team-content")

    def watch_team_members(self, members: List[Dict[str, Any]]) -> None:
        """React to team members change."""
        self._update_display()

    def add_member(self, member_id: str, name: str, status: str = "online") -> None:
        """Add or update a team member.

        Args:
            member_id: Unique member identifier
            name: Display name
            status: Member status (online, away, testing)
        """
        current = self.team_members.copy()

        for member in current:
            if member["id"] == member_id:
                member["name"] = name
                member["status"] = status
                member["last_seen"] = datetime.now()
                break
        else:
            current.append(
                {
                    "id": member_id,
                    "name": name,
                    "status": status,
                    "last_seen": datetime.now(),
                }
            )

        self.team_members = current

    def remove_member(self, member_id: str) -> None:
        """Remove a team member.

        Args:
            member_id: Unique member identifier
        """
        self.team_members = [m for m in self.team_members if m["id"] != member_id]

    def _update_display(self) -> None:
        """Update the team view display."""
        content = self.query_one("#team-content", Static)

        if not self.team_members:
            content.update("No team members online")
            return

        table = Table(title="Team Activity", show_header=True)
        table.add_column("Status", width=8)
        table.add_column("Name", style="bold")
        table.add_column("Last Seen", justify="right")

        for member in self.team_members:
            status = member.get("status", "offline")
            if status == "online":
                status_icon = "[green]●[/green]"
            elif status == "away":
                status_icon = "[yellow]●[/yellow]"
            elif status == "testing":
                status_icon = "[blue]●[/blue]"
            else:
                status_icon = "[dim]●[/dim]"

            last_seen = member.get("last_seen", datetime.now())
            time_diff = (datetime.now() - last_seen).total_seconds()

            if time_diff < 60:
                time_str = "just now"
            elif time_diff < 3600:
                time_str = f"{int(time_diff / 60)}m ago"
            else:
                time_str = f"{int(time_diff / 3600)}h ago"

            table.add_row(status_icon, member.get("name", "Unknown"), time_str)

        content.update(table)


class BroadcastWidget(Widget):
    """WebSocket status and broadcast events.

    Features:
    - Connection status
    - Event stream
    - Message history
    - Reconnection handling
    """

    DEFAULT_CSS = """
    BroadcastWidget {
        height: auto;
        border: solid $primary;
        padding: 1;
    }

    BroadcastWidget VerticalScroll {
        height: 100%;
    }
    """

    is_connected: reactive[bool] = reactive(False)
    connection_url: reactive[str] = reactive("")
    events: reactive[List[Dict[str, Any]]] = reactive(list, layout=True)

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Static(id="connection-status")
        with VerticalScroll():
            yield Static(id="broadcast-events")

    def watch_is_connected(self, connected: bool) -> None:
        """React to connection status change."""
        self._update_status()

    def watch_connection_url(self, url: str) -> None:
        """React to connection URL change."""
        self._update_status()

    def watch_events(self, events: List[Dict[str, Any]]) -> None:
        """React to events change."""
        self._update_events()

    def add_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Add a broadcast event.

        Args:
            event_type: Type of event
            data: Event data
        """
        self.events = self.events + [
            {
                "type": event_type,
                "data": data,
                "timestamp": datetime.now(),
            }
        ]

    def _update_status(self) -> None:
        """Update the connection status display."""
        status = self.query_one("#connection-status", Static)

        if self.is_connected:
            status_text = Text()
            status_text.append("● ", style="green")
            status_text.append("Connected ", style="bold green")
            if self.connection_url:
                status_text.append(f"to {self.connection_url}", style="dim")
        else:
            status_text = Text()
            status_text.append("● ", style="red")
            status_text.append("Disconnected", style="bold red")

        status.update(status_text)

    def _update_events(self) -> None:
        """Update the events display."""
        events_content = self.query_one("#broadcast-events", Static)

        if not self.events:
            events_content.update("No events yet")
            return

        text = Text()

        for event in self.events[-50:]:
            timestamp = event["timestamp"].strftime("%H:%M:%S")
            event_type = event["type"]

            text.append(f"[{timestamp}] ", style="dim")
            text.append(f"{event_type}\n", style="cyan")

            for key, value in event["data"].items():
                text.append(f"  {key}: {value}\n", style="dim")

        events_content.update(text)
