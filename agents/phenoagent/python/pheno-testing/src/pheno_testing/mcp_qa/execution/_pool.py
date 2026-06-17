"""Connection pooling for MCP clients."""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ConnectionStats:
    """
    Statistics for connection pool.
    """

    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    failed_connections: int = 0
    reconnections: int = 0
    total_requests: int = 0


class PooledConnection:
    """
    A single pooled connection with health checking.
    """

    def __init__(self, connection_id: int, timeout: int = 30):
        self.connection_id = connection_id
        self.timeout = timeout
        self.client: Optional[httpx.AsyncClient] = None
        self.created_at = time.time()
        self.last_used = time.time()
        self.is_healthy = True
        self.request_count = 0

    async def connect(self, base_url: str, http2: bool = True) -> None:
        """
        Establish connection.
        """
        try:
            self.client = httpx.AsyncClient(
                base_url=base_url,
                timeout=self.timeout,
                http2=http2,
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
            )
            self.is_healthy = True
            logger.debug(f"Connection {self.connection_id} established")
        except Exception as e:
            self.is_healthy = False
            logger.error(f"Failed to establish connection {self.connection_id}: {e}")
            raise

    async def close(self) -> None:
        """
        Close connection.
        """
        if self.client:
            await self.client.aclose()
            self.client = None
        logger.debug(f"Connection {self.connection_id} closed")

    async def health_check(self) -> bool:
        """
        Perform health check on connection.
        """
        if not self.client:
            self.is_healthy = False
            return False

        try:
            self.is_healthy = True
            return True
        except Exception as e:
            logger.warning(f"Health check failed for connection {self.connection_id}: {e}")
            self.is_healthy = False
            return False

    async def execute_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """
        Execute a request using this connection.
        """
        if not self.client or not self.is_healthy:
            raise RuntimeError(f"Connection {self.connection_id} is not healthy")

        try:
            self.last_used = time.time()
            self.request_count += 1

            if method.upper() == "GET":
                response = await self.client.get(endpoint, **kwargs)
            elif method.upper() == "POST":
                response = await self.client.post(endpoint, **kwargs)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.is_healthy = False
            logger.error(f"Request failed on connection {self.connection_id}: {e}")
            raise


class PooledMCPClient:
    """
    MCP Client with connection pooling and automatic reconnection.
    """

    def __init__(
        self,
        base_url: str,
        min_connections: int = 4,
        max_connections: int = 20,
        connection_timeout: int = 30,
        enable_http2: bool = True,
    ):
        self.base_url = base_url
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.enable_http2 = enable_http2

        self._pool: List[PooledConnection] = []
        self._available: asyncio.Queue = asyncio.Queue()
        self._semaphore = asyncio.Semaphore(max_connections)
        self._stats = ConnectionStats()
        self._initialized = False
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """
        Initialize connection pool with minimum connections.
        """
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            logger.info(
                f"Initializing connection pool (min: {self.min_connections}, max: {self.max_connections})"
            )

            for i in range(self.min_connections):
                conn = await self._create_connection(i)
                self._pool.append(conn)
                await self._available.put(conn)

            self._stats.total_connections = len(self._pool)
            self._stats.idle_connections = len(self._pool)
            self._initialized = True
            logger.info("Connection pool initialized")

    async def _create_connection(self, conn_id: int) -> PooledConnection:
        """
        Create a new pooled connection.
        """
        conn = PooledConnection(conn_id, timeout=self.connection_timeout)
        try:
            await conn.connect(self.base_url, http2=self.enable_http2)
            return conn
        except Exception as e:
            self._stats.failed_connections += 1
            logger.error(f"Failed to create connection: {e}")
            raise

    @asynccontextmanager
    async def acquire(self):
        """
        Acquire a connection from the pool.
        """
        if not self._initialized:
            await self.initialize()

        async with self._semaphore:
            try:
                conn = await asyncio.wait_for(self._available.get(), timeout=5.0)
            except asyncio.TimeoutError:
                if len(self._pool) < self.max_connections:
                    conn_id = len(self._pool)
                    conn = await self._create_connection(conn_id)
                    self._pool.append(conn)
                    self._stats.total_connections += 1
                else:
                    conn = await self._available.get()

            self._stats.active_connections += 1
            self._stats.idle_connections -= 1

            if not await conn.health_check():
                try:
                    await conn.close()
                    await conn.connect(self.base_url, http2=self.enable_http2)
                    self._stats.reconnections += 1
                except Exception as e:
                    logger.error(f"Failed to reconnect: {e}")
                    raise

            try:
                yield conn
            finally:
                self._stats.active_connections -= 1
                self._stats.idle_connections += 1
                await self._available.put(conn)

    async def execute(self, method: str, endpoint: str, **kwargs) -> Any:
        """
        Execute a request using pooled connection.
        """
        async with self.acquire() as conn:
            self._stats.total_requests += 1
            return await conn.execute_request(method, endpoint, **kwargs)

    async def close(self) -> None:
        """
        Close all connections in the pool.
        """
        logger.info("Closing connection pool")
        for conn in self._pool:
            await conn.close()
        self._pool.clear()
        self._initialized = False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get connection pool statistics.
        """
        return {
            "total_connections": self._stats.total_connections,
            "active_connections": self._stats.active_connections,
            "idle_connections": self._stats.idle_connections,
            "failed_connections": self._stats.failed_connections,
            "reconnections": self._stats.reconnections,
            "total_requests": self._stats.total_requests,
        }
