"""
Resource registry facade for MCP SDK kit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


@dataclass
class ResourceTemplate:
    """
    Lightweight template descriptor placeholder.
    """

    name: str
    uri_pattern: str
    description: str
    handler: Callable[[Any, Any, Any], Awaitable[Any]]


class ResourceRegistry:
    """
    Minimal facade until full implementation is shared.
    """

    templates: list[ResourceTemplate]

    def __init__(self) -> None:
        self.templates = []

    def register_template(self, template: ResourceTemplate) -> None:
        self.templates.append(template)
