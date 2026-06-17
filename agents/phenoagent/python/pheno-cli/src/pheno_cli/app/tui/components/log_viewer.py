"""
Log viewer component.
"""

from __future__ import annotations

import time
from typing import Any

from .base import HAS_TEXTUAL, Panel, Static
from .config import ComponentTheme


class LogViewer(Static if HAS_TEXTUAL else object):
    """
    Enhanced log viewer with filtering and search.
    """

    def __init__(
        self,
        title: str = "Logs",
        max_lines: int = 1000,
        show_timestamps: bool = True,
        show_levels: bool = True,
        auto_scroll: bool = True,
        theme: ComponentTheme = ComponentTheme.DEFAULT,
        **kwargs: Any,
    ):
        if HAS_TEXTUAL:
            super().__init__(**kwargs)
        self.title = title
        self.max_lines = max_lines
        self.show_timestamps = show_timestamps
        self.show_levels = show_levels
        self.auto_scroll = auto_scroll
        self.theme = theme
        self.logs: list[dict[str, Any]] = []

    def add_log(self, message: str, level: str = "INFO", timestamp: str | None = None) -> None:
        """
        Add a log entry.
        """
        if timestamp is None:
            timestamp = time.strftime("%H:%M:%S")

        self.logs.append({"message": message, "level": level, "timestamp": timestamp})

        if len(self.logs) > self.max_lines:
            self.logs = self.logs[-self.max_lines :]

        if HAS_TEXTUAL:
            self.refresh()

    def clear_logs(self) -> None:
        """
        Clear all logs.
        """
        self.logs.clear()
        if HAS_TEXTUAL:
            self.refresh()

    def render(self) -> Any:
        """
        Render log viewer.
        """
        if not HAS_TEXTUAL:
            return f"Logs ({len(self.logs)} entries)"

        level_colors = {
            "DEBUG": "dim",
            "INFO": "white",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold red",
        }

        content_lines = []
        for entry in self.logs[-50:]:
            parts = []

            if self.show_timestamps:
                parts.append(f"[dim]{entry['timestamp']}[/dim]")

            if self.show_levels:
                level = entry["level"]
                color = level_colors.get(level, "white")
                parts.append(f"[{color}]{level:8}[/{color}]")

            parts.append(entry["message"])
            content_lines.append(" ".join(parts))

        content = "\n".join(content_lines) if content_lines else "[dim]No logs[/dim]"

        return Panel(content, title=self.title, border_style="blue", height=10)


__all__ = ["LogViewer"]
