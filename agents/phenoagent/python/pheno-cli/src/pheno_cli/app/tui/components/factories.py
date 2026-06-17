"""
Factory functions for composite components.
"""

from __future__ import annotations

from typing import Any

from .base import Container


def create_status_panel(context: str = "pheno", **kwargs: Any) -> Container:
    """
    Create a context-themed status panel.
    """
    theme_configs = {
        "atoms": {"border_color": "blue", "icon": "⚛️"},
        "zen": {"border_color": "purple", "icon": "🧘"},
        "byteport": {"border_color": "cyan", "icon": "🚢"},
        "pheno": {"border_color": "green", "icon": "🧬"},
    }

    theme_configs.get(context, theme_configs["pheno"])
    return Container(**kwargs)


def create_monitoring_dashboard(context: str = "pheno", **kwargs: Any) -> Container:
    """
    Create a context-specific monitoring dashboard.
    """
    return Container(**kwargs)


__all__ = ["create_monitoring_dashboard", "create_status_panel"]
