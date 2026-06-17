"""Utilities to attach OpenTelemetry tracing to aiohttp ClientSession, if available.

No hard dependency: if opentelemetry-instrumentation-aiohttp-client is missing,
this becomes a no-op and returns the original kwargs.

Targets: Python 3.12+.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping


def _build_trace_config():
    """Return an aiohttp TraceConfig if the OTel instrumentation is available.

    Uses opentelemetry.instrumentation.aiohttp_client.create_trace_config.
    Returns None if unavailable.
    """
    try:
        from opentelemetry.instrumentation.aiohttp_client import (  # type: ignore
            create_trace_config,
        )

        return create_trace_config()
    except Exception:
        return None


def apply_aiohttp_otel_kwargs(kwargs: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Merge OTel trace config into aiohttp.ClientSession kwargs if possible.

    Example:
        session = aiohttp.ClientSession(**apply_aiohttp_otel_kwargs({"timeout": timeout}))
    """
    out: dict[str, Any] = dict(kwargs or {})
    trace_config = _build_trace_config()
    if not trace_config:
        return out

    existing = out.get("trace_configs") or []
    if isinstance(existing, list):
        out["trace_configs"] = [*existing, trace_config]
    else:
        out["trace_configs"] = [trace_config]
    return out
