"""
Resource scheme registry and factory helpers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .common import LOGGER
from .config import ConfigResourceScheme
from .files import FilesResourceScheme
from .logs import LogsResourceScheme
from .metrics import MetricsResourceScheme
from .prompts import PromptsResourceScheme
from .static import StaticResourceScheme
from .system import SystemResourceScheme
from .tools import ToolsResourceScheme
from .zen import ZenResourceScheme

if TYPE_CHECKING:
    from .base import ResourceSchemeHandler


class ResourceSchemeRegistry:
    """
    Registry for resource scheme handlers.
    """

    def __init__(self):
        self.handlers: dict[str, ResourceSchemeHandler] = {}
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """
        Register default scheme handlers.
        """
        self.handlers["zen"] = ZenResourceScheme()
        self.handlers["system"] = SystemResourceScheme()
        self.handlers["config"] = ConfigResourceScheme()
        self.handlers["logs"] = LogsResourceScheme()
        self.handlers["metrics"] = MetricsResourceScheme()
        self.handlers["tools"] = ToolsResourceScheme()
        self.handlers["prompts"] = PromptsResourceScheme()
        self.handlers["files"] = FilesResourceScheme()
        self.handlers["static"] = StaticResourceScheme()

    def register_handler(self, scheme: str, handler: ResourceSchemeHandler) -> None:
        """
        Register a custom scheme handler.
        """
        self.handlers[scheme] = handler
        LOGGER.info("Registered resource scheme handler: %s", scheme)

    def get_handler(self, scheme: str) -> ResourceSchemeHandler | None:
        """
        Get handler for a scheme.
        """
        return self.handlers.get(scheme)

    def list_schemes(self) -> list[str]:
        """
        List all registered schemes.
        """
        return list(self.handlers.keys())


def create_resource_handler(scheme: str) -> ResourceSchemeHandler | None:
    """
    Factory function to create resource handler for scheme.
    """
    handlers = {
        "zen": ZenResourceScheme,
        "system": SystemResourceScheme,
        "config": ConfigResourceScheme,
        "logs": LogsResourceScheme,
        "metrics": MetricsResourceScheme,
        "tools": ToolsResourceScheme,
        "prompts": PromptsResourceScheme,
        "files": FilesResourceScheme,
        "static": StaticResourceScheme,
    }

    handler_class = handlers.get(scheme)
    if handler_class:
        return handler_class()
    return None


__all__ = ["ResourceSchemeRegistry", "create_resource_handler"]
