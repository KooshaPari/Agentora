"""
Base MCP resource templates shared across projects.
"""

from __future__ import annotations

from .shared_templates import ALL_SHARED_TEMPLATES, get_shared_templates


def get_base_templates() -> list[ResourceTemplate]:
    """
    Return core MCP resource templates.
    """
    return get_shared_templates()


# Export the shared templates for easy access
ALL_RESOURCE_TEMPLATES = ALL_SHARED_TEMPLATES
