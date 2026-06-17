"""
Resource Adapters - Generic patterns for managing any system resource

Provides adapter-based architecture for extensible resource management.
"""

from .api import APIAdapter
from .base import HealthCheckStrategy, ResourceAdapter
from .command import CommandAdapter
from .daemon import SystemDaemonAdapter
from .docker import DockerAdapter
from .factory import ResourceFactory, resource_from_dict

__all__ = [
    "APIAdapter",
    "CommandAdapter",
    "DockerAdapter",
    "HealthCheckStrategy",
    "ResourceAdapter",
    "ResourceFactory",
    "SystemDaemonAdapter",
    "resource_from_dict",
]
