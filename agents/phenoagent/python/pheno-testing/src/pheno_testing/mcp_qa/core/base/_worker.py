"""Worker context and environment management for parallel test execution.

Provides:
- Worker ID assignment for debugging
- Worker-specific environment isolation
- Thread-safe worker tracking
- Semaphore-based concurrency control
"""

import asyncio
import os
import threading
from typing import Dict, Optional, Set


class WorkerContext:
    """Manages worker-specific context for parallel test execution."""

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self._worker_lock = threading.Lock()
        self._active_workers: Set[int] = set()
        self._worker_errors: Dict[int, list[str]] = {}
        self._worker_envs: Dict[int, Dict[str, str]] = {}
        self._semaphore: Optional[asyncio.Semaphore] = None

    def get_worker_id(self) -> int:
        """Get unique worker ID for the current thread/task."""
        try:
            task = asyncio.current_task()
            if task:
                return hash(task) % 10000
        except RuntimeError:
            pass
        return threading.get_ident() % 10000

    def setup_environment(self, worker_id: int) -> None:
        """Set up worker-specific environment isolation."""
        with self._worker_lock:
            if worker_id not in self._worker_envs:
                self._worker_envs[worker_id] = {
                    "TEST_WORKER_ID": str(worker_id),
                    "TEST_WORKER_TEMP": f"/tmp/test_worker_{worker_id}",
                }
                self._active_workers.add(worker_id)
                self._worker_errors[worker_id] = []
                for key, value in self._worker_envs[worker_id].items():
                    os.environ[f"{key}_{worker_id}"] = value

    def cleanup_environment(self, worker_id: int) -> None:
        """Clean up worker-specific environment."""
        with self._worker_lock:
            if worker_id in self._worker_envs:
                for key in self._worker_envs[worker_id].keys():
                    os.environ.pop(f"{key}_{worker_id}", None)
                self._active_workers.discard(worker_id)
                del self._worker_envs[worker_id]

    def initialize_semaphore(self, workers: int) -> None:
        """Initialize the concurrency semaphore."""
        self._semaphore = asyncio.Semaphore(workers)

    def acquire(self) -> asyncio.Semaphore:
        """Get the semaphore for concurrency control."""
        return self._semaphore

    def record_error(self, worker_id: int, error: str) -> None:
        """Record an error for a worker."""
        with self._worker_lock:
            self._worker_errors[worker_id].append(error)

    @property
    def active_workers(self) -> Set[int]:
        """Get set of active worker IDs."""
        return self._active_workers.copy()

    @property
    def worker_errors(self) -> Dict[int, list[str]]:
        """Get error counts per worker."""
        with self._worker_lock:
            return {wid: len(errs) for wid, errs in self._worker_errors.items()}

    def cleanup_all(self) -> None:
        """Clean up all worker environments."""
        for worker_id in list(self._active_workers):
            self.cleanup_environment(worker_id)
