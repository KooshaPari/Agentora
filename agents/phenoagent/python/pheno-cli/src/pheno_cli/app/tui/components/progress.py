"""
Progress widget component.
"""

from __future__ import annotations

import time
from typing import Any

from .base import HAS_TEXTUAL, Panel, Static, reactive
from .config import ComponentTheme


class ProgressWidget(Static if HAS_TEXTUAL else object):
    """
    Enhanced progress widget with multiple display modes.
    """

    def __init__(
        self,
        total: int = 100,
        label: str = "Progress",
        show_percentage: bool = True,
        show_eta: bool = True,
        show_rate: bool = False,
        theme: ComponentTheme = ComponentTheme.DEFAULT,
        **kwargs: Any,
    ):
        if HAS_TEXTUAL:
            super().__init__(**kwargs)
        self.total = total
        self.current = reactive(0)
        self.label = reactive(label)
        self.show_percentage = show_percentage
        self.show_eta = show_eta
        self.show_rate = show_rate
        self.theme = theme
        self.start_time: float | None = None

    def update_progress(self, current: int, label: str = "") -> None:
        """
        Update progress value and optional label.
        """
        if self.start_time is None:
            self.start_time = time.time()

        self.current = current
        if label:
            self.label = label
        if HAS_TEXTUAL:
            self.refresh()

    def render(self) -> Any:
        """
        Render progress widget.
        """
        if not HAS_TEXTUAL:
            return f"Progress: {self.current}/{self.total}"

        percentage = (self.current / self.total) * 100 if self.total > 0 else 0
        bar_width = 20
        filled = int((percentage / 100) * bar_width)
        bar = "▓" * filled + "░" * (bar_width - filled)

        parts = [f"[blue]{bar}[/blue]"]

        if self.show_percentage:
            parts.append(f"{percentage:.1f}%")

        parts.append(f"({self.current}/{self.total})")

        if self.show_eta and self.start_time and self.current > 0:
            elapsed = time.time() - self.start_time
            eta = (elapsed / self.current) * (self.total - self.current)
            parts.append(f"{int(eta)}s remaining")

        content = " ".join(parts)

        return Panel(content, title=str(self.label), border_style="blue")


__all__ = ["ProgressWidget"]
