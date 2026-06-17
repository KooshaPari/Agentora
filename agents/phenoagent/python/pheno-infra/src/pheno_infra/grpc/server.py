"""GRPC server helpers with DI integration and observability.

Provides lightweight wrappers for creating gRPC servers with:
- Dependency injection via adapter-kit Container
- Interceptor composition (telemetry, auth, metadata)
- Configuration via config-kit
- Graceful shutdown handling

See: docs/adr/0003-grpc-kit.md
"""

from __future__ import annotations

import logging
from typing import Any

try:
    import grpc
    from grpc import aio

    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False
    grpc = None  # type: ignore
    aio = None  # type: ignore

# Optional DI integration
try:
    from adapter_kit import Container

    DI_AVAILABLE = True
except ImportError:
    DI_AVAILABLE = False
    Container = None  # type: ignore

logger = logging.getLogger(__name__)


class GrpcServerConfig:
    """Configuration for gRPC server.

    Can be used standalone or with config-kit integration.
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 50051,
        max_workers: int = 10,
        max_concurrent_rpcs: int | None = None,
        # Keepalive settings
        keepalive_time_ms: int = 10000,
        keepalive_timeout_ms: int = 5000,
        keepalive_permit_without_calls: bool = True,
        # TLS/SSL
        ssl_private_key: str | None = None,
        ssl_certificate: str | None = None,
        # Options
        options: list[tuple[str, Any]] | None = None,
    ):
        self.host = host
        self.port = port
        self.max_workers = max_workers
        self.max_concurrent_rpcs = max_concurrent_rpcs
        self.keepalive_time_ms = keepalive_time_ms
        self.keepalive_timeout_ms = keepalive_timeout_ms
        self.keepalive_permit_without_calls = keepalive_permit_without_calls
        self.ssl_private_key = ssl_private_key
        self.ssl_certificate = ssl_certificate
        self.options = options or []

    def to_options(self) -> list[tuple[str, Any]]:
        """
        Convert config to gRPC options.
        """
        opts = list(self.options)

        # Keepalive options
        opts.extend(
            [
                ("grpc.keepalive_time_ms", self.keepalive_time_ms),
                ("grpc.keepalive_timeout_ms", self.keepalive_timeout_ms),
                (
                    "grpc.keepalive_permit_without_calls",
                    1 if self.keepalive_permit_without_calls else 0,
                ),
            ],
        )

        # Concurrent RPC limit
        if self.max_concurrent_rpcs:
            opts.append(("grpc.max_concurrent_streams", self.max_concurrent_rpcs))

        return opts

    @property
    def address(self) -> str:
        """
        Get server address string.
        """
        return f"{self.host}:{self.port}"


class GrpcServer:
    """Lightweight gRPC server wrapper with DI and interceptor support.

    Example:
        >>> config = GrpcServerConfig(host="0.0.0.0", port=50051)
        >>> server = GrpcServer(config)
        >>>
        >>> # Add interceptors
        >>> server.add_interceptor(ServerTelemetryInterceptor())
        >>>
        >>> # Register services
        >>> from my_pb2_grpc import add_MyServiceServicer_to_server
        >>> add_MyServiceServicer_to_server(MyServiceImpl(), server.server)
        >>>
        >>> # Start server
        >>> await server.start()
        >>> await server.wait_for_termination()
    """

    def __init__(
        self,
        config: GrpcServerConfig,
        container: Container | None = None,
        interceptors: list[Any] | None = None,
    ):
        if not GRPC_AVAILABLE:
            raise ImportError("grpcio not installed. Install with: pip install grpcio grpcio-tools")

        self.config = config
        self.container = container
        self._interceptors = interceptors or []
        self._server: aio.Server | None = None

    def add_interceptor(self, interceptor: Any) -> None:
        """
        Add a server interceptor.
        """
        self._interceptors.append(interceptor)

    async def start(self) -> None:
        """
        Start the gRPC server.
        """
        if self._server is not None:
            logger.warning("Server already started")
            return

        # Create server with interceptors
        self._server = aio.server(
            interceptors=self._interceptors,
            options=self.config.to_options(),
        )

        # Add insecure port (or secure if TLS configured)
        if self.config.ssl_private_key and self.config.ssl_certificate:
            with open(self.config.ssl_private_key, "rb") as f:
                private_key = f.read()
            with open(self.config.ssl_certificate, "rb") as f:
                certificate_chain = f.read()

            credentials = grpc.ssl_server_credentials([(private_key, certificate_chain)])
            self._server.add_secure_port(self.config.address, credentials)
            logger.info(f"gRPC server starting with TLS at {self.config.address}")
        else:
            self._server.add_insecure_port(self.config.address)
            logger.info(f"gRPC server starting (insecure) at {self.config.address}")

        await self._server.start()
        logger.info("gRPC server started")

    async def stop(self, grace: float = 5.0) -> None:
        """
        Stop the gRPC server gracefully.
        """
        if self._server is None:
            return

        logger.info(f"Stopping gRPC server (grace={grace}s)...")
        await self._server.stop(grace)
        self._server = None
        logger.info("gRPC server stopped")

    async def wait_for_termination(self) -> None:
        """
        Wait for server termination.
        """
        if self._server is None:
            raise RuntimeError("Server not started")

        await self._server.wait_for_termination()

    @property
    def server(self) -> aio.Server:
        """
        Get the underlying gRPC server instance.
        """
        if self._server is None:
            raise RuntimeError("Server not started. Call start() first.")
        return self._server


def create_server(
    config: GrpcServerConfig,
    interceptors: list[Any] | None = None,
    container: Container | None = None,
) -> GrpcServer:
    """Create a gRPC server with interceptors.

    Args:
        config: Server configuration
        interceptors: List of server interceptors
        container: Optional DI container for service dependencies

    Returns:
        GrpcServer instance ready to register services

    Example:
        >>> from grpc_kit import create_server, GrpcServerConfig
        >>> from grpc_kit.interceptors import ServerTelemetryInterceptor
        >>>
        >>> config = GrpcServerConfig(port=50051)
        >>> server = create_server(
        ...     config,
        ...     interceptors=[ServerTelemetryInterceptor()],
        ... )
        >>>
        >>> # Register your services
        >>> # add_YourServiceServicer_to_server(YourService(), server.server)
        >>>
        >>> await server.start()
    """
    return GrpcServer(config=config, container=container, interceptors=interceptors)


__all__ = [
    "GrpcServer",
    "GrpcServerConfig",
    "create_server",
]
