"""
Resource scheme handlers and registry.
"""

from .base import ResourceSchemeHandler
from .config import ConfigResourceScheme
from .files import FilesResourceScheme
from .logs import LogsResourceScheme
from .metrics import MetricsResourceScheme
from .prompts import PromptsResourceScheme
from .registry import ResourceSchemeRegistry, create_resource_handler
from .static import StaticResourceScheme
from .system import SystemResourceScheme
from .tools import ToolsResourceScheme
from .zen import ZenResourceScheme

__all__ = [
    "ConfigResourceScheme",
    "FilesResourceScheme",
    "LogsResourceScheme",
    "MetricsResourceScheme",
    "PromptsResourceScheme",
    "ResourceSchemeHandler",
    "ResourceSchemeRegistry",
    "StaticResourceScheme",
    "SystemResourceScheme",
    "ToolsResourceScheme",
    "ZenResourceScheme",
    "create_resource_handler",
]
