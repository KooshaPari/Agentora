"""
Models and constants for tunnel synchronization.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

# Fallback Cloudflare API token (can be overridden via env or file)
CLOUDFLARE_API_TOKEN_FALLBACK = "F5lBjouWaymoiTgptvaWrJp-mDMLPXvHybDik_Bk"


@dataclass
class TunnelInfo:
    """
    Information about a tunnel configuration.
    """

    tunnel_id: str
    hostname: str
    config_path: str
    port: int
    process_pid: int | None = None
    status: str = "unknown"  # unknown, starting, running, stopped, error
    created_at: float = 0.0
    last_health_check: float = 0.0

    def __post_init__(self) -> None:
        if self.created_at == 0.0:
            self.created_at = time.time()


@dataclass
class TunnelEvent:
    tunnel_id: str
    status: str  # e.g., starting|ready|running|unhealthy|error|stopped
    url: str = ""
    message: str = ""
    error: Exception | None = None
    timestamp: float = time.time()
