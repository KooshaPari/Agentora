"""
Tunnel registry for managing multiple tunnel instances.
"""

from __future__ import annotations

from .asyncio_impl import AsyncTunnelManager
from .sync_impl import SyncTunnelManager
from .types import TunnelNotFoundError


class TunnelRegistry:
    def __init__(self) -> None:
        self._tunnels: dict[str, SyncTunnelManager | AsyncTunnelManager] = {}
        import logging

        self.logger = logging.getLogger(f"{__name__}.TunnelRegistry")

    def register_sync_tunnel(self, name: str, manager: SyncTunnelManager) -> None:
        self._tunnels[name] = manager
        self.logger.info(f"Registered sync tunnel: {name}")

    def register_async_tunnel(self, name: str, manager: AsyncTunnelManager) -> None:
        self._tunnels[name] = manager
        self.logger.info(f"Registered async tunnel: {name}")

    def get_tunnel(self, name: str) -> SyncTunnelManager | AsyncTunnelManager:
        if name not in self._tunnels:
            raise TunnelNotFoundError(f"Tunnel '{name}' not found in registry")
        return self._tunnels[name]

    def list_tunnels(self) -> list[str]:
        return list(self._tunnels.keys())

    def stop_all_sync_tunnels(self) -> bool:
        success = True
        for name, tunnel in self._tunnels.items():
            if isinstance(tunnel, SyncTunnelManager):
                try:
                    tunnel.stop()
                except Exception as e:
                    self.logger.exception(f"Failed to stop tunnel {name}: {e}")
                    success = False
        return success

    async def stop_all_async_tunnels(self) -> bool:
        success = True
        for name, tunnel in self._tunnels.items():
            if isinstance(tunnel, AsyncTunnelManager):
                try:
                    await tunnel.stop()
                except Exception as e:
                    self.logger.exception(f"Failed to stop tunnel {name}: {e}")
                    success = False
        return success


tunnel_registry = TunnelRegistry()
