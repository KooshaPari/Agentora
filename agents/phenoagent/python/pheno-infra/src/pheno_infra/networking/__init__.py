"""KInfra Networking package (canonicalized from legacy kinfra_networking module).

Public API remains compatible; prefer importing from pheno.infra.networking.
"""

from .frameworks import (
    detect_framework,
    start_fastapi_with_smart_networking,
    start_flask_with_smart_networking,
)
from .health_checks import wait_for_health
from .options import (
    DefaultLogger,
    Logger,
    NetworkingOptions,
    NetworkStartResult,
    TunnelConfig,
)
from .ports import allocate_free_port
from .server import get_networking_config_from_env, start_server_with_smart_networking
from .tunnel_setup import (
    create_kinfra_tunnel_if_enabled,
    ensure_named_tunnel_autocreate,
    ensure_named_tunnel_route,
)

__all__ = [
    "DefaultLogger",
    "Logger",
    "NetworkStartResult",
    "NetworkingOptions",
    "TunnelConfig",
    "allocate_free_port",
    "create_kinfra_tunnel_if_enabled",
    "detect_framework",
    "ensure_named_tunnel_autocreate",
    "ensure_named_tunnel_route",
    "get_networking_config_from_env",
    "start_fastapi_with_smart_networking",
    "start_flask_with_smart_networking",
    "start_server_with_smart_networking",
    "wait_for_health",
]
