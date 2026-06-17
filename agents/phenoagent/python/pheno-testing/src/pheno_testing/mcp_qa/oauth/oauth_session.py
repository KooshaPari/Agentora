"""
Session-scoped helpers for sharing authenticated OAuth clients in pytest.
"""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Dict, Optional

import httpx
from fastmcp import Client

from .oauth_automation import FlowResult, OAuthAutomator, create_default_automator
from .oauth_cache import CachedOAuthClient


class OAuthSessionBroker:
    """
    Coordinate OAuth automation, token caching, and reusable clients.
    """

    def __init__(
        self,
        mcp_url: str,
        *,
        provider: str = "authkit",
        client_name: str = "Atoms MCP Test Suite",
        automator: Optional[OAuthAutomator] = None,
        credential_overrides: Optional[Dict[str, str]] = None,
        mfa_code: Optional[str] = None,
    ) -> None:
        self.mcp_url = mcp_url
        self.provider = provider
        self.client_name = client_name
        self._automator = automator or create_default_automator(verbose=False)
        self._credential_overrides = dict(credential_overrides or {})
        self._mfa_code = mfa_code

        self._cached_client = CachedOAuthClient(
            mcp_url,
            client_name=client_name,
            playwright_oauth_handler=self._playwright_handler,
        )

        self._client: Optional[Client] = None
        self._client_lock = asyncio.Lock()
        self._flow_result: Optional[FlowResult] = None
        self._token_lock = asyncio.Lock()

    async def _playwright_handler(
        self, oauth_url: str
    ) -> bool:  # pragma: no cover - exercised in integration tests
        flow_result = await self._automator.authenticate(
            oauth_url,
            provider=self.provider,
            credential_overrides=self._credential_overrides or None,
            mfa_code=self._mfa_code,
        )
        self._flow_result = flow_result
        return flow_result.success

    async def ensure_client(self) -> Client:
        """
        Return a shared FastMCP client, creating it if necessary.
        """

        if self._client is not None:
            return self._client

        async with self._client_lock:
            if self._client is None:
                self._client = await self._cached_client.create_client()
            return self._client

    @asynccontextmanager
    async def fastmcp_client(self) -> AsyncIterator[Client]:
        """
        Async context manager that yields the shared FastMCP client.
        """

        client = await self.ensure_client()
        yield client

    def get_flow_result(self) -> Optional[FlowResult]:
        """
        Return the most recent :class:`FlowResult` from the automation.
        """

        return self._flow_result

    def token_cache_path(self) -> Path:
        """
        Return the filesystem path containing the cached OAuth token.
        """

        return self._cached_client._get_cache_path()  # noqa: SLF001 - internal helper is stable within tests

    async def get_token_payload(self) -> Dict[str, Any]:
        """
        Read the cached token JSON, ensuring it exists.
        """

        async with self._token_lock:
            cache_path = self.token_cache_path()
            if not cache_path.exists():
                await self.ensure_client()

            if not cache_path.exists():
                raise FileNotFoundError(
                    f"OAuth token cache not found at {cache_path}. Run the OAuth flow first."
                )

            with cache_path.open("r", encoding="utf-8") as handle:
                return json.load(handle)

    async def get_authorization_header(self) -> Dict[str, str]:
        """
        Return an Authorization header derived from the cached token.
        """

        payload = await self.get_token_payload()
        access_token = payload.get("access_token")
        token_type = payload.get("token_type", "Bearer")

        if not access_token:
            raise KeyError(
                "OAuth token payload missing 'access_token'. Delete cache to re-authenticate."
            )

        return {"Authorization": f"{token_type} {access_token}"}

    @asynccontextmanager
    async def http_client(
        self,
        *,
        base_url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 30.0,
    ) -> AsyncIterator[httpx.AsyncClient]:
        """
        Yield an ``httpx.AsyncClient`` pre-populated with OAuth headers.
        """

        auth_header = await self.get_authorization_header()
        merged_headers = {**auth_header, **(headers or {})}

        async with httpx.AsyncClient(
            base_url=base_url, headers=merged_headers, timeout=timeout
        ) as client:
            yield client

    async def close(self) -> None:
        """
        Close the shared client and release resources.
        """

        if self._client is not None:
            try:
                await self._client.__aexit__(None, None, None)
            except RuntimeError as e:
                # Ignore "not holding this lock" errors during cleanup
                # This can happen when async generators are closed while tasks are cancelled
                if "not holding this lock" not in str(e):
                    raise
            finally:
                self._client = None
