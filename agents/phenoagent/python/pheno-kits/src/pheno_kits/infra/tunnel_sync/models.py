"""
Tunnel Synchronization - Automatic cloudflared tunnel management with port synchronization.
"""

import logging
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


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
    status: str = "unknown"
    created_at: float = 0.0
    last_health_check: float = 0.0

    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()
