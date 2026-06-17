"""Connection pooling module for db-kit.

Provides HTTP connection pooling with health monitoring and resource management.
"""

from .connection_pool import (
    AsyncConnectionPool,
    ConnectionPoolConfig,
    ConnectionStats,
    SyncConnectionPool,
)
from .pool_manager import (
    ConnectionPoolManager,
    cleanup_all_pools,
    get_pool_manager,
    get_provider_pool,
)

__all__ = [
    # Connection pools
    "AsyncConnectionPool",
    "ConnectionPoolConfig",
    # Pool manager
    "ConnectionPoolManager",
    "ConnectionStats",
    "SyncConnectionPool",
    "cleanup_all_pools",
    "get_pool_manager",
    "get_provider_pool",
]
