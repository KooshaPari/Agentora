"""
Test coordination to prevent duplicate runs across team.
"""

import hashlib
import time
from typing import Optional

from .cache import SharedCache
from .models import TestResult


class TestCoordinator:
    """
    Prevent duplicate test runs across team.
    """

    def __init__(self, cache: SharedCache):
        self.cache = cache
        self.lock_prefix = "test_lock:"
        self.result_prefix = "test_result:"
        self.lock_timeout = 300  # 5 minutes

    def _get_test_key(self, test_name: str, endpoint: str) -> str:
        """
        Generate a unique key for a test.
        """
        combined = f"{test_name}:{endpoint}"
        return hashlib.md5(combined.encode()).hexdigest()

    async def acquire_test_lock(self, test_name: str, endpoint: str, user: str) -> bool:
        """
        Try to acquire a lock for running a test.
        """
        key = self._get_test_key(test_name, endpoint)
        lock_key = f"{self.lock_prefix}{key}"

        existing_lock = await self.cache.get(lock_key)
        if existing_lock:
            if time.time() - existing_lock["timestamp"] > self.lock_timeout:
                await self.cache.delete(lock_key)
            else:
                return False

        await self.cache.set(
            lock_key, {"user": user, "timestamp": time.time()}, ttl=self.lock_timeout
        )

        return True

    async def release_test_lock(self, test_name: str, endpoint: str):
        """
        Release a test lock.
        """
        key = self._get_test_key(test_name, endpoint)
        lock_key = f"{self.lock_prefix}{key}"
        await self.cache.delete(lock_key)

    async def get_test_lock_holder(self, test_name: str, endpoint: str) -> Optional[str]:
        """
        Get who holds the lock for a test.
        """
        key = self._get_test_key(test_name, endpoint)
        lock_key = f"{self.lock_prefix}{key}"
        lock_data = await self.cache.get(lock_key)
        return lock_data["user"] if lock_data else None

    async def store_test_result(self, test_name: str, endpoint: str, result: TestResult):
        """
        Store a test result for sharing.
        """
        key = self._get_test_key(test_name, endpoint)
        result_key = f"{self.result_prefix}{key}"
        await self.cache.set(result_key, result.to_dict(), ttl=3600)  # 1 hour TTL

    async def get_test_result(self, test_name: str, endpoint: str) -> Optional[TestResult]:
        """
        Get a cached test result.
        """
        key = self._get_test_key(test_name, endpoint)
        result_key = f"{self.result_prefix}{key}"
        result_data = await self.cache.get(result_key)
        if result_data:
            return TestResult(**result_data)
        return None

    async def is_test_running(self, test_name: str, endpoint: str) -> bool:
        """
        Check if a test is currently running.
        """
        holder = await self.get_test_lock_holder(test_name, endpoint)
        return holder is not None

    async def wait_for_test(
        self, test_name: str, endpoint: str, timeout: float = 300
    ) -> Optional[TestResult]:
        """
        Wait for a test to complete and return its result.
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            if not await self.is_test_running(test_name, endpoint):
                result = await self.get_test_result(test_name, endpoint)
                if result:
                    return result

            await asyncio.sleep(1)

        return None
