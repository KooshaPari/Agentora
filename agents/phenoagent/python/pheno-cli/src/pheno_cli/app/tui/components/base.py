"""
Shared Textual/Rich bindings for TUI components.
"""

from __future__ import annotations

from collections.abc import Generator as ComposeResult
from typing import Any

try:
    from rich.panel import Panel
    from rich.table import Table
    from textual.app import ComposeResult
    from textual.containers import Container, Horizontal, Vertical
    from textual.reactive import reactive
    from textual.widgets import Button, Checkbox, Input, Select, Static

    HAS_TEXTUAL = True
except ImportError:  # pragma: no cover - fallback for non-TUI environments
    Panel = Table = None  # type: ignore[assignment]
    ComposeResult = list  # type: ignore[assignment]

    class _Fallback:
        """
        Simple placeholder for textual widgets when not installed.
        """

        def __init__(self, *args: Any, **kwargs: Any):
            self.args = args
            self.kwargs = kwargs

        def __call__(self, *args: Any, **kwargs: Any):
            return self.__class__(*args, **kwargs)

    class _Reactive:
        """
        Mimic textual's reactive descriptor.
        """

        def __init__(self, initial: Any):
            self.value = initial

        def __get__(self, instance: Any, owner: Any):
            return self.value

        def __set__(self, instance: Any, value: Any):
            self.value = value

    def reactive(value: Any):  # type: ignore[override]
        return _Reactive(value)

    Static = Button = Checkbox = Input = Select = Container = Horizontal = Vertical = _Fallback  # type: ignore[assignment]
    HAS_TEXTUAL = False


__all__ = [
    "HAS_TEXTUAL",
    "Button",
    "Checkbox",
    "ComposeResult",
    "Container",
    "Horizontal",
    "Input",
    "Panel",
    "Select",
    "Static",
    "Table",
    "Vertical",
    "reactive",
]
