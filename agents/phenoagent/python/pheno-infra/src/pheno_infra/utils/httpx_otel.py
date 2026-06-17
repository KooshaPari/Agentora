"""Utilities to attach OpenTelemetry event hooks to httpx clients, if available.

This is a no-op unless pydevkit.http.otel_hooks is installed and exposes
HTTPX event hooks. It safely merges those hooks with any existing hooks
provided by the caller.

Targets: Python 3.12+.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


def _load_pydevkit_httpx_hooks() -> Mapping[str, Sequence]:
    """Best-effort import of pydevkit's HTTPX OTel hooks.

    Tries a few likely attribute names and returns a dict compatible with httpx's
    event_hooks parameter: {"request": [callables], "response": [callables]}. Returns an
    empty mapping on any failure.
    """
    try:
        # Import module lazily to avoid hard dependency
        from pheno.dev.http import otel_hooks  # type: ignore
    except Exception:
        return {}

    candidates = (
        "get_httpx_event_hooks",
        "build_httpx_event_hooks",
        "httpx_event_hooks",
        "make_httpx_event_hooks",
    )

    for name in candidates:
        try:
            if not hasattr(otel_hooks, name):
                continue
            obj = getattr(otel_hooks, name)
            value = obj() if callable(obj) else obj  # try calling if it's a factory
            if isinstance(value, dict):
                # Basic shape check
                req = value.get("request")
                resp = value.get("response")
                if isinstance(req, (list, tuple)) or req is None:
                    if isinstance(resp, (list, tuple)) or resp is None:
                        return value  # type: ignore[return-value]
        except Exception:
            # Try next candidate name
            continue

    return {}


def apply_httpx_otel_event_hooks(kwargs: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Merge pydevkit's HTTPX OTel event hooks (if present) into client kwargs.

    Example:
        async with httpx.AsyncClient(**apply_httpx_otel_event_hooks({})) as client:
            ...
    """
    base: dict[str, Any] = dict(kwargs or {})

    hooks = _load_pydevkit_httpx_hooks()
    if not hooks:
        return base

    existing = base.get("event_hooks") or {}
    merged_hooks: dict[str, list] = {
        "request": list(existing.get("request", [])),
        "response": list(existing.get("response", [])),
    }

    for key in ("request", "response"):
        extra = hooks.get(key) or []
        if isinstance(extra, (list, tuple)):
            merged_hooks[key].extend(list(extra))
        elif callable(extra):  # defensive: accept a single callable
            merged_hooks[key].append(extra)  # type: ignore[arg-type]

    base["event_hooks"] = merged_hooks
    return base
