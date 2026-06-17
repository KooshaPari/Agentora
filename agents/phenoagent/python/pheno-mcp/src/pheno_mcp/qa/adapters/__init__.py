"""Adapter utilities for the MCP QA toolkit.

For the consolidated toolkit we currently expose a lightweight HTTP client that
wraps ``httpx`` but falls back to the standard library when the dependency is
unavailable.  The intent is to keep the public surface compatible with the
original ``mcp_qa.adapters`` package while the richer implementation is migrated
over in phases.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Self

try:  # pragma: no cover - optional dependency
    import httpx
except Exception:  # pragma: no cover - httpx not installed
    httpx = None  # type: ignore[assignment]


@dataclass
class FastHTTPResponse:
    """
    Simplified response wrapper returned by :class:`FastHTTPClient`.
    """

    status_code: int
    json_data: dict[str, Any] | None = None
    text: str = ""

    def json(self) -> dict[str, Any]:
        return self.json_data or {}


class FastHTTPClient:
    """Minimal asynchronous HTTP client used by the MCP QA tooling.

    The original implementation delegated to httpx with retry/backoff logic.
    To keep consolidation simple while remaining compatible we implement a
    small subset of that behaviour: ``get``/``post`` helpers plus the async
    context manager protocol.  When httpx is not available we fall back to the
    standard library using ``urllib.request`` executed in a thread pool.
    """

    def __init__(self, base_url: str | None = None, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.timeout = timeout
        self._client: Any = None

    async def __aenter__(self) -> Self:
        if httpx:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if httpx and self._client:
            await self._client.aclose()
        self._client = None

    async def get(self, path: str, **kwargs: Any) -> FastHTTPResponse:
        return await self.request("GET", path, **kwargs)

    async def post(
        self, path: str, json: dict[str, Any] | None = None, **kwargs: Any,
    ) -> FastHTTPResponse:
        return await self.request("POST", path, json=json, **kwargs)

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> FastHTTPResponse:
        url = f"{self.base_url}/{path.lstrip('/')}" if self.base_url else path

        if httpx:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(method, url, json=json, headers=headers)
                try:
                    payload = response.json()
                except ValueError:
                    payload = None
                return FastHTTPResponse(response.status_code, payload, response.text)

        # Fallback using standard library (synchronous executed via thread)
        import asyncio
        import json as std_json
        from functools import partial
        from urllib.request import Request, urlopen

        body = std_json.dumps(json).encode("utf-8") if json is not None else None
        req = Request(url, data=body, method=method.upper())
        for key, value in (headers or {}).items():
            req.add_header(key, value)
        if json is not None:
            req.add_header("Content-Type", "application/json")

        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, partial(urlopen, req, timeout=self.timeout))
        text = response.read().decode()
        try:
            payload = std_json.loads(text)
        except ValueError:
            payload = None
        return FastHTTPResponse(response.getcode(), payload, text)


__all__ = ["FastHTTPClient", "FastHTTPResponse"]
