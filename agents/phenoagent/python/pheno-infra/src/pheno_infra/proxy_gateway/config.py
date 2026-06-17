"""Config types for :mod:`pheno.infra.proxy_gateway`."""

from __future__ import annotations

import time
from typing import Any


class UpstreamConfig:
    """Configuration for an upstream service and its health state."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8000,
        path_prefix: str = "",
        health_check_interval: float = 5.0,
        health_check_timeout: float = 2.0,
        service_name: str | None = None,
        tenant: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.host = host
        self.port = port
        self.path_prefix = path_prefix.rstrip("/")
        self.health_check_interval = health_check_interval
        self.health_check_timeout = health_check_timeout
        self.service_name = service_name
        self.tenant = tenant
        self.metadata = metadata or {}
        self.is_healthy = False
        self.last_health_check = 0.0
        # Track when a health transition last occurred; initialise to creation time.
        self.last_state_change = time.time()


__all__ = ["UpstreamConfig"]
