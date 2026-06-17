"""Generic Status Panel Component.

Reusable status panel for displaying key-value data.
"""

from typing import Any, Dict, List

try:
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from textual.widgets import Static

    HAS_TEXTUAL = True
except ImportError:
    HAS_TEXTUAL = False
    Static = object


class GenericStatusPanel(Static if HAS_TEXTUAL else object):
    """Generic status panel widget.

    Displays key-value pairs in a formatted panel. Fully reusable across projects.
    """

    def __init__(self, title: str, fields: List[str], data: Dict[str, Any] = None, **kwargs):
        """Initialize status panel.

        Args:
            title: Panel title
            fields: List of field names to display
            data: Initial data values
        """
        if not HAS_TEXTUAL:
            raise ImportError("Textual is required")

        super().__init__(**kwargs)
        self.panel_title = title
        self.fields = fields
        self.data = data or {}

    def update_data(self, data: Dict[str, Any]):
        """
        Update panel data and refresh display.
        """
        self.data.update(data)
        self.refresh()

    def render(self) -> Panel:
        """
        Render the status panel.
        """
        table = Table.grid(padding=(0, 2))
        table.add_column(style="bold cyan", justify="right")
        table.add_column(style="white")

        for field in self.fields:
            value = self.data.get(field, "—")
            table.add_row(f"{field}:", str(value))

        return Panel(table, title=f"[bold]{self.panel_title}[/bold]", border_style="cyan")
