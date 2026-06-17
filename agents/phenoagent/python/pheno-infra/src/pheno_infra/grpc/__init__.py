"""
pheno.grpc - gRPC integration utilities

Provides gRPC interceptors, server/client helpers, and configuration.

Migrated from grpc-kit into pheno namespace.

Features:
- Interceptors: Telemetry, auth, metadata
- Server helpers: GrpcServer with config
- Client helpers: GrpcChannel with interceptors
- OpenTelemetry integration

Usage:
    from pheno.infra.grpc import GrpcServer, GrpcChannel
    from pheno.infra.grpc import ServerTelemetryInterceptor, ClientTelemetryInterceptor

    # Create server with telemetry
    server = GrpcServer(
        port=50051,
        interceptors=[ServerTelemetryInterceptor()]
    )

    # Create client channel
    channel = GrpcChannel(
        target="localhost:50051",
        interceptors=[ClientTelemetryInterceptor()]
    )
"""

from .interceptors import (
    ClientSpanAttributesInterceptor,
    ClientTelemetryInterceptor,
    MetadataAuthInterceptor,
    ServerSpanAttributesInterceptor,
    ServerTelemetryInterceptor,
)

# Server and client helpers (Task 3.1)
try:

    _HELPERS_AVAILABLE = True
except ImportError:
    _HELPERS_AVAILABLE = False

__version__ = "0.1.0"

__all__ = [
    "ClientSpanAttributesInterceptor",
    # Interceptors
    "ClientTelemetryInterceptor",
    "MetadataAuthInterceptor",
    "ServerSpanAttributesInterceptor",
    "ServerTelemetryInterceptor",
]

# Export helpers if available
if _HELPERS_AVAILABLE:
    __all__.extend(
        [
            # Client helpers
            "GrpcChannel",
            "GrpcClientConfig",
            # Server helpers
            "GrpcServer",
            "GrpcServerConfig",
            "create_channel",
            "create_server",
        ],
    )
