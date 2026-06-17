"""
Bootstrap utilities for OpenTelemetry and Prometheus (pheno.observability).
"""

from __future__ import annotations

from typing import Any

from .otel import configure_otel as _configure_otel

__all__ = ["add_prometheus_endpoint", "init_otel"]


def init_otel(
    *,
    service_name: str,
    environment: str | None = None,
    otlp_endpoint: str | None = None,
    fastapi_app: Any | None = None,
) -> None:
    """
    Initialize OTel tracing (and metrics provider via configure_otel) and optionally
    instrument FastAPI.
    """
    try:
        _configure_otel(
            service_name=service_name,
            environment=environment or "dev",
            otlp_endpoint=otlp_endpoint,
            enable_tracing=True,
            enable_metrics=True,
        )
        if fastapi_app is not None:
            from opentelemetry.instrumentation.fastapi import (
                FastAPIInstrumentor as _FastAPIInstrumentor,
            )

            _FastAPIInstrumentor.instrument_app(fastapi_app)
    except ImportError:
        # If OpenTelemetry not installed, be a no-op; callers can gate on optional deps
        pass


def add_prometheus_endpoint(app: Any, path: str = "/metrics") -> None:
    """
    Add a /metrics endpoint backed by prometheus_client for FastAPI/Starlette apps.
    """
    try:
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
    except Exception as e:  # pragma: no cover
        raise ImportError(
            "prometheus_client not installed. Install with: pip install prometheus-client",
        ) from e

    # Try FastAPI convenient route first
    try:
        from fastapi import APIRouter, Response

        router = APIRouter()

        async def _metrics_handler(request):  # type: ignore[no-redef]
            return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

        if hasattr(app, "include_router"):
            router.add_api_route(path, _metrics_handler, methods=["GET"], include_in_schema=False)
            app.include_router(router)
            return
    except Exception:
        # Fall through to generic Starlette/ASGI
        pass

    add_route = getattr(app, "add_route", None)
    if callable(add_route):

        async def _metrics_handler(request):  # type: ignore[no-redef]
            return generate_latest()

        add_route(path, _metrics_handler, methods=["GET"])  # type: ignore[arg-type]
        return

    raise TypeError("App does not support adding routes for metrics endpoint")
