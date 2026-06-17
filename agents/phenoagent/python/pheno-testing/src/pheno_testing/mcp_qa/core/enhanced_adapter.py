"""Enhanced MCP Client Adapter with Rich Logging.

Provides beautiful, intuitive logging for MCP tool calls and responses using the
enhanced MCP formatter from pheno-sdk.
"""

import json
import logging
import time
from typing import Any, Dict, Optional

from fastmcp import Client

from ..logging import ToolCallContext, create_mcp_logger


class EnhancedMCPAdapter:
    """Enhanced adapter for FastMCP Client with rich logging.

    Features:
    - Beautiful color-coded output
    - Emoji indicators for quick scanning
    - Structured logging with context
    - Performance metrics
    - Error highlighting
    - Configurable verbosity

    Example:
        adapter = EnhancedMCPAdapter(client, verbose_on_fail=True)
        result = await adapter.call_tool("entity_tool", {
            "operation": "create",
            "entity_type": "project"
        })
    """

    def __init__(
        self,
        client: Client,
        *,
        logger_name: str = "atoms.mcp",
        verbose_on_fail: bool = True,
        use_color: bool = True,
        use_emoji: bool = True,
        log_level: str = "INFO",
    ):
        """Initialize enhanced adapter.

        Args:
            client: FastMCP Client instance
            logger_name: Name for the logger
            verbose_on_fail: Show detailed logs only on failures
            use_color: Enable colored output
            use_emoji: Enable emoji indicators
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.client = client
        self._url = getattr(client, "_url", "unknown")
        self.verbose_on_fail = verbose_on_fail
        self._call_count = 0

        # Create MCP-aware logger
        self.logger = create_mcp_logger(
            logger_name,
            level=log_level,
            use_color=use_color,
            use_emoji=use_emoji,
        )

        # For verbose_on_fail mode, we buffer logs
        self._log_buffer = []
        self._buffering = verbose_on_fail

    async def call_tool(
        self,
        tool_name: str,
        params: Dict[str, Any],
        *,
        call_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Call an MCP tool with rich logging.

        Args:
            tool_name: Name of the tool to call
            params: Tool parameters
            call_id: Optional call identifier for tracking

        Returns:
            Dict with structure:
            {
                "success": bool,
                "error": str | None,
                "duration_ms": float,
                "response": Any (parsed response if success),
                "call_id": str
            }
        """
        self._call_count += 1
        call_id = call_id or f"call-{self._call_count}"
        start = time.perf_counter()

        # Clear buffer for new call
        if self._buffering:
            self._log_buffer = []

        # Log the tool call
        self._log_tool_call(tool_name, params, call_id)

        try:
            result = await self.client.call_tool(tool_name, arguments=params)
            duration_ms = (time.perf_counter() - start) * 1000

            if result is None:
                return self._handle_error(
                    tool_name, params, call_id, duration_ms, "Tool returned None"
                )

            if result.content:
                text = result.content[0].text

                try:
                    parsed = json.loads(text)
                    tool_success = parsed.get("success", True)

                    if tool_success:
                        return self._handle_success(tool_name, params, call_id, duration_ms, parsed)
                    else:
                        return self._handle_error(
                            tool_name,
                            params,
                            call_id,
                            duration_ms,
                            parsed.get("error", "Unknown error"),
                            response=parsed,
                        )

                except json.JSONDecodeError:
                    # Non-JSON response (might be valid for some tools)
                    return self._handle_success(
                        tool_name, params, call_id, duration_ms, {"text": text}
                    )

            # Empty response
            return self._handle_error(tool_name, params, call_id, duration_ms, "Empty response")

        except Exception as e:
            duration_ms = (time.perf_counter() - start) * 1000
            return self._handle_error(tool_name, params, call_id, duration_ms, str(e))

    def _log_tool_call(self, tool_name: str, params: Dict[str, Any], call_id: str):
        """
        Log a tool call.
        """
        ctx = ToolCallContext(
            tool_name=tool_name,
            params=params,
            call_id=call_id,
        )

        msg = f"Calling {tool_name}"

        if self._buffering:
            self._log_buffer.append((logging.INFO, msg, ctx))
        else:
            self.logger.info(msg, extra={"tool_context": ctx})

    def _handle_success(
        self,
        tool_name: str,
        params: Dict[str, Any],
        call_id: str,
        duration_ms: float,
        response: Any,
    ) -> Dict[str, Any]:
        """
        Handle successful tool call.
        """
        ctx = ToolCallContext(
            tool_name=tool_name,
            params=params,
            call_id=call_id,
            duration_ms=duration_ms,
            success=True,
            response=response,
        )

        msg = "Tool call succeeded"

        if self._buffering:
            # Success - don't print buffered logs
            self._log_buffer = []
        else:
            self.logger.info(msg, extra={"tool_context": ctx})

        return {
            "success": True,
            "error": None,
            "duration_ms": duration_ms,
            "response": response,
            "call_id": call_id,
        }

    def _handle_error(
        self,
        tool_name: str,
        params: Dict[str, Any],
        call_id: str,
        duration_ms: float,
        error: str,
        response: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Handle failed tool call.
        """
        ctx = ToolCallContext(
            tool_name=tool_name,
            params=params,
            call_id=call_id,
            duration_ms=duration_ms,
            success=False,
            error=error,
            response=response,
        )

        msg = f"Tool call failed: {error}"

        if self._buffering:
            # Failure - flush buffered logs
            self._flush_buffer()

        # Always log the error
        self.logger.error(msg, extra={"tool_context": ctx})

        return {
            "success": False,
            "error": error,
            "duration_ms": duration_ms,
            "response": response,
            "call_id": call_id,
            "request_params": params,
        }

    def _flush_buffer(self):
        """
        Flush buffered logs.
        """
        for level, msg, ctx in self._log_buffer:
            self.logger.log(level, msg, extra={"tool_context": ctx})
        self._log_buffer = []

    async def list_tools(self):
        """
        List available tools.
        """
        return await self.client.list_tools()

    async def get_tool(self, tool_name: str):
        """
        Get tool metadata.
        """
        tools = await self.list_tools()
        for tool in tools:
            if tool.name == tool_name:
                return tool
        return None

    @property
    def endpoint(self) -> str:
        """
        Get the MCP endpoint URL.
        """
        return self._url

    def enable_verbose(self):
        """
        Enable verbose logging (show all calls).
        """
        self._buffering = False
        self.logger.setLevel(logging.DEBUG)

    def disable_verbose(self):
        """
        Disable verbose logging (show only failures).
        """
        self._buffering = True
        self.logger.setLevel(logging.INFO)

    def get_stats(self) -> Dict[str, int]:
        """
        Get adapter statistics.
        """
        return {
            "total_calls": self._call_count,
        }


# Convenience function for creating adapters
def create_enhanced_adapter(
    client: Client,
    *,
    verbose_on_fail: bool = True,
    use_color: bool = True,
    use_emoji: bool = True,
) -> EnhancedMCPAdapter:
    """Create an enhanced MCP adapter with rich logging.

    Args:
        client: FastMCP Client instance
        verbose_on_fail: Show detailed logs only on failures
        use_color: Enable colored output
        use_emoji: Enable emoji indicators

    Returns:
        EnhancedMCPAdapter instance

    Example:
        from fastmcp import Client
        from pheno.testing.mcp_qa.core import create_enhanced_adapter

        client = Client(...)
        adapter = create_enhanced_adapter(client)
        result = await adapter.call_tool("entity_tool", {...})
    """
    return EnhancedMCPAdapter(
        client,
        verbose_on_fail=verbose_on_fail,
        use_color=use_color,
        use_emoji=use_emoji,
    )
