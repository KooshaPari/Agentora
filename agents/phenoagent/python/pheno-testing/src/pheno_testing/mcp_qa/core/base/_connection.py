"""Connection pool management for parallel test execution.

Provides:
- Connection pool initialization
- Base URL extraction from clients
- Response cache setup
"""

from typing import Any, Optional


class ConnectionPoolManager:
    """Manages connection pooling for parallel test execution."""

    def __init__(
        self,
        pool_class: Optional[Any] = None,
        cache_class: Optional[Any] = None,
        parallel: bool = False,
        workers: int = 4,
    ):
        self.pool_class = pool_class
        self.cache_class = cache_class
        self.parallel = parallel
        self.workers = workers
        self.connection_pool = None
        self.response_cache = None

    async def initialize(self, base_url: str) -> None:
        """Initialize connection pool and response cache."""
        if not self.parallel or not self.pool_class or not self.cache_class:
            return

        try:
            self.connection_pool = self.pool_class(
                base_url=base_url,
                min_connections=self.workers,
                max_connections=self.workers * 2,
            )
            await self.connection_pool.initialize()
            self.response_cache = self._cache_class(max_size=1000, default_ttl=60)
            print("Performance optimizations active")
            print(f"   Connection pool: {self.workers}-{self.workers * 2} clients")
            print("   Response cache: LRU (1000 entries, 60s TTL)")
        except Exception as e:
            print(f"Connection pool initialization failed: {e}")
            print("   Falling back to single client (will be slower)")
            self.connection_pool = None
            self.response_cache = None

    @staticmethod
    def extract_base_url(client_adapter: Any) -> str:
        """Extract base URL from client adapter."""
        client = client_adapter.client
        if hasattr(client, "mcp_url"):
            return client.mcp_url
        elif hasattr(client, "_client") and hasattr(client._client, "mcp_url"):
            return client._client.mcp_url
        elif hasattr(client, "url"):
            return client.url
        else:
            return getattr(client, "base_url", "http://localhost:8000")
