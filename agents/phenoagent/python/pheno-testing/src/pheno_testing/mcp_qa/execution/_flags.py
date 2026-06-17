"""Configuration flags for enabling/disabling optimizations."""

import os
from dataclasses import dataclass


@dataclass
class OptimizationFlags:
    """
    Configuration flags for enabling/disabling optimizations.
    """

    enable_connection_pooling: bool = True
    enable_batch_requests: bool = True
    enable_concurrency_optimization: bool = True
    enable_response_caching: bool = True
    enable_network_optimization: bool = True
    pool_min_size: int = 4
    pool_max_size: int = 20
    batch_size: int = 10
    cache_max_entries: int = 1000
    cache_ttl_seconds: int = 60
    worker_multiplier: int = 2
    enable_http2: bool = True
    enable_compression: bool = True
    connection_timeout: int = 30
    request_timeout: int = 60

    @classmethod
    def from_env(cls) -> "OptimizationFlags":
        """
        Create flags from environment variables.
        """
        return cls(
            enable_connection_pooling=os.getenv("MCP_ENABLE_POOLING", "true").lower() == "true",
            enable_batch_requests=os.getenv("MCP_ENABLE_BATCHING", "true").lower() == "true",
            enable_concurrency_optimization=os.getenv("MCP_ENABLE_CONCURRENCY", "true").lower()
            == "true",
            enable_response_caching=os.getenv("MCP_ENABLE_CACHING", "true").lower() == "true",
            enable_network_optimization=os.getenv("MCP_ENABLE_NETWORK_OPT", "true").lower()
            == "true",
            pool_min_size=int(os.getenv("MCP_POOL_MIN_SIZE", "4")),
            pool_max_size=int(os.getenv("MCP_POOL_MAX_SIZE", "20")),
            batch_size=int(os.getenv("MCP_BATCH_SIZE", "10")),
            cache_max_entries=int(os.getenv("MCP_CACHE_MAX_ENTRIES", "1000")),
            cache_ttl_seconds=int(os.getenv("MCP_CACHE_TTL", "60")),
            worker_multiplier=int(os.getenv("MCP_WORKER_MULTIPLIER", "2")),
            enable_http2=os.getenv("MCP_ENABLE_HTTP2", "true").lower() == "true",
            enable_compression=os.getenv("MCP_ENABLE_COMPRESSION", "true").lower() == "true",
            connection_timeout=int(os.getenv("MCP_CONNECTION_TIMEOUT", "30")),
            request_timeout=int(os.getenv("MCP_REQUEST_TIMEOUT", "60")),
        )
