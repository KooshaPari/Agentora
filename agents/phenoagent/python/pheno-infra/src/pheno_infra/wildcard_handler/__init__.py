"""Wildcard handler package.

Exposes WildcardStatusHandler and create_wildcard_handler.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..status_page import StatusPageGenerator
from .handler import WildcardStatusHandler

__all__ = ["WildcardStatusHandler", "create_wildcard_handler"]


def create_wildcard_handler(
    service_name: str,
    domain: str,
    routes: list[dict[str, str]],
    version: str = "1.0.0",
    description: str = "",
    health_status: dict[str, Any] | None = None,
    environment: str = "production",
    **kwargs,
) -> WildcardStatusHandler:
    status_generator = StatusPageGenerator(
        service_name=service_name,
        domain=domain,
        version=version,
        description=description,
        docs_url=kwargs.get("docs_url"),
        support_url=kwargs.get("support_url"),
    )
    return WildcardStatusHandler(
        status_generator=status_generator,
        available_routes=routes,
        health_status=health_status or {"status": "healthy", "checks": {}},
        environment=environment,
        uptime=kwargs.get("uptime"),
        metrics=kwargs.get("metrics"),
        enable_suggestions=kwargs.get("enable_suggestions", True),
    )
