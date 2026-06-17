from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import TypeVar

from pheno.mcp.metrics import get_metrics_collector

F = TypeVar("F", bound=Callable[..., Awaitable])


def track_llm_call(agent_type: str = "llm") -> Callable[[F], F]:
    """Async decorator to track LLM provider calls with duration and outcome.

    Expects the wrapped coroutine to return an object with optional `.usage`
    carrying input_tokens/output_tokens attributes.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):  # type: ignore[override]
            collector = get_metrics_collector()
            task_id = f"{func.__name__}:{int(time.time()*1000)}"
            collector.start_execution(agent_type=agent_type, task_id=task_id)
            try:
                start = time.time()
                result = await func(*args, **kwargs)
                time.time() - start
                usage = getattr(result, "usage", None)
                tokens = 0
                if usage:
                    tokens = getattr(usage, "total_tokens", 0) or 0
                collector.complete_execution(task_id=task_id, success=True, output_length=tokens)
                return result
            except Exception as e:  # pragma: no cover - behavior
                collector.complete_execution(task_id=task_id, success=False, error=str(e))
                raise

        return wrapper  # type: ignore[return-value]

    return decorator
