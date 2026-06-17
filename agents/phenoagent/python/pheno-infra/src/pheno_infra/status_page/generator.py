"""
StatusPageGenerator using UI helpers.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .ui import (
    build_status_page_html,
    generate_health_checks_html,
    generate_links_html,
    generate_metrics_html,
    generate_routes_html,
)


class StatusPageGenerator:
    def __init__(
        self,
        service_name: str,
        domain: str,
        version: str = "1.0.0",
        description: str = "",
        docs_url: str | None = None,
        support_url: str | None = None,
    ):
        self.service_name = service_name
        self.domain = domain
        self.version = version
        self.description = description
        self.docs_url = docs_url
        self.support_url = support_url

    def generate_html(
        self,
        routes: list[dict[str, str]],
        health_status: dict[str, Any],
        environment: str = "production",
        uptime: str | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> str:
        status = health_status.get("status", "unknown")
        routes_html = generate_routes_html(routes)
        health_html = generate_health_checks_html(health_status.get("checks", {}))
        metrics_html = generate_metrics_html(metrics or {}) if metrics else ""
        links_html = generate_links_html(self.docs_url, self.support_url)
        return build_status_page_html(
            service_name=self.service_name,
            version=self.version,
            description=self.description,
            domain=self.domain,
            routes_html=routes_html,
            health_html=health_html,
            metrics_html=metrics_html,
            links_html=links_html,
            status=status,
            environment=environment,
            uptime=uptime or None,
        )

    def generate_json(
        self,
        routes: list[dict[str, str]],
        health_status: dict[str, Any],
        environment: str = "production",
        uptime: str | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> dict:
        return {
            "service": {
                "name": self.service_name,
                "version": self.version,
                "description": self.description,
                "domain": self.domain,
                "environment": environment,
                "uptime": uptime,
            },
            "status": health_status.get("status", "unknown"),
            "health": health_status,
            "routes": routes,
            "metrics": metrics or {},
            "links": {"docs": self.docs_url, "support": self.support_url},
            "timestamp": datetime.now().isoformat(),
        }
