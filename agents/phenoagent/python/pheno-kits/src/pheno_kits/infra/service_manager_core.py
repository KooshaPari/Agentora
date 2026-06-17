"""
Service Manager Core - Re-exports from service_manager_impl.

This module exists for backwards compatibility and re-exports
the core types from the main implementation.
"""

from .service_manager_impl import (
    FileChangeHandler,
    ResourceConfig,
    ResourceStatus,
    ServiceConfig,
    ServiceStatus,
    WATCHDOG_AVAILABLE,
)

__all__ = [
    "FileChangeHandler",
    "ResourceConfig",
    "ResourceStatus",
    "ServiceConfig",
    "ServiceStatus",
    "WATCHDOG_AVAILABLE",
]
