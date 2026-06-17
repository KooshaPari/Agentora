"""Constants and patterns used across cleanup modules."""

from __future__ import annotations

import os

try:
    from cloudflare import Cloudflare

    HAS_CLOUDFLARE = True
except Exception:  # pragma: no cover - optional dependency
    Cloudflare = None  # type: ignore
    HAS_CLOUDFLARE = False


try:
    import psutil  # type: ignore

    PSUTIL_AVAILABLE = True
except ImportError:  # pragma: no cover - runtime optional dependency
    PSUTIL_AVAILABLE = False


PROTECTED_PORTS: set[int] = {5432, 4222, 11434}
"""Ports that must never be terminated by automated cleanup routines."""

TUNNEL_PATTERNS = ["cloudflared", "ngrok", "localtunnel", "tunnel", "tunnel-sync"]
DNS_PATTERNS = ["dnsmasq", "unbound", "bind9", "named", "dns-server"]
RELATED_SERVICE_PATTERNS = [
    "atoms-mcp",
    "zen-mcp",
    "mcp-server",
    "fastmcp",
    "pheno-sdk",
]
