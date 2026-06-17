"""Performance optimizations for MCP test suite.

This module provides optimized client adapters with connection pooling, batching,
caching, and concurrency management for improved test performance.
"""

from .optimization_batching import BatchRequestOptimizer
from .optimization_cache import ResponseCacheLayer
from .optimization_concurrency import ConcurrencyOptimizer
from .optimization_config import OptimizationFlags
from .optimization_network import NetworkOptimizer
from .optimization_pool import PooledMCPClient

from .optimization_client import OptimizedMCPClient, create_optimized_client

__all__ = [
    "OptimizationFlags",
    "PooledMCPClient",
    "BatchRequestOptimizer",
    "ConcurrencyOptimizer",
    "ResponseCacheLayer",
    "NetworkOptimizer",
    "OptimizedMCPClient",
    "create_optimized_client",
]
