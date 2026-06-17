"""
KInfra: Cross-platform infrastructure orchestration toolkit.

This kit provides comprehensive infrastructure management for dynamic services:
- Port allocation and conflict resolution
- Tunnel management and health monitoring
- Service lifecycle orchestration
- Process management and cleanup
- Proxy server with smart routing
- Resource management and adapters
- Fallback server capabilities

Features:
- Dynamic port allocation with persistence
- Secure tunnel synchronization (cloudflared, ngrok)
- Service health checks (HTTP, TCP, custom)
- Process isolation and management
- Smart proxy with upstream failover
- Resource adapters (database, cache, queue)
- Middleware helpers for common patterns
- DNS-safe slug generation
- Orphaned process cleanup
- Service dependency resolution
"""

from typing import Dict, List, Optional

# Utility modules
from . import adapters, middleware_helpers, templates

# NEW: Core managers (consolidated)
from .core import (
    CleanupManager,
    Tunnel,
    TunnelConfig,
)
from .core import (
    PortManager as CorePortManager,
)
from .core import (
    ResourceManager as CoreResourceManager,
)
from .core import (
    TunnelManager as CoreTunnelManager,
)

# Exceptions
from .exceptions import (
    KInfraError,
    PortAllocationError,
    ServiceConflictError,
    ServiceError,
    TunnelError,
)
from .fallback_server import FallbackServer, run_fallback_server

# Core infrastructure
from .kinfra import KInfra
from .orchestrator import OrchestratorConfig, ServiceOrchestrator

# Port management (legacy - use core.PortManager instead)
from .port_allocator import PortAllocator, SmartPortAllocator
from .port_registry import PortRegistry, ServiceInfo

# Proxy and fallback servers
from .proxy_server import SmartProxyServer, UpstreamConfig, run_smart_proxy

# Resource management (legacy - use core.ResourceManager instead)
from .resource_manager import ResourceManager

# Service orchestration
from .service_manager import (
    ResourceConfig,
    ResourceStatus,
    ServiceConfig,
    ServiceManager,
    ServiceStatus,
)

# Legacy support (deprecated, will be removed in v2.0)
from .smart_infra_manager import SmartInfraManager, get_smart_infra_manager

# NEW: Startup framework
from .startup import StartupConfig, UnifiedStartup

# Tunnel management (legacy - use core.TunnelManager instead)
from .tunnel_sync import TunnelInfo, TunnelManager

# Utility functions - DNS
from .utils.dns import dns_safe_slug

# Utility functions - Health checks
from .utils.health import (
    check_http_health,
    check_tcp_health,
    check_tunnel_health,
)

# Utility functions - Process management
from .utils.process import (
    cleanup_orphaned_processes,
    get_port_occupant,
    is_port_free,
    kill_processes_on_port,
    terminate_process,
)

__version__ = "1.0.0"
__kit_name__ = "infra"

__all__ = [
    "CleanupManager",
    "CorePortManager",
    # NEW: Core managers (canonical - use these!)
    "CoreResourceManager",
    "CoreTunnelManager",
    # Servers
    "FallbackServer",
    # Core
    "KInfra",
    # Exceptions
    "KInfraError",
    "OrchestratorConfig",
    "PortAllocationError",
    "PortAllocator",
    # Port management (legacy - use CorePortManager)
    "PortRegistry",
    "ResourceConfig",
    # Resource management (legacy - use CoreResourceManager)
    "ResourceManager",
    "ResourceStatus",
    "ServiceConfig",
    "ServiceConflictError",
    "ServiceError",
    "ServiceInfo",
    # Service orchestration
    "ServiceManager",
    "ServiceOrchestrator",
    "ServiceStatus",
    # Legacy (deprecated)
    "SmartInfraManager",
    "SmartPortAllocator",
    "SmartProxyServer",
    "StartupConfig",
    "Tunnel",
    "TunnelConfig",
    "TunnelError",
    "TunnelInfo",
    # Tunnel management (legacy - use CoreTunnelManager)
    "TunnelManager",
    # NEW: Startup framework
    "UnifiedStartup",
    "UpstreamConfig",
    # Modules
    "adapters",
    # Health check utilities
    "check_http_health",
    "check_tcp_health",
    "check_tunnel_health",
    "cleanup_orphaned_processes",
    # DNS utilities
    "dns_safe_slug",
    "get_port_occupant",
    "get_smart_infra_manager",
    # Process utilities
    "is_port_free",
    "kill_processes_on_port",
    "middleware_helpers",
    "run_fallback_server",
    "run_smart_proxy",
    "templates",
    "terminate_process",
]
