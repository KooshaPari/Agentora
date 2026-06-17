"""Connection pooling and resource management for optimal performance.

This module provides:
- HTTP connection pooling for providers
- Resource lifecycle management
- Connection health monitoring
- Automatic connection cleanup and recycling
- Memory-efficient resource usage

Ported from zen-mcp-server to be provider-agnostic.
"""

import asyncio
import logging
import threading
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, contextmanager, suppress
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

try:
    import aiohttp

    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ConnectionPoolConfig:
    """
    Configuration for connection pools.
    """

    # Pool sizing
    max_connections: int = 100
    max_connections_per_host: int = 10

    # Timeout settings (in seconds)
    connect_timeout: float = 30.0
    read_timeout: float = 60.0
    pool_timeout: float = 5.0

    # Keep-alive settings
    keep_alive_timeout: float = 30.0
    max_keepalive_connections: int = 20

    # Retry settings
    max_retries: int = 3
    retry_backoff_factor: float = 0.5

    # Health check settings
    health_check_interval: float = 60.0
    max_idle_time: float = 300.0

    # Memory management
    enable_cleanup: bool = True
    cleanup_interval: float = 120.0


@dataclass
class ConnectionStats:
    """
    Statistics for a connection pool.
    """

    # Connection counts
    active_connections: int = 0
    idle_connections: int = 0
    total_connections: int = 0

    # Request stats
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0

    # Timing stats
    avg_response_time: float = 0.0
    min_response_time: float = 0.0
    max_response_time: float = 0.0

    # Pool health
    pool_created: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    health_status: str = "healthy"

    # Resource usage
    memory_usage_bytes: int = 0
    cpu_usage_percent: float = 0.0


class AsyncConnectionPool:
    """
    Async HTTP connection pool with health monitoring.
    """

    def __init__(self, pool_name: str, config: ConnectionPoolConfig | None = None):
        if not AIOHTTP_AVAILABLE:
            raise ImportError(
                "aiohttp is required for AsyncConnectionPool. Install with: pip install aiohttp",
            )

        self.pool_name = pool_name
        self.config = config or ConnectionPoolConfig()
        self.stats = ConnectionStats()
        self._session: aiohttp.ClientSession | None = None
        self._lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task | None = None
        self._health_check_task: asyncio.Task | None = None
        self._response_times: list[float] = []
        self._start_time = time.time()

        logger.info(f"AsyncConnectionPool '{pool_name}' initialized")

    async def initialize(self):
        """
        Initialize the connection pool.
        """
        async with self._lock:
            if self._session is None:
                timeout = aiohttp.ClientTimeout(
                    total=self.config.read_timeout,
                    connect=self.config.connect_timeout,
                    sock_read=self.config.read_timeout,
                )

                connector = aiohttp.TCPConnector(
                    limit=self.config.max_connections,
                    limit_per_host=self.config.max_connections_per_host,
                    ttl_dns_cache=300,
                    keepalive_timeout=self.config.keep_alive_timeout,
                )

                self._session = aiohttp.ClientSession(
                    timeout=timeout,
                    connector=connector,
                )

                # Start background tasks
                if self.config.enable_cleanup:
                    self._cleanup_task = asyncio.create_task(self._cleanup_loop())

                self._health_check_task = asyncio.create_task(self._health_check_loop())

                logger.info(f"AsyncConnectionPool '{self.pool_name}' session created")

    async def close(self):
        """
        Close the connection pool and cleanup resources.
        """
        async with self._lock:
            if self._cleanup_task:
                self._cleanup_task.cancel()
                with suppress(asyncio.CancelledError):
                    await self._cleanup_task

            if self._health_check_task:
                self._health_check_task.cancel()
                with suppress(asyncio.CancelledError):
                    await self._health_check_task

            if self._session:
                await self._session.close()
                self._session = None
                logger.info(f"AsyncConnectionPool '{self.pool_name}' closed")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[aiohttp.ClientSession, None]:
        """
        Get a session from the pool.
        """
        if self._session is None:
            await self.initialize()

        self.stats.active_connections += 1
        start_time = time.time()

        try:
            yield self._session

            # Record successful request
            response_time = time.time() - start_time
            self._record_response_time(response_time)
            self.stats.successful_requests += 1

        except Exception as e:
            self.stats.failed_requests += 1
            logger.exception(f"Connection pool error: {e}")
            raise

        finally:
            self.stats.active_connections -= 1
            self.stats.total_requests += 1
            self.stats.last_activity = datetime.now()

    def _record_response_time(self, response_time: float):
        """
        Record response time for statistics.
        """
        self._response_times.append(response_time)

        # Keep only last 1000 response times
        if len(self._response_times) > 1000:
            self._response_times = self._response_times[-1000:]

        # Update stats
        if self._response_times:
            self.stats.avg_response_time = sum(self._response_times) / len(self._response_times)
            self.stats.min_response_time = min(self._response_times)
            self.stats.max_response_time = max(self._response_times)

    async def _cleanup_loop(self):
        """
        Background task for periodic cleanup.
        """
        while True:
            try:
                await asyncio.sleep(self.config.cleanup_interval)
                await self._perform_cleanup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Cleanup loop error: {e}")

    async def _perform_cleanup(self):
        """
        Perform cleanup of idle connections.
        """
        # This is handled by aiohttp's connector
        logger.debug(f"Cleanup performed for pool '{self.pool_name}'")

    async def _health_check_loop(self):
        """
        Background task for health monitoring.
        """
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self._check_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Health check loop error: {e}")

    async def _check_health(self):
        """
        Check pool health.
        """
        # Check if pool is idle for too long
        idle_time = (datetime.now() - self.stats.last_activity).total_seconds()

        if idle_time > self.config.max_idle_time:
            self.stats.health_status = "idle"
        elif self.stats.failed_requests > self.stats.successful_requests * 0.5:
            self.stats.health_status = "degraded"
        else:
            self.stats.health_status = "healthy"

        logger.debug(f"Pool '{self.pool_name}' health: {self.stats.health_status}")

    def get_stats(self) -> dict[str, Any]:
        """
        Get pool statistics.
        """
        return {
            "pool_name": self.pool_name,
            "active_connections": self.stats.active_connections,
            "total_requests": self.stats.total_requests,
            "successful_requests": self.stats.successful_requests,
            "failed_requests": self.stats.failed_requests,
            "avg_response_time": self.stats.avg_response_time,
            "health_status": self.stats.health_status,
            "uptime_seconds": time.time() - self._start_time,
        }


