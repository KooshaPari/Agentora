"""
Shared configuration objects for TUI components.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ComponentTheme(Enum):
    """
    Predefined component themes.
    """

    DEFAULT = "default"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"
    ATOMS = "atoms"
    ZEN = "zen"
    BYTEPORT = "byteport"


@dataclass
class ComponentConfig:
    """
    Configuration for TUI components.
    """

    theme: ComponentTheme = ComponentTheme.DEFAULT
    title: str = ""
    subtitle: str = ""
    border_style: str = "solid"
    show_header: bool = True
    show_footer: bool = True
    auto_refresh: bool = False
    refresh_interval: float = 1.0
    context: str = "pheno"
    extra_styles: dict[str, str] = field(default_factory=dict)


__all__ = ["ComponentConfig", "ComponentTheme"]
