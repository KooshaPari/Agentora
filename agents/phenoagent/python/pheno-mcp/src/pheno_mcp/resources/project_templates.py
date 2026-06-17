"""
Project-specific MCP resource templates shared with downstream projects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .registry import ResourceTemplate

if TYPE_CHECKING:
    from collections.abc import Callable


def get_project_templates(handler_factory: Callable[[], Any]) -> list[ResourceTemplate]:
    """
    Return project-specific resource templates using the provided handler factory.
    """

    handler = handler_factory()
    return [
        ResourceTemplate(
            name="project-graph",
            uri_pattern="project://graphs/list/{filter}",
            description="List all active project graphs",
            handler=lambda path, params, ctx: handler.handle_resource_request(
                "/graphs/list", params, ctx,
            ),
        ),
    ]
