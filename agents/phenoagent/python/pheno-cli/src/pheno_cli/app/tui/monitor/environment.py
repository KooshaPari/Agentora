"""
Environment detection helpers for monitor UIs.
"""

from __future__ import annotations

HAS_RICH = False
HAS_TEXTUAL = False

try:  # pragma: no cover - optional dependency
    from rich import box
    from rich.align import Align
    from rich.console import Console, Group
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table

    HAS_RICH = True
except ImportError:  # pragma: no cover - fallback
    Console = Group = Panel = Table = Layout = Live = Align = box = None  # type: ignore

try:  # pragma: no cover - optional dependency
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Vertical
    from textual.widgets import (
        DataTable,
        Footer,
        Header,
        Input,
        Log,
        Static,
        TabbedContent,
        TabPane,
    )

    HAS_TEXTUAL = True
except ImportError:  # pragma: no cover - fallback
    App = ComposeResult = Horizontal = Vertical = DataTable = Footer = Header = Input = Log = Static = TabPane = TabbedContent = None  # type: ignore


__all__ = [
    "HAS_RICH",
    "HAS_TEXTUAL",
    "Align",
    "App",
    "ComposeResult",
    "Console",
    "DataTable",
    "Footer",
    "Group",
    "Header",
    "Horizontal",
    "Input",
    "Layout",
    "Live",
    "Log",
    "Panel",
    "Static",
    "TabPane",
    "TabbedContent",
    "Table",
    "Vertical",
    "box",
]
