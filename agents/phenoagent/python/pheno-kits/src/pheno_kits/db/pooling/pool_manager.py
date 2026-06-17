"""Connection pool manager for managing multiple connection pools.

Provides centralized management of connection pools for different providers/services.
"""

import asyncio
import logging
from typing import Any

from .connection_pool import (
    AsyncConnectionPool,
    ConnectionPoolConfig,
    SyncConnectionPool,
)

logger = logging.getLogger(__name__)


class ConnectionPoolManager:
    """Manages multiple connection pools for different providers/services.

    Example:
        manager = ConnectionPoolManager()

        # Get or create a pool
        pool = manager.get_pool("my_service", async_pool=True)

        # Use the pool
        async with pool.get_session() as session:
            async with session.get("https://api.example.com") as response:
                data = await response.json()

        # Cleanup all pools
        await manager.cleanup_all()
    """

    def __init__(self):
        self._async_pools: dict[str, AsyncConnectionPool] = {}
        self._sync_pools: dict[str, SyncConnectionPool] = {}
        self._lock = asyncio.Lock()
        self._sync_lock = None  # Will be created when needed
        logger.info("ConnectionPoolManager initialized")

    def get_pool(
        self,
        pool_name: str,
        async_pool: bool = True,
        config: ConnectionPoolConfig | None = None,
    ) -> AsyncConnectionPool | SyncConnectionPool:
        """Get or create a connection pool.

        Args:
            pool_name: Unique name for the pool
            async_pool: If True, return AsyncConnectionPool, else SyncConnectionPool
            config: Optional configuration for the pool

        Returns:
            Connection pool instance
        """
        if async_pool:
            if pool_name not in self._async_pools:
                self._async_pools[pool_name] = AsyncConnectionPool(pool_name, config)
                logger.info(f"Created async pool: {pool_name}")
            return self._async_pools[pool_name]
        if pool_name not in self._sync_pools:
            self._sync_pools[pool_name] = SyncConnectionPool(pool_name, config)
            logger.info(f"Created sync pool: {pool_name}")
        return self._sync_pools[pool_name]

    async def close_pool(self, pool_name: str, async_pool: bool = True):
        """
        Close a specific pool.
        """
        if async_pool:
            if pool_name in self._async_pools:
                await self._async_pools[pool_name].close()
                del self._async_pools[pool_name]
                logger.info(f"Closed async pool: {pool_name}")
        elif pool_name in self._sync_pools:
            self._sync_pools[pool_name].close()
            del self._sync_pools[pool_name]
            logger.info(f"Closed sync pool: {pool_name}")

    async def cleanup_all(self):
        """
        Close all connection pools.
        """
        # Close async pools
        for pool_name, pool in list(self._async_pools.items()):
            try:
                await pool.close()
                logger.info(f"Closed async pool: {pool_name}")
            except Exception as e:
                logger.exception(f"Error closing async pool {pool_name}: {e}")

        self._async_pools.clear()

        # Close sync pools
        for pool_name, pool in list(self._sync_pools.items()):
            try:
                pool.close()
                logger.info(f"Closed sync pool: {pool_name}")
            except Exception as e:
                logger.exception(f"Error closing sync pool {pool_name}: {e}")

        self._sync_pools.clear()

        logger.info("All connection pools closed")

    def get_all_stats(self) -> dict[str, Any]:
        """
        Get statistics for all pools.
        """
        stats = {
            "async_pools": {},
            "sync_pools": {},
            "total_pools": len(self._async_pools) + len(self._sync_pools),
        }

        for pool_name, pool in self._async_pools.items():
            stats["async_pools"][pool_name] = pool.get_stats()

        for pool_name, pool in self._sync_pools.items():
            stats["sync_pools"][pool_name] = pool.get_stats()

        return stats

    def list_pools(self) -> dict[str, list[str]]:
        """
        List all active pools.
        """
        return {
            "async_pools": list(self._async_pools.keys()),
            "sync_pools": list(self._sync_pools.keys()),
        }


# Global pool manager instance
_pool_manager: ConnectionPoolManager | None = None


def get_pool_manager() -> ConnectionPoolManager:
    """
    Get the global connection pool manager instance.
    """
    global _pool_manager
    if _pool_manager is None:
        _pool_manager = ConnectionPoolManager()
    return _pool_manager


def get_provider_pool(
    provider_name: str,
    async_pool: bool = True,
    config: ConnectionPoolConfig | None = None,
) -> AsyncConnectionPool | SyncConnectionPool:
    """Convenience function to get a pool for a specific provider.

    Args:
        provider_name: Name of the provider (e.g., "openai", "anthropic")
        async_pool: If True, return AsyncConnectionPool
        config: Optional pool configuration

    Returns:
        Connection pool for the provider
    """
    manager = get_pool_manager()
    return manager.get_pool(provider_name, async_pool, config)


async def cleanup_all_pools():
    """
    Cleanup all connection pools (convenience function).
    """
    manager = get_pool_manager()
    await manager.cleanup_all()
