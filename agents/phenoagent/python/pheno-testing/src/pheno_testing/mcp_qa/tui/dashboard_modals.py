"""Modal dialogs for MCP test dashboard.

Contains FilterModal, ExportModal, and HelpModal for Phase 3-4 features.
"""

from typing import Any, Dict

from textual.containers import Container, Horizontal, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label, Select, Static

import logging

logger = logging.getLogger("pheno.testing.mcp_qa.tui")


class FilterModal(ModalScreen):
    """Modal dialog for filtering tests (Phase 3)."""

    CSS = """
    FilterModal {
        align: center middle;
    }

    #filter-dialog {
        width: 60;
        height: 25;
        border: thick $background 80%;
        background: $surface;
        padding: 1 2;
    }

    #filter-buttons {
        height: 3;
        align: center middle;
        margin-top: 1;
    }

    Button {
        margin: 0 1;
    }
    """

    def __init__(self, current_filters: Dict[str, Any]):
        super().__init__()
        self.current_filters = current_filters
        self.result_filters = current_filters.copy()

    def compose(self) -> None:
        """Create filter dialog components."""
        with Container(id="filter-dialog"):
            yield Label("[bold]Filter Tests[/bold]", classes="title")

            yield Label("\nTest Status:")
            yield Checkbox(
                "Show Passed", value=self.current_filters.get("show_passed", True), id="show_passed"
            )
            yield Checkbox(
                "Show Failed", value=self.current_filters.get("show_failed", True), id="show_failed"
            )
            yield Checkbox(
                "Show Skipped",
                value=self.current_filters.get("show_skipped", True),
                id="show_skipped",
            )
            yield Checkbox(
                "Show Cached", value=self.current_filters.get("show_cached", True), id="show_cached"
            )

            yield Label("\nSearch Pattern:")
            yield Input(
                placeholder="e.g., entity, test_create",
                value=self.current_filters.get("search", ""),
                id="search",
            )

            yield Label("\nTool Name:")
            yield Input(
                placeholder="e.g., entity_tool",
                value=self.current_filters.get("tool", ""),
                id="tool",
            )

            with Horizontal(id="filter-buttons"):
                yield Button("Apply", variant="primary", id="apply")
                yield Button("Reset", id="reset")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id

        if button_id == "apply":
            self.result_filters["show_passed"] = self.query_one("#show_passed", Checkbox).value
            self.result_filters["show_failed"] = self.query_one("#show_failed", Checkbox).value
            self.result_filters["show_skipped"] = self.query_one("#show_skipped", Checkbox).value
            self.result_filters["show_cached"] = self.query_one("#show_cached", Checkbox).value
            self.result_filters["search"] = self.query_one("#search", Input).value
            self.result_filters["tool"] = self.query_one("#tool", Input).value
            self.dismiss(self.result_filters)

        elif button_id == "reset":
            default_filters = {
                "show_passed": True,
                "show_failed": True,
                "show_skipped": True,
                "show_cached": True,
                "search": "",
                "tool": "",
            }
            self.dismiss(default_filters)

        elif button_id == "cancel":
            self.dismiss(self.current_filters)


class ExportModal(ModalScreen):
    """Modal dialog for exporting test results (Phase 4)."""

    CSS = """
    ExportModal {
        align: center middle;
    }

    #export-dialog {
        width: 60;
        height: 20;
        border: thick $background 80%;
        background: $surface;
        padding: 1 2;
    }

    #export-buttons {
        height: 3;
        align: center middle;
        margin-top: 1;
    }

    Button {
        margin: 0 1;
    }
    """

    def compose(self) -> None:
        """Create export dialog components."""
        with Container(id="export-dialog"):
            yield Label("[bold]Export Test Results[/bold]", classes="title")

            yield Label("\nExport Format:")
            yield Select(
                [("JSON", "json"), ("Markdown", "markdown"), ("HTML", "html"), ("CSV", "csv")],
                value="json",
                id="format",
            )

            yield Label("\nOutput Path:")
            yield Input(
                placeholder="e.g., results/test_report.json",
                value="test_report.json",
                id="output_path",
            )

            yield Label("\nInclude Options:")
            yield Checkbox("Include Full Error Messages", value=True, id="include_errors")
            yield Checkbox("Include Timing Details", value=True, id="include_timing")
            yield Checkbox("Include Cached Results", value=False, id="include_cached")

            with Horizontal(id="export-buttons"):
                yield Button("Export", variant="primary", id="export")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id

        if button_id == "export":
            export_config = {
                "format": self.query_one("#format", Select).value,
                "output_path": self.query_one("#output_path", Input).value,
                "include_errors": self.query_one("#include_errors", Checkbox).value,
                "include_timing": self.query_one("#include_timing", Checkbox).value,
                "include_cached": self.query_one("#include_cached", Checkbox).value,
            }
            self.dismiss(export_config)

        elif button_id == "cancel":
            self.dismiss(None)


class HelpModal(ModalScreen):
    """Modal dialog showing keyboard shortcuts and help (Phase 3)."""

    CSS = """
    HelpModal {
        align: center middle;
    }

    #help-dialog {
        width: 70;
        height: 30;
        border: thick $background 80%;
        background: $surface;
        padding: 1 2;
    }

    #help-content {
        height: 25;
    }
    """

    def compose(self) -> None:
        """Create help dialog components."""
        with Container(id="help-dialog"):
            yield Label(
                "[bold]Atoms MCP Test Dashboard - Keyboard Shortcuts[/bold]", classes="title"
            )

            with ScrollableContainer(id="help-content"):
                help_text = """
[bold cyan]General Commands[/]
  Q, Esc         Quit application
  H, ?           Show this help
  Ctrl+C         Force quit

[bold cyan]Test Execution[/]
  R              Run all tests
  Shift+R        Run selected tests only
  S              Stop running tests
  Space          Toggle test selection
  Enter          Run selected test

[bold cyan]Navigation[/]
  ↑↓←→           Navigate test tree
  Tab            Switch between panels
  Page Up/Down   Scroll output
  Home/End       Jump to top/bottom

[bold cyan]Filtering & Search[/]
  F, /           Open filter dialog
  Ctrl+F         Quick search
  N              Next search result
  Shift+N        Previous search result

[bold cyan]Cache Management[/]
  C              Clear test cache
  Shift+C        Clear cache for selected tool
  O              Clear OAuth cache

[bold cyan]Status Monitoring[/]
  Ctrl+H         Run health check (refresh all status)

[bold cyan]Live Reload (Phase 2)[/]
  L              Toggle live reload
  Shift+L        Configure watch paths
  Ctrl+R         Force reload

[bold cyan]View & Display[/]
  T              Toggle theme (light/dark)
  M              Show/hide metrics panel
  V              Show/hide team visibility
  1-5            Switch to panel 1-5
  Ctrl+L         Clear output log

[bold cyan]Export & Reports (Phase 4)[/]
  E              Export test results
  Shift+E        Quick export to JSON
  P              Generate performance report

[bold cyan]Team & Collaboration (Phase 5)[/]
  W              Toggle WebSocket broadcasting
  Shift+W        Configure WebSocket endpoint
  U              Show connected users

[bold cyan]Advanced[/]
  D              Toggle debug mode
  I              Inspect selected test
  Ctrl+S         Save session
  Ctrl+O         Load session
"""
                yield Static(help_text)

            yield Button("Close", variant="primary", id="close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "close":
            self.dismiss()


__all__ = [
    "FilterModal",
    "ExportModal",
    "HelpModal",
]
