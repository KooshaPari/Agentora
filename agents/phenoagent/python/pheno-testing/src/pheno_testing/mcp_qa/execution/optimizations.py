"""Performance Optimizations for MCP Test Suite.

This module provides optimized client adapters with connection pooling, batching,
caching, and concurrency management for improved test performance.
"""

import logging
from typing import Any, Dict, Optional

from ._batch import BatchRequestOptimizer
from ._cache import ResponseCacheLayer
from ._concurrency import ConcurrencyOptimizer
from ._flags import OptimizationFlags
from ._network import NetworkOptimizer
from ._pool import PooledConnection, PooledMCPClient

logger = logging.getLogger(__name__)


class OptimizedMCPClient:
    """Fully optimized MCP client with all optimization layers.

    This is the main client that applications should use.
    """

    def __init__(
        self,
        base_url: str,
        flags: Optional[OptimizationFlags] = None,
    ):
        self.base_url = base_url
        self.flags = flags or OptimizationFlags()

        self._pooled_client: Optional[PooledMCPClient] = None
        self._batch_optimizer: Optional[BatchRequestOptimizer] = None
        self._concurrency_optimizer: Optional[ConcurrencyOptimizer] = None
        self._cache: Optional[ResponseCacheLayer] = None
        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize all optimization layers.
        """
        if self._initialized:
            return

        logger.info("Initializing optimized MCP client")

        if self.flags.enable_connection_pooling:
            self._pooled_client = PooledMCPClient(
                base_url=self.base_url,
                min_connections=self.flags.pool_min_size,
                max_connections=self.flags.pool_max_size,
                connection_timeout=self.flags.connection_timeout,
                enable_http2=self.flags.enable_http2,
            )
            await self._pooled_client.initialize()

        if self.flags.enable_batch_requests and self._pooled_client:
            self._batch_optimizer = BatchRequestOptimizer(
                client=self._pooled_client,
                batch_size=self.flags.batch_size,
            )

        if self.flags.enable_concurrency_optimization:
            self._concurrency_optimizer = ConcurrencyOptimizer(
                worker_multiplier=self.flags.worker_multiplier,
            )

        if self.flags.enable_response_caching:
            self._cache = ResponseCacheLayer(
                max_size=self.flags.cache_max_entries,
                default_ttl=self.flags.cache_ttl_seconds,
            )

        self._initialized = True
        logger.info("Optimized MCP client initialized")

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        use_cache: bool = True,
    ) -> Any:
        """Call an MCP tool with all optimizations applied.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            use_cache: Whether to use response cache

        Returns:
            Tool response
        """
        if not self._initialized:
            await self.initialize()

        if use_cache and self._cache:
            cached = self._cache.get(tool_name, arguments)
            if cached is not None:
                return cached

        if self._batch_optimizer:
            result = await self._batch_optimizer.add_request(
                method="POST",
                endpoint="/tools/call",
                params={"tool": tool_name, "arguments": arguments},
            )
        elif self._pooled_client:
            result = await self._pooled_client.execute(
                method="POST",
                endpoint="/tools/call",
                json={"tool": tool_name, "arguments": arguments},
            )
        else:
            client = NetworkOptimizer.create_optimized_client(
                base_url=self.base_url,
                enable_http2=self.flags.enable_http2,
                enable_compression=self.flags.enable_compression,
            )
            try:
                response = await client.post(
                    "/tools/call",
                    json={"tool": tool_name, "arguments": arguments},
                )
                response.raise_for_status()
                result = response.json()
            finally:
                await client.aclose()

        if use_cache and self._cache and self._is_read_only(tool_name):
            self._cache.set(tool_name, arguments, result)

        return result

    def _is_read_only(self, tool_name: str) -> bool:
        """
        Check if a tool is read-only (safe to cache).
        """
        read_only_prefixes = ["get_", "list_", "search_", "query_", "find_"]
        return any(tool_name.startswith(prefix) for prefix in read_only_prefixes)

    async def close(self) -> None:
        """
        Close all resources.
        """
        if self._batch_optimizer:
            await self._batch_optimizer.flush()

        if self._pooled_client:
            await self._pooled_client.close()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics from all optimization layers.
        """
        stats: Dict[str, Any] = {}

        if self._pooled_client:
            stats["connection_pool"] = self._pooled_client.get_stats()

        if self._cache:
            stats["cache"] = self._cache.get_stats()

        if self._concurrency_optimizer:
            stats["concurrency"] = {
                "optimal_workers": self._concurrency_optimizer.get_optimal_worker_count(),
            }

        return stats


def create_optimized_client(base_url: str, **kwargs) -> OptimizedMCPClient:
    """Create an optimized MCP client with default settings.

    Args:
        base_url: Base URL for MCP server
        **kwargs: Additional flags for OptimizationFlags

    Returns:
        Optimized MCP client
    """
    flags = OptimizationFlags(**kwargs)
    return OptimizedMCPClient(base_url, flags)


__all__ = [
    "OptimizationFlags",
    "PooledMCPClient",
    "PooledConnection",
    "BatchRequestOptimizer",
    "ConcurrencyOptimizer",
    "ResponseCacheLayer",
    "NetworkOptimizer",
    "OptimizedMCPClient",
    "create_optimized_client",
]
