"""
FastHTTPClient - Lightweight HTTP client for MCP calls using captured OAuth token.

Makes REAL calls to the actual server/Supabase (validates RLS + schema).
Uses HTTP POST with JSON-RPC 2.0 instead of MCP SSE for 20x speed improvement.

This is a drop-in replacement for AtomsMCPClientAdapter that:
- Uses direct HTTP calls (no SSE overhead)
- Supports captured OAuth tokens
- Validates real backend behavior (RLS, schema, auth)
- Provides identical interface for test compatibility
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict

import httpx

try:
    from utils.logging_setup import get_logger
except ImportError:
    from ..utils.logging_utils import get_logger

from ..utils.http_retry import HTTPRetryConfig, HTTPRetryError, retry_async

logger = get_logger("atoms.fast_http")


class FastHTTPClient:
    """Lightweight HTTP client for MCP calls using captured OAuth token.

    Makes REAL calls to the actual server/Supabase (validates RLS + schema). Just uses
    HTTP instead of MCP SSE for 20x speed improvement.

    Interface matches AtomsMCPClientAdapter for drop-in test replacement.
    """

    # Configuration constants
    HTTP_TIMEOUT = (
        60.0  # seconds - timeout for individual HTTP calls (increased for slow operations)
    )
    SLOW_CALL_THRESHOLD = 5.0  # seconds - log if call takes longer than this
    MAX_RETRIES = 5  # Maximum retry attempts for failed calls (including CloudFlare 530 errors)
    RETRY_DELAY = 1.0  # Base delay between retries (exponential backoff)

    # Retry configuration for CloudFlare 530 and other 5xx errors
    RETRY_CONFIG = HTTPRetryConfig(
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
        mcp_endpoint: str,
        access_token: str,
        debug: bool = False,
        reauthenticate_callback: callable = None,
    ):
        """Initialize FastHTTPClient.

        Args:
            mcp_endpoint: MCP endpoint URL (e.g., "https://api.example.com/mcp")
            access_token: OAuth access token for authentication
            debug: Enable debug logging
            reauthenticate_callback: Async function to call when token expires (returns new token)
        """
        self.mcp_endpoint = mcp_endpoint
        self.access_token = access_token
        self.debug = debug
        self._reauthenticate_callback = reauthenticate_callback

        # Don't create HTTP client in __init__ - create it lazily in async context
        self._http_client = None

        # JSON-RPC request counter (for unique request IDs)
        self._request_id = 0

        # Call tracking (for statistics and debugging)
        self._call_count = 0
        self._error_count = 0
        self._call_history = []
        self._last_error = None

        # Metadata for compatibility with AtomsMCPClientAdapter
        self.endpoint = mcp_endpoint
        self._url = mcp_endpoint

        logger.debug(f"FastHTTPClient initialized for endpoint: {mcp_endpoint}")

    def _ensure_http_client(self):
        """
        Ensure HTTP client is created (lazy initialization).
        """
        if self._http_client is None:
            # Create event hooks for debugging
            async def log_request(request):
                logger.debug(f"→ [NETWORK] Sending {request.method} {request.url}")
                logger.debug(f"   Headers: {dict(request.headers)}")
                if request.content:
                    logger.debug(f"   Body: {request.content[:500]}")

            async def log_response(response):
                logger.debug(f"← [NETWORK] Received {response.status_code} from {response.url}")
                logger.debug(f"   Headers: {dict(response.headers)}")

            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.HTTP_TIMEOUT, connect=10.0, read=self.HTTP_TIMEOUT),
                limits=httpx.Limits(
                    max_keepalive_connections=5, max_connections=10
                ),  # Connection pooling
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",  # MCP requires both
                },
                event_hooks=(
                    {"request": [log_request], "response": [log_response]} if self.debug else {}
                ),
            )
            logger.debug(f"HTTP client created in event loop: {id(asyncio.get_event_loop())}")

    async def call_tool(self, name: str, params: Dict[str, Any]) -> Any:
        """Call a tool using HTTP POST with JSON-RPC 2.0.

        Args:
            name: Tool name
            params: Tool parameters (will be passed as "arguments" in JSON-RPC)

        Returns:
            Processed result matching AtomsMCPClientAdapter format:
            {
                "success": bool,
                "error": str | None,
                "response": dict,
                "request_params": dict | None
            }

        Raises:
            asyncio.TimeoutError: If call exceeds HTTP_TIMEOUT
            Exception: If tool call fails
        """
        # Ensure HTTP client exists in current event loop
        self._ensure_http_client()

        self._call_count += 1
        self._request_id += 1
        call_start = datetime.now()

        # Compact params for logging
        params_preview = self._format_params_for_log(params)

        if self.debug:
            logger.info(f"→ Calling {name} via HTTP with params: {params_preview}")

        # Define the HTTP call operation to be retried
        async def make_http_call():
            # Build JSON-RPC 2.0 request
            payload = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": name, "arguments": params},
                "id": self._request_id,
            }

            if self.debug:
                logger.debug(f"→ [HTTP REQUEST] POST {self.mcp_endpoint}")
                logger.debug(f"   Payload: {json.dumps(payload)}")

            # Make HTTP POST request with streaming support for SSE
            logger.debug(f"→ [CALL] About to make HTTP POST to {self.mcp_endpoint}")

            async with self._http_client.stream(
                "POST", self.mcp_endpoint, json=payload
            ) as response:
                logger.debug(f"← [CALL] HTTP POST completed with status {response.status_code}")

                # Check HTTP status (this will raise HTTPStatusError for 4xx/5xx)
                response.raise_for_status()

                # Check if response is SSE (text/event-stream)
                content_type = response.headers.get("content-type", "")

                if "text/event-stream" in content_type:
                    logger.debug("← [SSE] Response is Server-Sent Events, consuming stream...")

                    # Consume SSE stream until we find our JSON-RPC response
                    rpc_response = None
                    async for line in response.aiter_lines():
                        if not line:
                            continue  # Skip empty lines

                        if line.startswith("data: "):
                            data_str = line[6:]  # Remove "data: " prefix
                            if data_str.strip() and data_str != "[DONE]":
                                try:
                                    msg = json.loads(data_str)
                                    # Look for JSON-RPC response with matching ID
                                    if "jsonrpc" in msg and msg.get("id") == self._request_id:
                                        rpc_response = msg
                                        logger.debug(
                                            f"← [SSE] Found JSON-RPC response with id={self._request_id}"
                                        )
                                        break  # STOP reading immediately after getting our response
                                    # Also check for result without id field (some servers omit it)
                                    elif "result" in msg and not rpc_response:
                                        rpc_response = msg
                                        logger.debug("← [SSE] Found result message (no id check)")
                                        break
                                except json.JSONDecodeError:
                                    logger.debug(
                                        f"← [SSE] Skipping non-JSON line: {data_str[:100]}"
                                    )
                                    continue

                    if not rpc_response:
                        raise Exception("No JSON-RPC response found in SSE stream")

                else:
                    # Regular JSON response
                    logger.debug("← [JSON] Response is regular JSON")
                    response_text = await response.aread()
                    rpc_response = json.loads(response_text)

            # Check for JSON-RPC error
            if "error" in rpc_response:
                error_data = rpc_response["error"]
                error_msg = error_data if isinstance(error_data, str) else json.dumps(error_data)
                raise Exception(f"JSON-RPC Error: {error_msg}")

            # Extract result
            result_data = rpc_response.get("result", {})

            # Process result to match AtomsMCPClientAdapter format
            return self._process_result(result_data, name, params)

        # Execute with retry logic using our retry utility
        try:
            # Handle 401 errors separately (token refresh) before retrying
            processed_result = await retry_async(
                make_http_call, config=self.RETRY_CONFIG, operation_name=f"call_tool({name})"
            )

            # Log success with timing
            duration = (datetime.now() - call_start).total_seconds()
            success = processed_result.get("success", True)

            if duration >= self.SLOW_CALL_THRESHOLD or self.debug:
                status_emoji = "✓" if success else "✗"
                logger.info(
                    f"{status_emoji} Call to {name} completed in {duration:.2f}s "
                    f"(success={success})"
                )

            # Track successful call
            self._call_history.append(
                {
                    "tool": name,
                    "params": params,
                    "success": True,
                    "duration": duration,
                    "timestamp": call_start.isoformat(),
                }
            )

            return processed_result

        except HTTPRetryError as e:
            # Check if the underlying error was 401 (token expired)
            if (
                isinstance(e.last_error, httpx.HTTPStatusError)
                and e.last_error.response.status_code == 401
            ):
                logger.warning("⚠️  401 Unauthorized - token may have expired")

                # Try to re-authenticate if callback provided
                if self._reauthenticate_callback:
                    logger.info("🔄 Attempting re-authentication")
                    try:
                        new_token = await self._reauthenticate_callback()
                        if new_token:
                            self.access_token = new_token
                            # Recreate HTTP client with new token
                            await self.close()
                            self._http_client = None
                            self._ensure_http_client()
                            logger.info("✓ Re-authentication successful, retrying once more...")
                            # Retry one more time with new token
                            return await self.call_tool(name, params)
                    except Exception as reauth_error:
                        logger.error(f"Re-authentication failed: {reauth_error}")

            # All retries exhausted
            self._error_count += 1
            self._last_error = e.last_error

            duration = (datetime.now() - call_start).total_seconds()

            # Track failed call
            self._call_history.append(
                {
                    "tool": name,
                    "params": params,
                    "success": False,
                    "error": str(e.last_error),
                    "duration": duration,
                    "timestamp": call_start.isoformat(),
                }
            )

            # Log error
            error_type = type(e.last_error).__name__
            logger.error(
                f"❌ [ERROR] {name} failed after {duration:.2f}s\n"
                f"   Error type: {error_type}\n"
                f"   Error: {str(e.last_error)[:200]}\n"
                f"   Params: {params_preview}"
            )

            raise e.last_error

    async def list_tools(self) -> list:
        """List available tools using JSON-RPC 2.0.

        Returns:
            List of tool metadata objects

        Raises:
            asyncio.TimeoutError: If call exceeds HTTP_TIMEOUT
            Exception: If request fails
        """
        self._request_id += 1

        if self.debug:
            logger.info("→ Listing tools via HTTP")

        try:
            # Build JSON-RPC 2.0 request
            payload = {
                "jsonrpc": "2.0",
                "method": "tools/list",
                "params": {},
                "id": self._request_id,
            }

            # Make HTTP POST request
            # Note: Don't wrap in wait_for - httpx client already has timeout configured
            logger.debug(f"→ [CALL] About to make HTTP POST to {self.mcp_endpoint}")
            response = await self._http_client.post(self.mcp_endpoint, json=payload)
            logger.debug(f"← [CALL] HTTP POST completed with status {response.status_code}")

            # Check HTTP status
            response.raise_for_status()

            # Parse JSON-RPC response
            rpc_response = response.json()

            # Check for JSON-RPC error
            if "error" in rpc_response:
                error_data = rpc_response["error"]
                error_msg = error_data if isinstance(error_data, str) else json.dumps(error_data)
                raise Exception(f"JSON-RPC Error: {error_msg}")

            # Extract result
            result = rpc_response.get("result", {})
            tools = result.get("tools", [])

            if self.debug:
                logger.info(f"← Listed {len(tools)} tools")

            return tools

        except Exception as e:
            logger.error(f"❌ Failed to list tools: {e}")
            raise

    async def get_tool(self, tool_name: str):
        """Get tool metadata by name.

        Args:
            tool_name: Name of the tool to retrieve

        Returns:
            Tool metadata object or None if not found
        """
        tools = await self.list_tools()
        for tool in tools:
            # Handle both dict and object formats
            name = tool.get("name") if isinstance(tool, dict) else getattr(tool, "name", None)
            if name == tool_name:
                return tool
        return None

    def _process_result(
        self, result_data: Any, tool_name: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process result to match AtomsMCPClientAdapter format.

        Args:
            result_data: Raw result data from JSON-RPC response
            tool_name: Name of the tool that was called
            params: Parameters that were sent

        Returns:
            Processed result dictionary with success/error/response fields
        """
        if result_data is None:
            return {
                "success": False,
                "error": "Tool returned None",
                "response": None,
            }

        # Check if result_data has MCP content structure (from SSE response)
        if isinstance(result_data, dict) and "structuredContent" in result_data:
            # Extract the actual data from MCP's structuredContent
            structured = result_data.get("structuredContent", {})
            if isinstance(structured, dict):
                return structured  # Return the structured data directly

        # If result_data is already in the expected format, return it
        if isinstance(result_data, dict) and "success" in result_data:
            return result_data

        # Otherwise, wrap it in the expected format
        try:
            # Check if it's a string that needs JSON parsing
            if isinstance(result_data, str):
                parsed = json.loads(result_data)
                tool_success = parsed.get("success", True)
                return {
                    "success": tool_success,
                    "error": parsed.get("error") if not tool_success else None,
                    "response": parsed,
                    "request_params": params if not tool_success else None,
                }

            # Otherwise assume it's already structured data
            tool_success = (
                result_data.get("success", True) if isinstance(result_data, dict) else True
            )
            return {
                "success": tool_success,
                "error": (
                    result_data.get("error")
                    if isinstance(result_data, dict) and not tool_success
                    else None
                ),
                "response": result_data,
                "request_params": params if not tool_success else None,
            }

        except (json.JSONDecodeError, AttributeError):
            # If parsing fails, treat as successful text response
            return {
                "success": True,
                "error": None,
                "response": {"text": str(result_data)},
            }

    def _format_params_for_log(self, params: Dict[str, Any]) -> str:
        """Format parameters for logging (compact, safe).

        Args:
            params: Tool parameters

        Returns:
            Formatted string representation
        """
        try:
            # Create a copy to avoid modifying original
            safe_params = params.copy()

            # Truncate long values
            for key, value in safe_params.items():
                if isinstance(value, str) and len(value) > 100:
                    safe_params[key] = value[:100] + "..."
                elif isinstance(value, dict):
                    # Recursively truncate nested dicts
                    safe_params[key] = {
                        k: (v[:50] + "..." if isinstance(v, str) and len(v) > 50 else v)
                        for k, v in list(value.items())[:5]
                    }
                    if len(value) > 5:
                        safe_params[key]["..."] = f"({len(value) - 5} more fields)"

            return json.dumps(safe_params, default=str)
        except Exception:
            return str(params)[:200]

    # ============================================================================
    # Atoms-specific helper methods (for compatibility with AtomsMCPClientAdapter)
    # ============================================================================

    async def workspace_operation(self, operation: str, params: Dict[str, Any]) -> Any:
        """Atoms-specific workspace operation helper.

        Args:
            operation: Operation name (create, update, delete, etc.)
            params: Operation parameters

        Returns:
            Processed result
        """
        return await self.call_tool("workspace_operation", {"operation": operation, **params})

    async def entity_operation(self, entity_type: str, operation: str, data: Dict[str, Any]) -> Any:
        """Atoms-specific entity operation helper.

        Args:
            entity_type: Entity type name
            operation: Operation name (create, read, update, delete)
            data: Entity data

        Returns:
            Processed result
        """
        return await self.call_tool(
            "entity_operation", {"entity_type": entity_type, "operation": operation, "data": data}
        )

    # ============================================================================
    # Statistics and debugging
    # ============================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics.

        Returns:
            Dictionary with call counts, error counts, history, etc.
        """
        return {
            "call_count": self._call_count,
            "error_count": self._error_count,
            "success_rate": (
                (self._call_count - self._error_count) / self._call_count
                if self._call_count > 0
                else 0
            ),
            "last_error": str(self._last_error) if self._last_error else None,
            "call_history": self._call_history,
        }

    async def close(self):
        """
        Close HTTP client and release resources.
        """
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def __aenter__(self):
        """
        Async context manager entry.
        """
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Async context manager exit.
        """
        await self.close()


__all__ = ["FastHTTPClient"]
