"""Logging helpers for MCP QA tests.

``QuietLogger`` temporarily raises the logging level for noisy modules so test
output remains concise.  The implementation is intentionally small but mirrors
the behaviour of the standalone project.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from collections.abc import Iterable


class QuietLogger:
    """
    Context manager that temporarily silences chatty loggers.
    """

    def __init__(self, names: Iterable[str] | None = None, level: int = logging.WARNING) -> None:
        self.names = list(names or ["httpx", "asyncio"])
        self.level = level
        self._original_levels: dict[str, int] = {}

    def __enter__(self) -> Self:
        for name in self.names:
            logger = logging.getLogger(name)
            self._original_levels[name] = logger.level
            logger.setLevel(self.level)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        for name, original in self._original_levels.items():
            logging.getLogger(name).setLevel(original)


__all__ = ["QuietLogger"]
