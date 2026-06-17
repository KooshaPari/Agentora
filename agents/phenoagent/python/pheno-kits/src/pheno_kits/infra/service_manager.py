"""
Service Manager - Infrastructure service management.

Provides complete service lifecycle management for KInfra with:
- Process startup and management
- Continuous health monitoring
- File watching and auto-reload
- Resource dependency checking
"""

from .service_manager_impl import (
    ServiceManager,
    ServiceConfig,
    ResourceConfig,
    ServiceStatus,
    ResourceStatus,
    FileChangeHandler,
    WATCHDOG_AVAILABLE,
)

__all__ = [
    "ServiceManager",
    "ServiceConfig",
    "ResourceConfig",
    "ServiceStatus",
    "ResourceStatus",
    "FileChangeHandler",
    "WATCHDOG_AVAILABLE",
]
