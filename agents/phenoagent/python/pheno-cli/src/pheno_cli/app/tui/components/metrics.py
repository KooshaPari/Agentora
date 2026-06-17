"""
Metrics table component.
"""

from __future__ import annotations

from typing import Any

from .base import HAS_TEXTUAL, Panel, Static, Table
from .config import ComponentTheme


class MetricsTable(Static if HAS_TEXTUAL else object):
    """
    Configurable metrics display table.
    """

    def __init__(
        self,
        title: str = "Metrics",
        columns: list[str] | None = None,
        theme: ComponentTheme = ComponentTheme.DEFAULT,
        **kwargs: Any,
    ):
        if HAS_TEXTUAL:
            super().__init__(**kwargs)
        self.title = title
        self.columns = columns or ["Metric", "Value"]
        self.metrics: dict[str, dict[str, Any]] = {}
        self.theme = theme

    def set_metric(self, name: str, value: Any, unit: str = "", status: str = "normal") -> None:
        """
        Set or update a metric value.
        """
        self.metrics[name] = {"value": value, "unit": unit, "status": status}
        if HAS_TEXTUAL:
            self.refresh()

    def remove_metric(self, name: str) -> None:
        """
        Remove a metric.
        """
        if name in self.metrics:
            del self.metrics[name]
            if HAS_TEXTUAL:
                self.refresh()

    def render(self) -> Any:
        """
        Render metrics table.
        """
        if not HAS_TEXTUAL:
            return f"Metrics: {self.metrics}"

        table = Table(expand=True)
        for col in self.columns:
            table.add_column(col, justify="left")

        status_colors = {
            "normal": "white",
            "good": "green",
            "warning": "yellow",
            "error": "red",
            "info": "blue",
        }

        for name, data in self.metrics.items():
            value = data["value"]
            unit = data["unit"]
            status = data["status"]
            color = status_colors.get(status, "white")

            value_str = f"[{color}]{value}{unit}[/{color}]"
            table.add_row(name, value_str)

        return Panel(table, title=self.title, border_style="blue")


__all__ = ["MetricsTable"]
