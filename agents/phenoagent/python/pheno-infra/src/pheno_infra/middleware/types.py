"""
Types and configuration for KInfra middleware.
"""

from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class ServiceState(Enum):
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"
    STOPPED = "stopped"
    MAINTENANCE = "maintenance"


class MiddlewareConfig:
    def __init__(
        self,
        templates_dir: Path | None = None,
        enable_loading: bool = True,
        enable_fallback: bool = True,
        enable_health_check: bool = True,
        loading_timeout: int = 120,
        health_check_interval: float = 5.0,
    ):
        self.templates_dir = (
            templates_dir or (Path(__file__).parent / "../templates/error_pages").resolve()
        )
        self.enable_loading = enable_loading
        self.enable_fallback = enable_fallback
        self.enable_health_check = enable_health_check
        self.loading_timeout = loading_timeout
        self.health_check_interval = health_check_interval
