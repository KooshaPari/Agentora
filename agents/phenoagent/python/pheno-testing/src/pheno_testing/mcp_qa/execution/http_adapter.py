"""HTTP adapter for direct API calls bypassing MCP protocol.

This adapter allows tests to make direct HTTP calls to MCP tool endpoints, which is ~20x
faster than going through the MCP protocol for simple operations.

Includes automatic retry logic for CloudFlare 530 errors and other 5xx errors.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from ..oauth.oauth_session import OAuthSessionBroker
from ..utils.http_retry import HTTPRetryConfig, HTTPRetryError, retry_async


class HTTPToolAdapter:
    """
    Adapter for calling MCP tools via direct HTTP requests with retry logic.
    """

    # Default retry configuration for CloudFlare 530 and other 5xx errors
    DEFAULT_RETRY_CONFIG = HTTPRetryConfig(
        max_retries=5,
        backoff_factor=2.0,
        initial_backoff=1.0,
        max_backoff=60.0,
        retryable_status_codes={500, 502, 503, 504, 530},  # Include CloudFlare 530
        retry_on_timeout=True,
        retry_on_connection_error=True,
    )

    def __init__(
        self,
        broker: OAuthSessionBroker,
        api_base_url: str,
        retry_config: Optional[HTTPRetryConfig] = None,
    ):
        """Initialize HTTP tool adapter.

        Args:
            broker: OAuth session broker with auth credentials
            api_base_url: Base URL for API (e.g., "https://zen.kooshapari.com/api")
            retry_config: Custom retry configuration (uses defaults if None)
        """
        self.broker = broker
        self.api_base_url = api_base_url.rstrip("/")
        self.retry_config = retry_config or self.DEFAULT_RETRY_CONFIG

    async def call_tool_http(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        *,
        timeout: float = 30.0,
        retry: bool = True,
    ) -> Dict[str, Any]:
        """Call tool via direct HTTP POST with automatic retry.

        Args:
            tool_name: Name of tool to call
            arguments: Tool arguments
            timeout: Request timeout in seconds
            retry: Whether to enable retry logic (default: True)

        Returns:
            Response dict with 'success' and 'result' or 'error'
        """

        async def make_request():
            async with self.broker.http_client(timeout=timeout) as client:
                response = await client.post(
                    f"{self.api_base_url}/tools/{tool_name}", json=arguments
                )
                response.raise_for_status()
                return response

        try:
            if retry:
                # Use retry logic
                response = await retry_async(
                    make_request,
                    config=self.retry_config,
                    operation_name=f"call_tool_http({tool_name})",
                )
            else:
                # Direct call without retry
                response = await make_request()

            return {"success": True, "result": response.json(), "status_code": response.status_code}

        except HTTPRetryError as e:
            # Retry exhausted, return error info
            if isinstance(e.last_error, httpx.HTTPStatusError):
                return {
                    "success": False,
                    "error": f"HTTP {e.last_error.response.status_code}: {e.last_error.response.text}",
                    "status_code": e.last_error.response.status_code,
                    "attempts": e.attempts,
                }
            return {"success": False, "error": str(e.last_error), "attempts": e.attempts}

        except httpx.HTTPStatusError as e:
            # Direct error without retry
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}: {e.response.text}",
                "status_code": e.response.status_code,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def call_tool_http_raw(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        *,
        timeout: float = 30.0,
        retry: bool = True,
    ) -> httpx.Response:
        """Call tool via HTTP and return raw response with retry.

        Args:
            tool_name: Name of tool to call
            arguments: Tool arguments
            timeout: Request timeout in seconds
            retry: Whether to enable retry logic (default: True)

        Returns:
            Raw httpx Response object

        Raises:
            HTTPRetryError: If all retry attempts are exhausted
        """

        async def make_request():
            async with self.broker.http_client(timeout=timeout) as client:
                response = await client.post(
                    f"{self.api_base_url}/tools/{tool_name}", json=arguments
                )
                response.raise_for_status()
                return response

        if retry:
            return await retry_async(
                make_request,
                config=self.retry_config,
                operation_name=f"call_tool_http_raw({tool_name})",
            )
        else:
            return await make_request()


class HybridToolAdapter:
    """Adapter that supports both MCP and HTTP calls.

    Use HTTP for fast operations, fall back to MCP for complex ones.
    """

    def __init__(
        self,
        mcp_adapter: Any,
        http_adapter: Optional[HTTPToolAdapter] = None,  # MCPClientAdapter
    ):
        """Initialize hybrid adapter.

        Args:
            mcp_adapter: Traditional MCP client adapter
            http_adapter: Optional HTTP adapter for direct calls
        """
        self.mcp_adapter = mcp_adapter
        self.http_adapter = http_adapter
        self._http_enabled_tools = {
            "chat",
            "listmodels",
            "analyze",
            "codereview",
            "planner",
            "consensus",
            "thinkdeep",
        }

    def __getattr__(self, name: str) -> Any:
        """
        Delegate attribute access to MCP adapter.
        """
        return getattr(self.mcp_adapter, name)

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Set attributes on self or delegate to MCP adapter.
        """
        if name in ("mcp_adapter", "http_adapter", "_http_enabled_tools"):
            # Set on self
            object.__setattr__(self, name, value)
        elif hasattr(self, "mcp_adapter"):
            # Delegate to MCP adapter
            setattr(self.mcp_adapter, name, value)
        else:
            # During __init__, before mcp_adapter is set
            object.__setattr__(self, name, value)

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        *,
        force_mcp: bool = False,
        force_http: bool = False,
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """Call tool using best method.

        Args:
            tool_name: Tool to call
            arguments: Tool arguments
            force_mcp: Force MCP protocol even if HTTP available
            force_http: Force HTTP even if tool not in whitelist
            timeout: Request timeout

        Returns:
            Result dict
        """
        # Use HTTP if available and tool supports it
        use_http = (
            self.http_adapter is not None
            and not force_mcp
            and (tool_name in self._http_enabled_tools or force_http)
        )

        if use_http:
            return await self.http_adapter.call_tool_http(tool_name, arguments, timeout=timeout)
        else:
            return await self.mcp_adapter.call_tool(tool_name, arguments)

    def enable_http_for_tool(self, tool_name: str):
        """
        Enable HTTP calls for specific tool.
        """
        self._http_enabled_tools.add(tool_name)

    def disable_http_for_tool(self, tool_name: str):
        """
        Disable HTTP calls for specific tool.
        """
        self._http_enabled_tools.discard(tool_name)
