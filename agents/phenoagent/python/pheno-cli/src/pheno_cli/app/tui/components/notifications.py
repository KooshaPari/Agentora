"""
Notification area component.
"""

from __future__ import annotations

import time
from typing import Any

from .base import HAS_TEXTUAL, Panel, Static
from .config import ComponentTheme


class NotificationArea(Static if HAS_TEXTUAL else object):
    """
    Notification area for alerts and messages.
    """

    def __init__(
        self,
        max_notifications: int = 5,
        auto_dismiss: bool = True,
        dismiss_timeout: float = 5.0,
        theme: ComponentTheme = ComponentTheme.DEFAULT,
        **kwargs: Any,
    ):
        if HAS_TEXTUAL:
            super().__init__(**kwargs)
        self.max_notifications = max_notifications
        self.auto_dismiss = auto_dismiss
        self.dismiss_timeout = dismiss_timeout
        self.theme = theme
        self.notifications: list[dict[str, Any]] = []

    def add_notification(self, message: str, level: str = "info", persistent: bool = False) -> None:
        """
        Add a notification.
        """
        notification = {
            "id": f"notif-{time.time()}",
            "message": message,
            "level": level,
            "timestamp": time.time(),
            "persistent": persistent,
        }

        self.notifications.append(notification)

        if len(self.notifications) > self.max_notifications:
            self.notifications = self.notifications[-self.max_notifications :]

        if self.auto_dismiss and not persistent and HAS_TEXTUAL:
            self.set_timer(
                self.dismiss_timeout, lambda: self._dismiss_notification(notification["id"]),
            )

        if HAS_TEXTUAL:
            self.refresh()

    def _dismiss_notification(self, notif_id: str) -> None:
        """
        Dismiss a notification by ID.
        """
        self.notifications = [n for n in self.notifications if n["id"] != notif_id]
        if HAS_TEXTUAL:
            self.refresh()

    def clear_notifications(self) -> None:
        """
        Clear all notifications.
        """
        self.notifications.clear()
        if HAS_TEXTUAL:
            self.refresh()

    def render(self) -> Any:
        """
        Render notifications.
        """
        if not HAS_TEXTUAL:
            return f"Notifications: {len(self.notifications)}"

        if not self.notifications:
            return Panel("[dim]No notifications[/dim]", title="Notifications")

        level_icons = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}
        level_colors = {"info": "blue", "success": "green", "warning": "yellow", "error": "red"}

        content_lines = []
        for notif in self.notifications[-5:]:
            icon = level_icons.get(notif["level"], "•")
            color = level_colors.get(notif["level"], "white")
            message = notif["message"]
            content_lines.append(f"[{color}]{icon} {message}[/{color}]")

        content = "\n".join(content_lines)

        return Panel(content, title="Notifications", border_style="yellow")


__all__ = ["NotificationArea"]
