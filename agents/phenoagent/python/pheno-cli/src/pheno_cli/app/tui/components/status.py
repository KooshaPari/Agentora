"""
Status indicator component.
"""

from __future__ import annotations

from typing import Any

from .base import HAS_TEXTUAL, Static, reactive
from .config import ComponentTheme


class StatusIndicator(Static if HAS_TEXTUAL else object):
    """
    Configurable status indicator with different states.
    """

    def __init__(
        self,
        status: str = "unknown",
        label: str = "",
        theme: ComponentTheme = ComponentTheme.DEFAULT,
        **kwargs: Any,
    ):
        if HAS_TEXTUAL:
            super().__init__(**kwargs)
        self.status = reactive(status)
        self.label = reactive(label)
        self.theme = theme

        self.status_config = {
            "online": {"icon": "✅", "color": "green", "text": "Online"},
            "offline": {"icon": "❌", "color": "red", "text": "Offline"},
            "warning": {"icon": "⚠️", "color": "yellow", "text": "Warning"},
            "loading": {"icon": "🔄", "color": "blue", "text": "Loading"},
            "success": {"icon": "✅", "color": "green", "text": "Success"},
            "error": {"icon": "❌", "color": "red", "text": "Error"},
            "unknown": {"icon": "❓", "color": "dim", "text": "Unknown"},
        }

    def set_status(self, status: str, label: str = "") -> None:
        """
        Update status and optional label.
        """
        self.status = status
        if label:
            self.label = label
        if HAS_TEXTUAL:
            self.refresh()

    def render(self) -> Any:
        """
        Render status indicator.
        """
        if not HAS_TEXTUAL:
            return f"{self.status}: {self.label}"

        config = self.status_config.get(self.status, self.status_config["unknown"])
        icon = config["icon"]
        color = config["color"]
        text = config["text"]

        display_text = self.label if self.label else text
        return f"[{color}]{icon} {display_text}[/{color}]"


__all__ = ["StatusIndicator"]
