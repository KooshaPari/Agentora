"""
Convenience functions and pytest fixtures for tunneling managers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .asyncio_impl import AsyncTunnelManager
from .sync_impl import SyncTunnelManager
from .types import TunnelConfig, TunnelType

if TYPE_CHECKING:
    from pathlib import Path


def pytest_tunnel_config() -> TunnelConfig:
    return TunnelConfig(
        name="test-tunnel",
        local_url="http://0.0.0.0:8000",
        tunnel_type=TunnelType.QUICK,
        log_level="debug",
    )


def pytest_sync_tunnel_manager(tunnel_config: TunnelConfig | None = None) -> SyncTunnelManager:
    config = tunnel_config or pytest_tunnel_config()
    return SyncTunnelManager(config)


def pytest_async_tunnel_manager(tunnel_config: TunnelConfig | None = None) -> AsyncTunnelManager:
    config = tunnel_config or pytest_tunnel_config()
    return AsyncTunnelManager(config)


def create_quick_tunnel(
    name: str, local_url: str, hostname: str | None = None,
) -> SyncTunnelManager:
    config = TunnelConfig(
        name=name, local_url=local_url, hostname=hostname, tunnel_type=TunnelType.QUICK,
    )
    return SyncTunnelManager(config)


async def create_async_quick_tunnel(
    name: str, local_url: str, hostname: str | None = None,
) -> AsyncTunnelManager:
    config = TunnelConfig(
        name=name, local_url=local_url, hostname=hostname, tunnel_type=TunnelType.QUICK,
    )
    return AsyncTunnelManager(config)


def create_persistent_tunnel(
    name: str,
    local_url: str,
    hostname: str,
    credentials_file: Path | None = None,
    tunnel_token: str | None = None,
) -> SyncTunnelManager:
    config = TunnelConfig(
        name=name,
        local_url=local_url,
        hostname=hostname,
        tunnel_type=TunnelType.PERSISTENT,
        credentials_file=str(credentials_file) if credentials_file else None,
        tunnel_token=tunnel_token,
    )
    return SyncTunnelManager(config)
