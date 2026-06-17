"""Task Storage Layer.

Provides persistence for agent tasks using Redis or in-memory storage.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class TaskStorage:
    """
    Abstract interface for task storage.
    """

    async def save_task(self, task_id: str, task_data: dict[str, Any]) -> bool:
        """
        Save task data.
        """
        raise NotImplementedError

    async def get_task(self, task_id: str) -> dict[str, Any] | None:
        """
        Get task data by ID.
        """
        raise NotImplementedError

    async def delete_task(self, task_id: str) -> bool:
        """
        Delete task data.
        """
        raise NotImplementedError

    async def list_tasks(self, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """
        List tasks, optionally filtered by status.
        """
        raise NotImplementedError

    async def cleanup_old_tasks(self, retention_seconds: int) -> int:
        """
        Clean up tasks older than retention period.
        """
        raise NotImplementedError


class InMemoryTaskStorage(TaskStorage):
    """
    In-memory task storage for development/testing.
    """

    def __init__(self):
        self._tasks: dict[str, dict[str, Any]] = {}

    async def save_task(self, task_id: str, task_data: dict[str, Any]) -> bool:
        """
        Save task data in memory.
        """
        self._tasks[task_id] = {**task_data, "updated_at": datetime.now().isoformat()}
        return True

    async def get_task(self, task_id: str) -> dict[str, Any] | None:
        """
        Get task data from memory.
        """
        return self._tasks.get(task_id)

    async def delete_task(self, task_id: str) -> bool:
        """
        Delete task from memory.
        """
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False

    async def list_tasks(self, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """
        List tasks from memory.
        """
        tasks = list(self._tasks.values())

        if status:
            tasks = [t for t in tasks if t.get("status") == status]

        # Sort by updated_at desc
        tasks.sort(key=lambda t: t.get("updated_at", ""), reverse=True)

        return tasks[:limit]

    async def cleanup_old_tasks(self, retention_seconds: int) -> int:
        """
        Clean up old tasks from memory.
        """
        cutoff = datetime.now() - timedelta(seconds=retention_seconds)
        cutoff_iso = cutoff.isoformat()

        old_task_ids = [
            task_id
            for task_id, task_data in self._tasks.items()
            if task_data.get("completed_at", "") < cutoff_iso
        ]

        for task_id in old_task_ids:
            del self._tasks[task_id]

        return len(old_task_ids)


class RedisTaskStorage(TaskStorage):
    """
    Redis-based task storage for production.
    """

    def __init__(self, redis_client):
        self.redis = redis_client
        self.key_prefix = "agent:task:"

    def _make_key(self, task_id: str) -> str:
        """
        Generate Redis key for task.
        """
        return f"{self.key_prefix}{task_id}"

    async def save_task(self, task_id: str, task_data: dict[str, Any]) -> bool:
        """
        Save task data to Redis.
        """
        try:
            key = self._make_key(task_id)
            data = {**task_data, "updated_at": datetime.now().isoformat()}

            # Serialize to JSON
            serialized = json.dumps(data, default=str)

            # Save to Redis
            self.redis.setex(key, 3600 * 24, serialized)  # 24 hour TTL

            # Also add to index for listing
            self.redis.zadd(f"{self.key_prefix}index", {task_id: datetime.now().timestamp()})

            return True

        except Exception as e:
            logger.exception(f"Failed to save task to Redis: {e}")
            return False

    async def get_task(self, task_id: str) -> dict[str, Any] | None:
        """
        Get task data from Redis.
        """
        try:
            key = self._make_key(task_id)
            data = self.redis.get(key)

            if data:
                return json.loads(data)

            return None

        except Exception as e:
            logger.exception(f"Failed to get task from Redis: {e}")
            return None

    async def delete_task(self, task_id: str) -> bool:
        """
        Delete task from Redis.
        """
        try:
            key = self._make_key(task_id)
            self.redis.delete(key)
            self.redis.zrem(f"{self.key_prefix}index", task_id)
            return True

        except Exception as e:
            logger.exception(f"Failed to delete task from Redis: {e}")
            return False

    async def list_tasks(self, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """
        List tasks from Redis.
        """
        try:
            # Get recent task IDs from index
            task_ids = self.redis.zrevrange(
                f"{self.key_prefix}index", 0, limit * 2,  # Get more to account for filtering
            )

            tasks = []
            for task_id in task_ids:
                task_data = await self.get_task(
                    task_id.decode() if isinstance(task_id, bytes) else task_id,
                )
                if task_data:
                    if status is None or task_data.get("status") == status:
                        tasks.append(task_data)

                if len(tasks) >= limit:
                    break

            return tasks

        except Exception as e:
            logger.exception(f"Failed to list tasks from Redis: {e}")
            return []

    async def cleanup_old_tasks(self, retention_seconds: int) -> int:
        """
        Clean up old tasks from Redis.
        """
        try:
            cutoff_timestamp = (datetime.now() - timedelta(seconds=retention_seconds)).timestamp()

            # Get old task IDs
            old_task_ids = self.redis.zrangebyscore(f"{self.key_prefix}index", 0, cutoff_timestamp)

            # Delete old tasks
            count = 0
            for task_id in old_task_ids:
                task_id_str = task_id.decode() if isinstance(task_id, bytes) else task_id
                await self.delete_task(task_id_str)
                count += 1

            return count

        except Exception as e:
            logger.exception(f"Failed to cleanup old tasks: {e}")
            return 0


def create_task_storage(redis_client=None) -> TaskStorage:
    """Factory function to create appropriate task storage.

    Args:
        redis_client: Optional Redis client. If None, checks environment.

    Returns:
        TaskStorage instance (either Redis or in-memory)
    """
    # Check if Redis storage is explicitly disabled
    storage_mode = os.getenv("ZEN_STORAGE", os.getenv("ZEN_STORAGE_MODE", "memory")).lower()

    if storage_mode != "redis" or redis_client is None:
        logger.info("Using in-memory task storage")
        return InMemoryTaskStorage()

    # Try to use Redis storage
    try:
        if redis_client is None:
            import redis as redis_lib

            redis_client = redis_lib.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                db=int(os.getenv("REDIS_DB", "1")),
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            redis_client.ping()  # Test connection

        logger.info("Using Redis task storage")
        return RedisTaskStorage(redis_client)

    except Exception as e:
        logger.warning(f"Failed to connect to Redis, falling back to in-memory storage: {e}")
        return InMemoryTaskStorage()
