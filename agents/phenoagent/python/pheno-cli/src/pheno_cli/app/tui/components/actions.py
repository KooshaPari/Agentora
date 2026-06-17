"""
Action panel component.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .base import (
    HAS_TEXTUAL,
    Button,
    ComposeResult,
    Container,
    Horizontal,
    Static,
    Vertical,
)
from .config import ComponentTheme

if TYPE_CHECKING:
    from collections.abc import Callable


class ActionPanel(Container if HAS_TEXTUAL else object):
    """
    Panel with configurable action buttons.
    """

    def __init__(
        self,
        title: str = "Actions",
        actions: list[dict[str, Any]] | None = None,
        layout: str = "horizontal",
        theme: ComponentTheme = ComponentTheme.DEFAULT,
        **kwargs: Any,
    ):
        if HAS_TEXTUAL:
            super().__init__(**kwargs)
        self.title = title
        self.actions = actions or []
        self.layout = layout
        self.theme = theme

    def add_action(
        self,
        name: str,
        label: str,
        callback: Callable[..., Any],
        variant: str = "default",
        enabled: bool = True,
    ) -> None:
        """
        Add an action button.
        """
        action = {
            "name": name,
            "label": label,
            "callback": callback,
            "variant": variant,
            "enabled": enabled,
        }
        self.actions.append(action)

    def compose(self) -> ComposeResult:
        """
        Compose action panel UI.
        """
        if not HAS_TEXTUAL:
            return []

        yield Static(f"[bold]{self.title}[/bold]", id="actions-title")

        container = (
            Horizontal(id="actions-container")
            if self.layout == "horizontal"
            else Vertical(id="actions-container")
        )

        with container:
            for action in self.actions:
                yield Button(
                    action["label"],
                    id=f"btn-{action['name']}",
                    variant=action["variant"],
                    disabled=not action["enabled"],
                )


__all__ = ["ActionPanel"]
