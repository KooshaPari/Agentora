"""
KInfra Utilities - Common utilities extracted from various KInfra modules.

This package contains reusable utility functions for:
- Process management (port checking, process termination)
- Health checking (HTTP/TCP health probes)
- DNS utilities (DNS-safe slug generation)
"""

from .dns import (
    dns_safe_slug,
)
from .health import (
    check_http_health,
    check_tcp_health,
)
from .process import (
    cleanup_orphaned_processes,
    get_port_occupant,
    is_port_free,
    kill_processes_on_port,
    terminate_process,
)

__all__ = [
    # Health check utilities
    "check_http_health",
    "check_tcp_health",
    "cleanup_orphaned_processes",
    # DNS utilities
    "dns_safe_slug",
    "get_port_occupant",
    # Process utilities
    "is_port_free",
    "kill_processes_on_port",
    "terminate_process",
]
