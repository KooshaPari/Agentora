"""Filter and search widgets for MCP QA TUI.

Interactive filtering and selection widgets:
- FilterDialogWidget: Modal dialog for test filtering
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import (
    Button,
    Checkbox,
    Input,
    Label,
    Static,
)


class FilterDialogWidget(Widget):
    """Modal dialog for test filtering.

    Features:
    - Filter by status
    - Filter by category
    - Filter by name pattern
    - Apply/cancel buttons
    """

    DEFAULT_CSS = """
    FilterDialogWidget {
        align: center middle;
        width: 60;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1;
    }

    FilterDialogWidget Input {
        margin: 1 0;
    }

    FilterDialogWidget Button {
        margin: 1 1;
    }
    """

    def __init__(
        self,
        current_filters: Optional[Dict[str, Any]] = None,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._current_filters = current_filters or {}

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Static("Filter Tests", classes="dialog-title")

        yield Label("Status:")
        yield Checkbox(
            "Passed", id="filter-passed", value=self._current_filters.get("passed", True)
        )
        yield Checkbox(
            "Failed", id="filter-failed", value=self._current_filters.get("failed", True)
        )
        yield Checkbox(
            "Skipped", id="filter-skipped", value=self._current_filters.get("skipped", True)
        )
        yield Checkbox(
            "Pending", id="filter-pending", value=self._current_filters.get("pending", True)
        )

        yield Label("Name Pattern:")
        yield Input(
            placeholder="Filter by name (regex supported)",
            id="filter-pattern",
            value=self._current_filters.get("pattern", ""),
        )

        yield Label("Category:")
        yield Input(
            placeholder="Filter by category",
            id="filter-category",
            value=self._current_filters.get("category", ""),
        )

        with Horizontal():
            yield Button("Apply", variant="primary", id="apply-filter")
            yield Button("Cancel", variant="default", id="cancel-filter")

    @on(Button.Pressed, "#apply-filter")
    def handle_apply(self) -> None:
        """Handle apply button press."""
        filters = {
            "passed": self.query_one("#filter-passed", Checkbox).value,
            "failed": self.query_one("#filter-failed", Checkbox).value,
            "skipped": self.query_one("#filter-skipped", Checkbox).value,
            "pending": self.query_one("#filter-pending", Checkbox).value,
            "pattern": self.query_one("#filter-pattern", Input).value,
            "category": self.query_one("#filter-category", Input).value,
        }
        self.post_message(self.FiltersApplied(filters))

    @on(Button.Pressed, "#cancel-filter")
    def handle_cancel(self) -> None:
        """Handle cancel button press."""
        self.post_message(self.FiltersCancelled())

    class FiltersApplied(Widget.Message):
        """Posted when filters are applied."""

        def __init__(self, filters: Dict[str, Any]) -> None:
            super().__init__()
            self.filters = filters

    class FiltersCancelled(Widget.Message):
        """Posted when filter dialog is cancelled."""

        pass