class SyncConnectionPool:
    """
    Synchronous HTTP connection pool with health monitoring.
    """

    def __init__(self, pool_name: str, config: ConnectionPoolConfig | None = None):
        if not HTTPX_AVAILABLE:
            raise ImportError(
                "httpx is required for SyncConnectionPool. Install with: pip install httpx",
            )

        self.pool_name = pool_name
        self.config = config or ConnectionPoolConfig()
        self.stats = ConnectionStats()
        self._client: httpx.Client | None = None
        self._lock = threading.Lock()
        self._response_times: list[float] = []
        self._start_time = time.time()

        logger.info(f"SyncConnectionPool '{pool_name}' initialized")

    def initialize(self):
        """
        Initialize the connection pool.
        """
        with self._lock:
            if self._client is None:
                limits = httpx.Limits(
                    max_connections=self.config.max_connections,
                    max_keepalive_connections=self.config.max_keepalive_connections,
                )

                timeout = httpx.Timeout(
                    connect=self.config.connect_timeout,
                    read=self.config.read_timeout,
                    pool=self.config.pool_timeout,
                )

                self._client = httpx.Client(
                    limits=limits,
                    timeout=timeout,
                )

                logger.info(f"SyncConnectionPool '{self.pool_name}' client created")

    def close(self):
        """
        Close the connection pool.
        """
        with self._lock:
            if self._client:
                self._client.close()
                self._client = None
                logger.info(f"SyncConnectionPool '{self.pool_name}' closed")

    @contextmanager
    def get_client(self):
        """
        Get a client from the pool.
        """
        if self._client is None:
            self.initialize()

        self.stats.active_connections += 1
        start_time = time.time()

        try:
            yield self._client

            # Record successful request
            response_time = time.time() - start_time
            self._record_response_time(response_time)
            self.stats.successful_requests += 1

        except Exception as e:
            self.stats.failed_requests += 1
            logger.exception(f"Connection pool error: {e}")
            raise

        finally:
            self.stats.active_connections -= 1
            self.stats.total_requests += 1
            self.stats.last_activity = datetime.now()

    def _record_response_time(self, response_time: float):
        """
        Record response time for statistics.
        """
        self._response_times.append(response_time)

        # Keep only last 1000 response times
        if len(self._response_times) > 1000:
            self._response_times = self._response_times[-1000:]

        # Update stats
        if self._response_times:
            self.stats.avg_response_time = sum(self._response_times) / len(self._response_times)
            self.stats.min_response_time = min(self._response_times)
            self.stats.max_response_time = max(self._response_times)

    def get_stats(self) -> dict[str, Any]:
        """
        Get pool statistics.
        """
        return {
            "pool_name": self.pool_name,
            "active_connections": self.stats.active_connections,
            "total_requests": self.stats.total_requests,
            "successful_requests": self.stats.successful_requests,
            "failed_requests": self.stats.failed_requests,
            "avg_response_time": self.stats.avg_response_time,
            "uptime_seconds": time.time() - self._start_time,
        }
