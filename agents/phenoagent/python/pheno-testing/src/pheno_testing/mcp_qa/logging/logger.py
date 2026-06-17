"""
Structured logger facade.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from .config import configure_logging


class StructuredLogger:
    def __init__(self, logger: logging.Logger, context: Dict[str, Any] | None = None) -> None:
        self._logger = logger
        self._context = context or {}

    def bind(self, **context: Any) -> "StructuredLogger":
        combined = {**self._context, **context}
        return StructuredLogger(self._logger, combined)

    def debug(self, message: str, **context: Any) -> None:
        self._log(logging.DEBUG, message, context)

    def info(self, message: str, **context: Any) -> None:
        self._log(logging.INFO, message, context)

    def warning(self, message: str, **context: Any) -> None:
        self._log(logging.WARNING, message, context)

    def error(self, message: str, **context: Any) -> None:
        self._log(logging.ERROR, message, context)

    def exception(self, message: str, **context: Any) -> None:
        self._log(logging.ERROR, message, context, exc_info=True)

    @property
    def level(self) -> int:
        return self._logger.level

    @level.setter
    def level(self, value: int) -> None:
        self._logger.level = value

    def setLevel(self, level: int) -> None:
        self._logger.setLevel(level)

    def getEffectiveLevel(self) -> int:
        return self._logger.getEffectiveLevel()

    def isEnabledFor(self, level: int) -> bool:
        return self._logger.isEnabledFor(level)

    def _log(
        self, level: int, message: str, context: Dict[str, Any], *, exc_info: bool = False
    ) -> None:
        payload = {**self._context, **context}
        self._logger.log(level, message, extra={"context": payload}, exc_info=exc_info)


_logger_cache: Dict[str, StructuredLogger] = {}


def get_logger(name: str) -> StructuredLogger:
    configure_logging()
    if name not in _logger_cache:
        logger = logging.getLogger(name)
        _logger_cache[name] = StructuredLogger(logger)
    return _logger_cache[name]
