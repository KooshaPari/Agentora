"""Interceptors for gRPC client/server with OpenTelemetry + auth metadata.

This file only defines interfaces and thin defaults. Actual OTEL exporter setup is left
to the service (see observability guide).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

try:
    import grpc
except Exception:  # pragma: no cover
    grpc = None  # type: ignore


class ClientTelemetryInterceptor:
    """
    ClientInterceptor adding trace context to metadata.
    """

    def __init__(self, get_headers: Callable[[], dict[str, str]] | None = None):
        self._get_headers = get_headers or (dict)

    def intercept_unary_unary(self, continuation, client_call_details, request):  # type: ignore[no-any-unimported]
        if grpc is None:  # pragma: no cover
            return continuation(client_call_details, request)
        metadata = (
            [] if client_call_details.metadata is None else list(client_call_details.metadata)
        )
        # Inject custom headers (correlation id, traceparent, etc.)
        for k, v in self._get_headers().items():
            metadata.append((k, v))
        new_details = client_call_details._replace(metadata=metadata)  # type: ignore[attr-defined]
        return continuation(new_details, request)


class ServerTelemetryInterceptor:
    """
    ServerInterceptor extracting trace/correlation metadata for logging/OTEL.
    """

    def __init__(self, on_metadata: Callable[[dict[str, str]], None] | None = None):
        self._on_metadata = on_metadata or (lambda _: None)

    def intercept_service(self, continuation, handler_call_details):  # type: ignore[no-any-unimported]
        if grpc is None:  # pragma: no cover
            return continuation(handler_call_details)
        md = dict(handler_call_details.invocation_metadata or [])
        self._on_metadata(md)
        return continuation(handler_call_details)


class MetadataAuthInterceptor:
    """
    Server-side auth check via metadata (e.g., bearer tokens).
    """

    def __init__(self, authorize: Callable[[dict[str, str]], bool]):
        self._authorize = authorize

    def intercept_service(self, continuation, handler_call_details):  # type: ignore[no-any-unimported]
        if grpc is None:  # pragma: no cover
            return continuation(handler_call_details)
        md = dict(handler_call_details.invocation_metadata or [])
        if not self._authorize(md):
            # Minimal raise; in real code, raise appropriate grpc.RpcError
            raise PermissionError("unauthorized")
        return continuation(handler_call_details)


class ServerSpanAttributesInterceptor:
    """
    Server interceptor that adds request metadata as span attributes if OTel is present.
    """

    def __init__(self, attr_prefix: str = "rpc."):
        self._prefix = attr_prefix

    def intercept_service(self, continuation, handler_call_details):  # type: ignore[no-any-unimported]
        if grpc is None:  # pragma: no cover
            return continuation(handler_call_details)
        try:
            from opentelemetry import trace  # type: ignore
        except Exception:
            return continuation(handler_call_details)
        span = trace.get_current_span()
        if span and handler_call_details.invocation_metadata:
            md = dict(handler_call_details.invocation_metadata)
            for k, v in md.items():
                # Avoid overly verbose values
                if len(str(v)) <= 256:
                    span.set_attribute(f"{self._prefix}metadata.{k}", v)
        return continuation(handler_call_details)


class ClientSpanAttributesInterceptor:
    """
    Client interceptor that adds request metadata as span attributes if OTel is present.
    """

    def __init__(self, attr_prefix: str = "rpc."):
        self._prefix = attr_prefix

    def intercept_unary_unary(self, continuation, client_call_details, request):  # type: ignore[no-any-unimported]
        if grpc is None:  # pragma: no cover
            return continuation(client_call_details, request)
        try:
            from opentelemetry import trace  # type: ignore
        except Exception:
            return continuation(client_call_details, request)
        span = trace.get_current_span()
        if span and client_call_details.metadata:
            for k, v in client_call_details.metadata:
                if len(str(v)) <= 256:
                    span.set_attribute(f"{self._prefix}metadata.{k}", v)
        return continuation(client_call_details, request)
