"""
Cost estimation helpers using tiktoken and litellm.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    import tiktoken  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    tiktoken = None

try:  # pragma: no cover - optional dependency
    from litellm import completion_cost  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    completion_cost = None


def estimate_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    """
    Estimate token usage for text using tiktoken when available.
    """

    if tiktoken is None:  # pragma: no cover - optional dependency guard
        logger.debug("tiktoken not installed, returning length heuristic")
        return max(1, len(text) // 4)

    try:
        enc = tiktoken.encoding_for_model(model)
    except Exception:  # pragma: no cover - fallback to generic encoding
        enc = tiktoken.get_encoding("cl100k_base")

    return len(enc.encode(text))


def estimate_completion_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    Estimate USD cost using litellm cost tables.
    """

    if completion_cost is None:  # pragma: no cover - optional dependency guard
        logger.debug("litellm not installed; returning zero cost")
        return 0.0

    try:
        cost = completion_cost(  # type: ignore[call-arg]
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        return float(cost)
    except Exception as exc:  # pragma: no cover - defensive path
        logger.warning("cost_estimation_failed", model=model, error=str(exc))
        return 0.0
