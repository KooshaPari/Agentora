"""
Data grid component.
"""

from __future__ import annotations

from typing import Any

from .base import HAS_TEXTUAL, Panel, Static, Table
from .config import ComponentTheme


class DataGrid(Static if HAS_TEXTUAL else object):
    """
    Configurable data grid with sorting and filtering.
    """

    def __init__(
        self,
        title: str = "Data",
        columns: list[dict[str, Any]] | None = None,
        data: list[dict[str, Any]] | None = None,
        sortable: bool = True,
        filterable: bool = True,
        theme: ComponentTheme = ComponentTheme.DEFAULT,
        **kwargs: Any,
    ):
        if HAS_TEXTUAL:
            super().__init__(**kwargs)
        self.title = title
        self.columns = columns or []
        self.data = data or []
        self.sortable = sortable
        self.filterable = filterable
        self.theme = theme
        self.sort_column = ""
        self.sort_reverse = False
        self.filter_text = ""

    def set_data(self, data: list[dict[str, Any]]) -> None:
        """
        Set grid data.
        """
        self.data = data
        if HAS_TEXTUAL:
            self.refresh()

    def add_column(
        self, name: str, title: str, width: int | None = None, align: str = "left",
    ) -> None:
        """
        Add a column to the grid.
        """
        column = {"name": name, "title": title, "width": width, "align": align}
        self.columns.append(column)

    def render(self) -> Any:
        """
        Render data grid.
        """
        if not HAS_TEXTUAL:
            return f"Data Grid: {len(self.data)} rows"

        table = Table(expand=True)

        for col in self.columns:
            justify = col.get("align", "left")
            table.add_column(col["title"], justify=justify)

        filtered_data = self.data
        if self.filter_text:
            filtered_data = [
                row
                for row in self.data
                if any(self.filter_text.lower() in str(value).lower() for value in row.values())
            ]

        if self.sort_column and self.sortable:
            filtered_data = sorted(
                filtered_data, key=lambda x: x.get(self.sort_column, ""), reverse=self.sort_reverse,
            )

        for row in filtered_data[:100]:
            values = []
            for col in self.columns:
                value = row.get(col["name"], "")
                values.append(str(value))
            table.add_row(*values)

        return Panel(table, title=self.title, border_style="blue")


__all__ = ["DataGrid"]
