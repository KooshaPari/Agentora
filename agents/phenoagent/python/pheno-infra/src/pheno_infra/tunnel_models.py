"""
Tunnel Governance - Enhanced tunnel lifecycle management

Provides sophisticated tunnel management with:
- Project-specific tunnel credentials and reuse
- Tunnel lifecycle management (reuse vs recreate)
- Shared credentials per project
- Tunnel health monitoring and cleanup
- Integration with existing tunnel systems
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TunnelLifecyclePolicy(Enum):
    """
    Tunnel lifecycle policy for management.
    """

    REUSE = "reuse"
    """
    Reuse existing tunnels when possible.
    """

    RECREATE = "recreate"
    """
    Always recreate tunnels.
    """

    SMART = "smart"
    """
    Smart decision based on tunnel health and age.
    """


class TunnelCredentialScope(Enum):
    """
    Scope for tunnel credentials.
    """

    GLOBAL = "global"
    """
    Global credentials shared across all projects.
    """

    PROJECT = "project"
    """
    Project-specific credentials.
    """

    SERVICE = "service"
    """
    Service-specific credentials.
    """


@dataclass
class TunnelCredentials:
    """
    Tunnel credentials for a specific scope.
    """

    scope: TunnelCredentialScope
    """
    Scope of the credentials.
    """

    project: str | None = None
    """
    Project name (for project/service scope).
    """

    service: str | None = None
    """
    Service name (for service scope).
    """

    provider: str = "cloudflare"
    """
    Tunnel provider (cloudflare, ngrok, etc.).
    """

    credentials: dict[str, Any] = field(default_factory=dict)
    """
    Provider-specific credentials.
    """

    created_at: float = field(default_factory=time.time)
    """
    Timestamp when credentials were created.
    """

    last_used: float = field(default_factory=time.time)
    """
    Timestamp when credentials were last used.
    """

    expires_at: float | None = None
    """
    Timestamp when credentials expire (if applicable).
    """

    is_active: bool = True
    """
    Whether the credentials are active.
    """


@dataclass
class TunnelInfo:
    """
    Information about a tunnel.
    """

    tunnel_id: str
    """
    Unique tunnel identifier.
    """

    project: str | None = None
    """
    Project name.
    """

    service: str | None = None
    """
    Service name.
    """

    hostname: str = ""
    """
    Tunnel hostname.
    """

    port: int = 0
    """
    Local port being tunneled.
    """

    provider: str = "cloudflare"
    """
    Tunnel provider.
    """

    status: str = "unknown"
    """
    Tunnel status (active, inactive, error).
    """

    created_at: float = field(default_factory=time.time)
    """
    Timestamp when tunnel was created.
    """

    last_seen: float = field(default_factory=time.time)
    """
    Timestamp when tunnel was last seen.
    """

    metadata: dict[str, Any] = field(default_factory=dict)
    """
    Additional tunnel metadata.
    """

    credentials_scope: TunnelCredentialScope = TunnelCredentialScope.PROJECT
    """
    Scope of credentials used for this tunnel.
    """


@dataclass
class TunnelGovernanceConfig:
    """
    Configuration for tunnel governance.
    """

    lifecycle_policy: TunnelLifecyclePolicy = TunnelLifecyclePolicy.SMART
    """
    Tunnel lifecycle policy.
    """

    credential_scope: TunnelCredentialScope = TunnelCredentialScope.PROJECT
    """
    Default credential scope.
    """

    tunnel_reuse_threshold: float = 300.0
    """
    Threshold for tunnel reuse in seconds.
    """

    tunnel_health_check_interval: float = 30.0
    """
    Tunnel health check interval in seconds.
    """

    max_tunnel_age: float = 3600.0
    """
    Maximum tunnel age before cleanup in seconds.
    """

    enable_credential_sharing: bool = True
    """
    Whether to enable credential sharing within projects.
    """

    enable_tunnel_reuse: bool = True
    """
    Whether to enable tunnel reuse.
    """

    cleanup_stale_tunnels: bool = True
    """
    Whether to clean up stale tunnels.
    """
