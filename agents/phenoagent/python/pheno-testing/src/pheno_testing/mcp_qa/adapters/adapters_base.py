"""Protocol definitions for MCP-Specific Adapters.

This module defines the Protocol classes that adapters must implement:
- OAuthCacheProvider: OAuth cache operations
- ClientAdapter: MCP client communication
- TunnelProvider: Tunnel configuration and management
- ResourceMonitor: Resource monitoring
- DatabaseProvider: Database operations
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

from fastmcp import Client

logger = logging.getLogger(__name__)


class OAuthCacheProvider(Protocol):
    """Protocol for OAuth cache operations."""

    def get_cache_path(self) -> Path:
        """Get the path where OAuth tokens are cached."""
        ...

    def is_token_cached(self) -> bool:
        """Check if valid OAuth token exists in cache."""
        ...

    def clear_cache(self) -> None:
        """Clear cached OAuth token to force re-authentication."""
        ...

    async def create_client(self) -> Client:
        """Create authenticated client using cached token."""
        ...


class ClientAdapter(Protocol):
    """Protocol for MCP client communication."""

    async def call_tool(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Call MCP tool and return normalized result."""
        ...

    async def list_tools(self) -> Dict[str, Any]:
        """List available MCP tools."""
        ...

    async def ping(self) -> Dict[str, Any]:
        """Ping server for health check."""
        ...

    def get_stats(self) -> Dict[str, Any]:
        """Get adapter statistics."""
        ...


class TunnelProvider(Protocol):
    """Protocol for tunnel configuration and management."""

    def get_public_url(self) -> Optional[str]:
        """Get the public URL for the tunnel."""
        ...

    def get_local_url(self) -> str:
        """Get the local URL being tunneled."""
        ...

    def is_active(self) -> bool:
        """Check if tunnel is currently active."""
        ...

    async def start(self) -> bool:
        """Start the tunnel."""
        ...

    async def stop(self) -> bool:
        """Stop the tunnel."""
        ...


class ResourceMonitor(Protocol):
    """Protocol for resource monitoring."""

    def get_process_info(self, pid: int) -> Optional[Any]:
        """Get detailed information about a process."""
        ...

    def find_pid_by_port(self, port: int) -> Optional[int]:
        """Find PID of process listening on a port."""
        ...

    def register_process(
        self,
        name: str,
        port: Optional[int] = None,
        pid: Optional[int] = None,
        command_pattern: Optional[str] = None,
    ) -> Any:
        """Register a process for monitoring."""
        ...

    def update_process(self, name: str) -> Optional[Any]:
        """Update information for a registered process."""
        ...

    def check_health(self, name: str, health_url: Optional[str] = None) -> Any:
        """Check health of a process."""
        ...


class DatabaseProvider(Protocol):
    """Protocol for database operations."""

    async def query(
        self,
        table: str,
        *,
        select: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Execute a query on a table."""
        ...

    async def get_single(
        self,
        table: str,
        *,
        select: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get a single record from a table."""
        ...

    async def insert(
        self,
        table: str,
        data: Dict[str, Any] | List[Dict[str, Any]],
        *,
        returning: Optional[str] = None,
    ) -> Dict[str, Any] | List[Dict[str, Any]]:
        """Insert one or more records."""
        ...

    async def update(
        self,
        table: str,
        data: Dict[str, Any],
        filters: Dict[str, Any],
        *,
        returning: Optional[str] = None,
    ) -> Dict[str, Any] | List[Dict[str, Any]]:
        """Update records."""
        ...

    async def delete(self, table: str, filters: Dict[str, Any]) -> int:
        """Delete records."""
        ...


__all__ = [
    "OAuthCacheProvider",
    "ClientAdapter",
    "TunnelProvider",
    "ResourceMonitor",
    "DatabaseProvider",
]
