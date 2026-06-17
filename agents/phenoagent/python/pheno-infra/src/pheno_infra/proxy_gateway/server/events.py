"""Structured event helpers for proxy health transitions."""

from __future__ import annotations

import logging
from typing import Any

event_logger = logging.getLogger("pheno.proxy.health")


def log_health_transition(state: dict[str, Any], previous: bool | None) -> None:
    """Emit a structured event describing an upstream health transition."""

    event_logger.info(
        "proxy.health_transition",
        event="proxy.health_transition",
        tenant=state.get("tenant"),
        project=state.get("project"),
        service=state.get("service"),
        path_prefix=state.get("path_prefix"),
        host=state.get("host"),
        port=state.get("port"),
        healthy=state.get("healthy"),
        previous_healthy=previous,
        last_checked=state.get("last_checked"),
        last_changed=state.get("last_changed"),
        metadata=state.get("metadata"),
    )


__all__ = ["event_logger", "log_health_transition"]
