"""OpenTelemetry helpers for pheno.observability.

All imports are optional; functions raise clear ImportError if OTel packages are
missing.
"""

from __future__ import annotations

from typing import Any

__all__ = ["configure_otel", "get_meter_provider", "get_tracer_provider"]

_tracer_provider: Any | None = None
_meter_provider: Any | None = None


def configure_otel(
    *,
    service_name: str,
    service_version: str = "0.1.0",
    environment: str = "dev",
    enable_tracing: bool = True,
    enable_metrics: bool = True,
    otlp_endpoint: str | None = None,
    console_export: bool = False,
) -> None:
    """Configure OpenTelemetry tracing and metrics providers.

    Minimal wrapper that prefers OTLP exporters when available and can optionally export
    to console for local development.
    """
    try:
        from opentelemetry import metrics as _metrics
        from opentelemetry import trace as _trace
        from opentelemetry.sdk.metrics import MeterProvider as _MeterProvider
        from opentelemetry.sdk.metrics.export import (
            ConsoleMetricExporter as _ConsoleMetricExporter,
        )
        from opentelemetry.sdk.metrics.export import (
            PeriodicExportingMetricReader as _PeriodicExportingMetricReader,
        )
        from opentelemetry.sdk.resources import Resource as _Resource
        from opentelemetry.sdk.trace import TracerProvider as _TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor as _BatchSpanProcessor,
        )
        from opentelemetry.sdk.trace.export import (
            ConsoleSpanExporter as _ConsoleSpanExporter,
        )
    except ImportError as e:  # pragma: no cover
        raise ImportError(
            "OpenTelemetry SDK not installed. Install: pip install opentelemetry-api opentelemetry-sdk",
        ) from e

    resource = _Resource.create(
        {
            "service.name": service_name,
            "service.version": service_version,
            "deployment.environment": environment,
        },
    )

    global _tracer_provider, _meter_provider

    if enable_tracing:
        _tracer_provider = _TracerProvider(resource=resource)
        if console_export:
            _tracer_provider.add_span_processor(_BatchSpanProcessor(_ConsoleSpanExporter()))
        if otlp_endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                    OTLPSpanExporter as _OTLPSpanExporter,
                )

                _tracer_provider.add_span_processor(
                    _BatchSpanProcessor(_OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)),
                )
            except ImportError:
                pass
        _trace.set_tracer_provider(_tracer_provider)

    if enable_metrics:
        readers = []
        if console_export:
            readers.append(
                _PeriodicExportingMetricReader(
                    _ConsoleMetricExporter(), export_interval_millis=10000,
                ),
            )
        if otlp_endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
                    OTLPMetricExporter as _OTLPMetricExporter,
                )

                readers.append(
                    _PeriodicExportingMetricReader(
                        _OTLPMetricExporter(endpoint=otlp_endpoint, insecure=True),
                        export_interval_millis=60000,
                    ),
                )
            except ImportError:
                pass
        _meter_provider = _MeterProvider(resource=resource, metric_readers=readers)
        _metrics.set_meter_provider(_meter_provider)


def get_tracer_provider() -> Any | None:
    return _tracer_provider


def get_meter_provider() -> Any | None:
    return _meter_provider
