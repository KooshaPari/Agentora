"""Test-related widgets for MCP QA TUI.

Interactive widgets for test selection and command execution:
- TestSelectorWidget: Multi-select tests with checkboxes
- CommandPaletteWidget: Quick action search and execution
- FileWatcherWidget: File watching for live reload
- ReloadIndicatorWidget: Reload status indicator
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from rich.panel import Panel
from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import (
    Button,
    Checkbox,
    Input,
    OptionList,
    Static,
)
from textual.widgets.option_list import Option


class FileWatcherWidget(Widget):
    """Display watched files and recent changes.

    Features:
    - List of watched files/directories
    - Recent change notifications
    - File status indicators
    - Click to focus on file
    """

    DEFAULT_CSS = """
    FileWatcherWidget {
        height: auto;
        border: solid $primary;
        padding: 1;
    }
    """

    watched_paths: reactive[List[Path]] = reactive(list, layout=True)
    recent_changes: reactive[List[tuple[datetime, Path, str]]] = reactive(list, layout=True)

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Static(id="watcher-content")

    def watch_watched_paths(self, paths: List[Path]) -> None:
        """React to watched paths change."""
        self._update_display()

    def watch_recent_changes(self, changes: List[tuple[datetime, Path, str]]) -> None:
        """React to recent changes."""
        self._update_display()

    def add_change(self, path: Path, event_type: str) -> None:
        """Add a file change event.

        Args:
            path: Path to changed file
            event_type: Type of change (modified, created, deleted)
        """
        timestamp = datetime.now()
        self.recent_changes = [(timestamp, path, event_type)] + self.recent_changes[:19]

    def _update_display(self) -> None:
        """Update the watcher display."""
        content = self.query_one("#watcher-content", Static)

        text = Text()

        text.append("Watched Paths:\n", style="bold")
        for path in self.watched_paths:
            text.append(f"  📁 {path}\n", style="cyan")

        text.append("\n")

        text.append("Recent Changes:\n", style="bold")
        for timestamp, path, event_type in self.recent_changes[:10]:
            time_str = timestamp.strftime("%H:%M:%S")

            if event_type == "created":
                icon = "[green]+[/green]"
            elif event_type == "deleted":
                icon = "[red]-[/red]"
            else:
                icon = "[yellow]~[/yellow]"

            text.append(f"  [{time_str}] {icon} {path.name}\n")

        content.update(Panel(text, title="File Watcher"))


class ReloadIndicatorWidget(Widget):
    """Visual indicator when reloading tests.

    Features:
    - Animated reload indicator
    - Reload status messages
    - Progress feedback
    - Color-coded states
    """

    DEFAULT_CSS = """
    ReloadIndicatorWidget {
        height: 3;
        border: solid $primary;
        padding: 1;
    }
    """

    is_reloading: reactive[bool] = reactive(False)
    reload_message: reactive[str] = reactive("")

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Static(id="reload-content")

    def watch_is_reloading(self, reloading: bool) -> None:
        """React to reload state change."""
        self._update_display()

    def watch_reload_message(self, message: str) -> None:
        """React to reload message change."""
        self._update_display()

    def _update_display(self) -> None:
        """Update the reload indicator."""
        content = self.query_one("#reload-content", Static)

        if self.is_reloading:
            text = Text()
            text.append("🔄 ", style="bold blue")
            text.append("Reloading... ", style="bold")
            if self.reload_message:
                text.append(self.reload_message, style="dim")
            content.update(text)
        else:
            content.update("")


class TestSelectorWidget(Widget):
    """Multi-select tests with checkboxes.

    Features:
    - Checkbox list of all tests
    - Select all/none
    - Filter integration
    - Bulk actions
    """

    DEFAULT_CSS = """
    TestSelectorWidget {
        height: auto;
        border: solid $primary;
        padding: 1;
    }

    TestSelectorWidget VerticalScroll {
        height: 100%;
    }
    """

    available_tests: reactive[List[str]] = reactive(list, layout=True)
    selected_tests: reactive[Set[str]] = reactive(set)

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with Vertical():
            with Horizontal():
                yield Button("Select All", id="select-all", variant="primary")
                yield Button("Select None", id="select-none", variant="default")

            with VerticalScroll():
                yield Container(id="test-checkboxes")

    def watch_available_tests(self, tests: List[str]) -> None:
        """React to available tests change."""
        self._rebuild_checkboxes()

    def _rebuild_checkboxes(self) -> None:
        """Rebuild the checkbox list."""
        container = self.query_one("#test-checkboxes", Container)
        container.remove_children()

        for test_name in self.available_tests:
            checkbox = Checkbox(
                test_name,
                value=test_name in self.selected_tests,
                id=f"test-{test_name}",
            )
            container.mount(checkbox)

    @on(Button.Pressed, "#select-all")
    def handle_select_all(self) -> None:
        """Select all tests."""
        self.selected_tests = set(self.available_tests)
        for checkbox in self.query(Checkbox):
            checkbox.value = True

    @on(Button.Pressed, "#select-none")
    def handle_select_none(self) -> None:
        """Deselect all tests."""
        self.selected_tests = set()
        for checkbox in self.query(Checkbox):
            checkbox.value = False

    @on(Checkbox.Changed)
    def handle_checkbox_change(self, event: Checkbox.Changed) -> None:
        """Handle individual checkbox changes."""
        test_name = event.checkbox.label.plain
        if event.checkbox.value:
            self.selected_tests = self.selected_tests | {test_name}
        else:
            self.selected_tests = self.selected_tests - {test_name}


class CommandPaletteWidget(Widget):
    """Quick action search and execution.

    Features:
    - Fuzzy search for commands
    - Keyboard shortcuts
    - Recent commands
    - Command categories
    """

    DEFAULT_CSS = """
    CommandPaletteWidget {
        align: center top;
        width: 80;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1;
    }

    CommandPaletteWidget Input {
        margin: 1 0;
    }

    CommandPaletteWidget OptionList {
        height: 20;
    }
    """

    def __init__(
        self,
        commands: Optional[List[Dict[str, Any]]] = None,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._commands = commands or []
        self._filtered_commands = self._commands.copy()

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Static("Command Palette", classes="dialog-title")
        yield Input(placeholder="Type to search commands...", id="command-search")
        yield OptionList(id="command-list")

    def on_mount(self) -> None:
        """Handle mount event."""
        self._update_command_list()

    @on(Input.Changed, "#command-search")
    def handle_search(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        query = event.value.lower()

        if not query:
            self._filtered_commands = self._commands.copy()
        else:
            self._filtered_commands = [
                cmd
                for cmd in self._commands
                if query in cmd.get("name", "").lower()
                or query in cmd.get("description", "").lower()
            ]

        self._update_command_list()

    def _update_command_list(self) -> None:
        """Update the command list."""
        option_list = self.query_one("#command-list", OptionList)
        option_list.clear_options()

        for cmd in self._filtered_commands:
            name = cmd.get("name", "Unknown")
            description = cmd.get("description", "")
            shortcut = cmd.get("shortcut", "")

            label = f"{name}"
            if shortcut:
                label += f" [{shortcut}]"
            if description:
                label += f" - {description}"

            option_list.add_option(Option(label, id=name))

    @on(OptionList.OptionSelected, "#command-list")
    def handle_command_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle command selection."""
        if event.option_id:
            self.post_message(self.CommandSelected(str(event.option_id)))

    class CommandSelected(Widget.Message):
        """Posted when a command is selected."""

        def __init__(self, command_id: str) -> None:
            super().__init__()
            self.command_id = command_id
