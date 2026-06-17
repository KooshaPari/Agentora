"""Proxy server package.

Exposes ProxyServer, UpstreamConfig, run_smart_proxy.
"""

from __future__ import annotations

from .config import UpstreamConfig
from .server import ProxyServer, run_smart_proxy

__all__ = ["ProxyServer", "UpstreamConfig", "run_smart_proxy"]
