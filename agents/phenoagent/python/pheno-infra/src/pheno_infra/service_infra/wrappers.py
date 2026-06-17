"""
Compatibility wrapper methods for legacy/canonical API names (refactored from
kinfra/wrappers.py).
"""

from __future__ import annotations

from typing import Any


class WrappersMixin:
    # --- Canonical wrappers ---
    def create_tunnel(
        self, service_name: str, port: int, domain: str | None = None, path: str = "/",
    ):
        return super().create_tunnel(service_name, port, domain=domain, path=path)  # type: ignore[misc]

    def ensure_port_and_tunnel(
        self,
        service_name: str,
        preferred_port: int | None = None,
        domain: str | None = None,
        path: str = "/",
    ) -> dict[str, Any]:
        # allocate_and_tunnel legacy name
        port = self.allocate_port(service_name, preferred_port)  # type: ignore[attr-defined]
        info = self.create_tunnel(service_name, port, domain=domain, path=path)
        return {
            "service_name": service_name,
            "port": port,
            "tunnel_info": info,
            "url": f"https://{info.hostname}",
            "hostname": info.hostname,
        }

    def get_public_url(self, service_name: str) -> str | None:
        return super().get_public_url(service_name)  # type: ignore[misc]

    def get_port(self, service_name: str) -> int | None:
        return super().get_port(service_name)  # type: ignore[misc]

    def get_info(self, service_name: str):
        return super().get_info(service_name)  # type: ignore[misc]
