"""GRPC client helpers with DI integration and observability.

Provides lightweight wrappers for creating gRPC clients with:
- Interceptor composition (telemetry, auth, correlation)
- Connection management and pooling
- Retry and timeout configuration
- DI integration via adapter-kit

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

logger = logging.getLogger(__name__)


class GrpcClientConfig:
    """Configuration for gRPC client.

    Can be used standalone or with config-kit integration.
    """

    def __init__(
        self,
        target: str,
        # Connection settings
        max_receive_message_length: int = 4 * 1024 * 1024,  # 4MB
        max_send_message_length: int = 4 * 1024 * 1024,  # 4MB
        # Keepalive settings
        keepalive_time_ms: int = 10000,
        keepalive_timeout_ms: int = 5000,
        keepalive_permit_without_calls: bool = True,
        # Retry/timeout
        enable_retries: bool = True,
        # TLS/SSL
        ssl_root_certificates: str | None = None,
        # Options
        options: list[tuple[str, Any]] | None = None,
    ):
        self.target = target
        self.max_receive_message_length = max_receive_message_length
        self.max_send_message_length = max_send_message_length
        self.keepalive_time_ms = keepalive_time_ms
        self.keepalive_timeout_ms = keepalive_timeout_ms
        self.keepalive_permit_without_calls = keepalive_permit_without_calls
        self.enable_retries = enable_retries
        self.ssl_root_certificates = ssl_root_certificates
        self.options = options or []

    def to_options(self) -> list[tuple[str, Any]]:
        """
        Convert config to gRPC options.
        """
        opts = list(self.options)

        # Message size limits
        opts.extend(
            [
                ("grpc.max_receive_message_length", self.max_receive_message_length),
                ("grpc.max_send_message_length", self.max_send_message_length),
            ],
        )

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

        # Retry configuration
        if self.enable_retries:
            opts.append(("grpc.enable_retries", 1))

        return opts


class GrpcChannel:
    """Lightweight gRPC channel wrapper with interceptor support.

    Example:
        >>> config = GrpcClientConfig(target="localhost:50051")
        >>> channel = GrpcChannel(config)
        >>>
        >>> # Add interceptors
        >>> channel.add_interceptor(ClientTelemetryInterceptor())
        >>>
        >>> # Create stub
        >>> from my_pb2_grpc import MyServiceStub
        >>> stub = MyServiceStub(channel.channel)
        >>>
        >>> # Make calls
        >>> response = await stub.MyMethod(request)
        >>>
        >>> # Close when done
        >>> await channel.close()
    """

    def __init__(
        self,
        config: GrpcClientConfig,
        interceptors: list[Any] | None = None,
    ):
        if not GRPC_AVAILABLE:
            raise ImportError("grpcio not installed. Install with: pip install grpcio grpcio-tools")

        self.config = config
        self._interceptors = interceptors or []
        self._channel: aio.Channel | None = None
        self._create_channel()

    def _create_channel(self) -> None:
        """
        Create the underlying gRPC channel.
        """
        # Create channel (insecure or secure)
        if self.config.ssl_root_certificates:
            with open(self.config.ssl_root_certificates, "rb") as f:
                root_certificates = f.read()

            credentials = grpc.ssl_channel_credentials(root_certificates)
            self._channel = aio.secure_channel(
                self.config.target,
                credentials,
                options=self.config.to_options(),
            )
            logger.info(f"gRPC channel created with TLS to {self.config.target}")
        else:
            self._channel = aio.insecure_channel(
                self.config.target,
                options=self.config.to_options(),
            )
            logger.info(f"gRPC channel created (insecure) to {self.config.target}")

        # Apply interceptors
        if self._interceptors:
            self._channel = grpc.intercept_channel(self._channel, *self._interceptors)

    def add_interceptor(self, interceptor: Any) -> None:
        """Add a client interceptor.

        Note: Must be called before creating stubs for the interceptor to take effect.
        """
        self._interceptors.append(interceptor)
        # Recreate channel with new interceptor
        if self._channel:
            self._create_channel()

    async def close(self) -> None:
        """
        Close the gRPC channel.
        """
        if self._channel is None:
            return

        await self._channel.close()
        logger.info(f"gRPC channel closed to {self.config.target}")
        self._channel = None

    async def wait_for_ready(self, timeout: float = 10.0) -> bool:
        """Wait for channel to be ready.

        Args:
            timeout: Timeout in seconds

        Returns:
            True if ready, False if timeout
        """
        if self._channel is None:
            return False

        try:
            await grpc.channel_ready_future(self._channel).wait(timeout=timeout)
            return True
        except grpc.FutureTimeoutError:
            return False

    @property
    def channel(self) -> aio.Channel:
        """
        Get the underlying gRPC channel.
        """
        if self._channel is None:
            raise RuntimeError("Channel closed or not initialized")
        return self._channel


def create_channel(
    target: str,
    interceptors: list[Any] | None = None,
    config: GrpcClientConfig | None = None,
) -> GrpcChannel:
    """Create a gRPC channel with interceptors.

    Args:
        target: Server address (host:port)
        interceptors: List of client interceptors
        config: Optional client configuration (created if not provided)

    Returns:
        GrpcChannel instance ready to create stubs

    Example:
        >>> from grpc_kit import create_channel
        >>> from grpc_kit.interceptors import ClientTelemetryInterceptor
        >>> from my_pb2_grpc import MyServiceStub
        >>>
        >>> channel = create_channel(
        ...     "localhost:50051",
        ...     interceptors=[ClientTelemetryInterceptor()],
        ... )
        >>>
        >>> stub = MyServiceStub(channel.channel)
        >>> response = await stub.MyMethod(request)
        >>>
        >>> await channel.close()
    """
    if config is None:
        config = GrpcClientConfig(target=target)

    return GrpcChannel(config=config, interceptors=interceptors)


__all__ = [
    "GrpcChannel",
    "GrpcClientConfig",
    "create_channel",
]
