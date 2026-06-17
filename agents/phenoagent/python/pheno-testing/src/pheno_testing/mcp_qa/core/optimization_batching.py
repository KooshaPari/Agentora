"""Batch request optimization for MCP clients."""

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from utils.logging_setup import get_logger

logger = get_logger(__name__)


@dataclass
class BatchRequest:
    """
    A single request in a batch.
    """

    request_id: str
    method: str
    endpoint: str
    params: Dict[str, Any]
    future: asyncio.Future


class BatchRequestOptimizer:
    """
    Optimizer for batching multiple requests together.
    """

    def __init__(
        self,
        client: "PooledMCPClient",
        batch_size: int = 10,
        batch_timeout: float = 0.1,
    ):
        self.client = client
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self._pending: List[BatchRequest] = []
        self._lock = asyncio.Lock()
        self._batch_task: Optional[asyncio.Task] = None
        self._request_hashes: Dict[str, List[asyncio.Future]] = {}

    def _generate_request_hash(self, method: str, endpoint: str, params: Dict[str, Any]) -> str:
        """
        Generate hash for request deduplication.
        """
        key_data = json.dumps(
            {"method": method, "endpoint": endpoint, "params": params}, sort_keys=True
        )
        return hashlib.sha256(key_data.encode()).hexdigest()

    async def add_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Add a request to the batch queue.
        """
        params = params or {}
        request_hash = self._generate_request_hash(method, endpoint, params)

        async with self._lock:
            if request_hash in self._request_hashes:
                logger.debug(f"Deduplicating request: {method} {endpoint}")
                future = asyncio.Future()
                self._request_hashes[request_hash].append(future)
                return await future

            request_id = f"req_{len(self._pending)}_{time.time()}"
            future = asyncio.Future()

            request = BatchRequest(
                request_id=request_id,
                method=method,
                endpoint=endpoint,
                params=params,
                future=future,
            )

            self._pending.append(request)
            self._request_hashes[request_hash] = [future]

            if len(self._pending) >= self.batch_size:
                await self._process_batch()
            elif not self._batch_task or self._batch_task.done():
                self._batch_task = asyncio.create_task(self._batch_timeout_handler())

        return await future

    async def _batch_timeout_handler(self) -> None:
        """
        Process batch after timeout if not full.
        """
        await asyncio.sleep(self.batch_timeout)
        async with self._lock:
            if self._pending:
                await self._process_batch()

    async def _process_batch(self) -> None:
        """
        Process all pending requests in parallel.
        """
        if not self._pending:
            return

        batch = self._pending[:]
        self._pending.clear()
        self._request_hashes.clear()

        logger.debug(f"Processing batch of {len(batch)} requests")

        tasks = [self._execute_request(req) for req in batch]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _execute_request(self, request: BatchRequest) -> None:
        """
        Execute a single request and set its future.
        """
        try:
            result = await self.client.execute(
                request.method,
                request.endpoint,
                json=request.params,
            )
            request.future.set_result(result)
        except Exception as e:
            request.future.set_exception(e)

    async def flush(self) -> None:
        """
        Flush all pending requests immediately.
        """
        async with self._lock:
            if self._pending:
                await self._process_batch()
