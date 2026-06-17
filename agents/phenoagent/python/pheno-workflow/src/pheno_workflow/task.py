"""
Task decorator for workflow definitions.
"""

from collections.abc import Callable
from functools import wraps


def task(retries: int = 3, backoff: str = "exponential", idempotency: str | None = None):
    """
    Decorator to define a workflow task.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        wrapper._is_task = True
        wrapper._retries = retries
        wrapper._backoff = backoff
        wrapper._idempotency = idempotency
        return wrapper

    return decorator


class Worker:
    """
    Worker for executing tasks.
    """

    def __init__(self, concurrency: int = 8, backend: str = "memory"):
        self.concurrency = concurrency
        self.backend = backend
        self.tasks = []

    def register(self, task_func):
        """
        Register a task.
        """
        self.tasks.append(task_func)

    async def start(self):
        """
        Start the worker.
        """
        print(f"Worker started with {self.concurrency} workers")
