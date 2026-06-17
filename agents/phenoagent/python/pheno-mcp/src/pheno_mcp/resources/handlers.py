"""
Shared MCP resource scheme handlers.
"""

from __future__ import annotations

from typing import Any


class ResourceSchemeHandler:
    """
    Minimal scheme handler base.
    """

    scheme: str

    def __init__(self, scheme: str) -> None:
        self.scheme = scheme

    async def handle_request(
        self, context: Any,
    ) -> dict[str, Any]:  # pragma: no cover - placeholder
        raise NotImplementedError
