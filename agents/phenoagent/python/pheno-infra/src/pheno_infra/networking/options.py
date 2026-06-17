"""Networking options, types, and logging utilities.

Extracted from legacy kinfra_networking module.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol


class Logger(Protocol):
    def info(self, message: str) -> None: ...
    def warn(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...


class DefaultLogger:
    """
    Default logger implementation using Python logging.
    """

    def __init__(self) -> None:
        self._logger = logging.getLogger("kinfra.networking")
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("[NETWORK] %(message)s")
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.INFO)

    def info(self, message: str) -> None:
        self._logger.info(message)

    def warn(self, message: str) -> None:
        self._logger.warning(message)

    def error(self, message: str) -> None:
        self._logger.error(message)


@dataclass
class NetworkingOptions:
    preferred_port: int | None = None
    respect_env_port: bool = True
    dynamic_fallback: bool = True
    enable_tunnel: bool = False
    kinfra_lib_path: str | None = None
    logger: Logger | None = None


@dataclass
class NetworkStartResult:
    port: int
    tunnel_url: str | None = None
    expected_host: str | None = None


@dataclass
class TunnelConfig:
    """
    Lightweight config passed to quick tunnel creation APIs.
    """

    port: int
    startup_timeout: int = 60000  # milliseconds
    protocol: str = "http"
    env: dict[str, str] | None = None
