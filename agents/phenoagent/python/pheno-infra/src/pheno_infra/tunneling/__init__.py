"""KInfra Tunneling package (canonicalized from legacy tunnel_manager module).

Public API remains compatible; prefer importing from pheno.infra.tunneling.
"""

from .asyncio_impl import AsyncTunnelManager
from .base import BaseTunnelManager
from .cleanup import (
    async_cleanup_all_tunnels,
    cleanup_all_tunnels,
    cleanup_orphaned_cloudflared_processes,
    cleanup_runtime_environment,
)
from .convenience import (
    create_async_quick_tunnel,
    create_persistent_tunnel,
    create_quick_tunnel,
    pytest_async_tunnel_manager,
    pytest_sync_tunnel_manager,
    pytest_tunnel_config,
)
from .registry import TunnelRegistry, tunnel_registry
from .sync_impl import SyncTunnelManager
from .types import (
    CloudflareTunnelError,
    TunnelConfig,
    TunnelConfigurationError,
    TunnelInfo,
    TunnelNotFoundError,
    TunnelOperationError,
    TunnelProtocol,
    TunnelStatus,
    TunnelType,
)

__all__ = [
    "AsyncTunnelManager",
    "BaseTunnelManager",
    "CloudflareTunnelError",
    "SyncTunnelManager",
    "TunnelConfig",
    "TunnelConfigurationError",
    "TunnelInfo",
    "TunnelNotFoundError",
    "TunnelOperationError",
    "TunnelProtocol",
    "TunnelRegistry",
    "TunnelStatus",
    "TunnelType",
    "async_cleanup_all_tunnels",
    "cleanup_all_tunnels",
    "cleanup_orphaned_cloudflared_processes",
    "cleanup_runtime_environment",
    "create_async_quick_tunnel",
    "create_persistent_tunnel",
    "create_quick_tunnel",
    "pytest_async_tunnel_manager",
    "pytest_sync_tunnel_manager",
    "pytest_tunnel_config",
    "tunnel_registry",
]
