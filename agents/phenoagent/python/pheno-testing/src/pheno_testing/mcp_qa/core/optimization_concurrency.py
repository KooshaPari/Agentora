"""Concurrency optimization for MCP test execution."""

import asyncio
import multiprocessing
from contextlib import asynccontextmanager
from typing import Optional

from utils.logging_setup import get_logger

logger = get_logger(__name__)


class ConcurrencyOptimizer:
    """
    Optimizer for managing concurrent test execution.
    """

    def __init__(
        self,
        worker_multiplier: int = 2,
        max_workers: Optional[int] = None,
        memory_limit_gb: float = 4.0,
    ):
        self.worker_multiplier = worker_multiplier
        self.memory_limit_gb = memory_limit_gb
        self._max_workers = max_workers
        self._rate_limiter: Optional[asyncio.Semaphore] = None

    def get_optimal_worker_count(self) -> int:
        """
        Calculate optimal worker count based on CPU and memory.
        """
        if self._max_workers:
            return self._max_workers

        cpu_count = multiprocessing.cpu_count()
        optimal = cpu_count * self.worker_multiplier

        try:
            import psutil

            available_memory_gb = psutil.virtual_memory().available / (1024**3)
            memory_based_workers = int(available_memory_gb / 0.5)
            optimal = min(optimal, memory_based_workers)
        except ImportError:
            logger.warning("psutil not available, skipping memory-based worker adjustment")

        logger.info(f"Optimal worker count: {optimal} (CPU cores: {cpu_count})")
        return max(1, optimal)

    def create_rate_limiter(self, max_concurrent: Optional[int] = None) -> asyncio.Semaphore:
        """
        Create a rate limiter for concurrent operations.
        """
        if max_concurrent is None:
            max_concurrent = self.get_optimal_worker_count()

        self._rate_limiter = asyncio.Semaphore(max_concurrent)
        return self._rate_limiter

    @asynccontextmanager
    async def limit_concurrency(self):
        """
        Context manager for limiting concurrency.
        """
        if not self._rate_limiter:
            self._rate_limiter = self.create_rate_limiter()

        async with self._rate_limiter:
            yield
