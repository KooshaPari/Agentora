"""Thin admin client for ProxyServer tenant endpoints.

Uses only stdlib (http.client) to avoid external dependencies.
"""

from __future__ import annotations

import http.client
import json
from typing import Any


class ProxyAdminClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 9100, timeout: float = 5.0):
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

    def add_upstream(
        self,
        path_prefix: str,
        port: int,
        host: str = "localhost",
        service_name: str | None = None,
        tenant: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data: dict[str, Any] = {"path_prefix": path_prefix, "port": port, "host": host}
        if service_name:
            data["service_name"] = service_name
        if tenant:
            data["tenant"] = tenant
        if metadata:
            data["metadata"] = metadata
        return self._request("POST", "/__admin__/tenant/upstream", data)

    def remove_upstream(self, path_prefix: str) -> dict[str, Any]:
        return self._request("DELETE", "/__admin__/tenant/upstream", {"path_prefix": path_prefix})

    def list_upstreams(self, tenant: str | None = None) -> dict[str, Any]:
        path = "/__admin__/tenant/upstreams"
        if tenant:
            path = f"{path}?tenant={tenant}"
        return self._request("GET", path)

    def deregister_tenant(
        self, tenant: str | None = None, path_prefixes: list[str] | None = None,
    ) -> dict[str, Any]:
        if not tenant and not path_prefixes:
            raise ValueError("Provide tenant or path_prefixes")
        data: dict[str, Any] = {}
        if tenant:
            data["tenant"] = tenant
        if path_prefixes:
            data["path_prefixes"] = path_prefixes
        return self._request("POST", "/__admin__/tenant/deregister", data)
