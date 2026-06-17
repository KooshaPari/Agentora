"""Fallback server package.

Exposes FallbackServer and run_fallback_server.
"""

from __future__ import annotations

from .server import FallbackServer, run_fallback_server

__all__ = ["FallbackServer", "run_fallback_server"]
