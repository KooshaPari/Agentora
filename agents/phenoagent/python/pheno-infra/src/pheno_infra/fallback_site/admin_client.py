"""Thin admin client for FallbackServer tenant endpoints.

Uses only stdlib (http.client) to avoid external dependencies.
"""

from __future__ import annotations

import http.client
import json
from typing import Any


class FallbackAdminClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 9000, timeout: float = 5.0):
        self.host = host
        self.port = port
        self.timeout = timeout

    def _request(
        self, method: str, path: str, data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        conn = http.client.HTTPConnection(self.host, self.port, timeout=self.timeout)
        try:
            headers = {"Content-Type": "application/json"}
            body = None
            if data is not None:
                body = json.dumps(data).encode("utf-8")
            conn.request(method, path, body=body, headers=headers)
            resp = conn.getresponse()
            content = resp.read().decode("utf-8")
            try:
                payload = json.loads(content) if content else {}
            except json.JSONDecodeError:
                payload = {"raw": content}
            if resp.status >= 400:
                raise RuntimeError(f"{method} {path} failed: {resp.status} {payload}")
            return payload
        finally:
            conn.close()

    def update_status(self, tenant: str, service_name: str, **fields: Any) -> dict[str, Any]:
        data: dict[str, Any] = {"tenant": tenant, "service_name": service_name}
        data.update(fields)
        return self._request("POST", "/__admin__/tenant/status", data)

    def delete_status(
        self, tenant: str | None = None, service_name: str | None = None,
    ) -> dict[str, Any]:
        if not tenant and not service_name:
            raise ValueError("Provide tenant or service_name")
        data: dict[str, Any] = {}
        if tenant:
            data["tenant"] = tenant
        if service_name:
            data["service_name"] = service_name
        return self._request("DELETE", "/__admin__/tenant/status", data)

    def list_status(self, tenant: str | None = None) -> dict[str, Any]:
        path = "/__admin__/tenant/status"
        if tenant:
            path = f"{path}?tenant={tenant}"
        return self._request("GET", path)
