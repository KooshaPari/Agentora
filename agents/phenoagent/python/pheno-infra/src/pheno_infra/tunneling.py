"""Canonical tunneling helpers for KInfra (namespace wrapper).

Note: This module re-exports the public API from the legacy top-level
module `tunnel_manager` to provide a stable namespaced import path:
    from pheno.infra.tunneling import AsyncTunnelManager, SyncTunnelManager
"""

# Re-export everything from the legacy module
from tunnel_manager import *  # noqa: F403
