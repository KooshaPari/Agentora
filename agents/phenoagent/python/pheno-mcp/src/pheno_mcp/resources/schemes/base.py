"""
Base abstractions for resource schemes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..template_engine import ResourceContext


class ResourceSchemeHandler(ABC):
    """
    Base class for resource scheme handlers.
    """

    def __init__(self, scheme: str):
        self.scheme = scheme

    @abstractmethod
    async def handle_request(self, context: ResourceContext) -> dict[str, Any]:
        """Handle a resource request.

        Subclasses that expose multiple handler methods typically rely on the template
        engine to call the appropriate method directly, so this remains abstract for
        extensibility.
        """
        raise NotImplementedError


__all__ = ["ResourceSchemeHandler"]
