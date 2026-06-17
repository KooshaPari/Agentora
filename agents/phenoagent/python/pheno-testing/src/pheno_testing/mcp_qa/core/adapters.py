"""
MCP Client Adapters - Unified Client Communication Layer

Combines best features from both Zen and Atoms frameworks:
- Unified interface for MCP tool calls
- Comprehensive error handling and logging
- Request/response timing
- Verbose-on-fail mode (quiet success, detailed failures)
- Statistics tracking
"""

import json
import time
from typing import Any, Dict, Optional

from fastmcp import Client


class MCPClientAdapter:
    """Unified adapter for MCP client communication.

    Features:
    - Normalized result format
    - Timing and statistics
    - Buffered logging (only shows on failure)
    - JSON parsing and validation
    - Error detail capture
    """

    def __init__(
        self,
        client: Client,
        debug: bool = False,
        verbose_on_fail: bool = True,
    ):
        """Initialize MCP client adapter.

        Args:
            client: FastMCP Client instance
            debug: Enable verbose debug logging (always on)
            verbose_on_fail: Show detailed logs only on failures (default: True)
        """
        self.client = client
        self.debug = debug
        self.verbose_on_fail = verbose_on_fail
        self._call_count = 0
        self._total_duration_ms = 0.0
        self._last_call_log: list[str] = []  # Buffer for conditional logging

        # Extract endpoint from client
        self.endpoint = getattr(client, "_url", "unknown")

    def _log(self, msg: str):
        """
        Add message to log buffer (printed only on error).
        """
        self._last_call_log.append(msg)
        if self.debug:
            print(msg)

    def _print_logs_on_error(self):
        """
        Print buffered logs when error occurs.
        """
        if self.verbose_on_fail and self._last_call_log:
            print("\n" + "=" * 80)
            print("FAILED TEST - DETAILED OUTPUT:")
            print("=" * 80)
            for log_line in self._last_call_log:
                print(log_line)

            # Try to collect server logs if available
            try:
                from .server_logs import collect_server_logs

                server_logs = collect_server_logs(lines=20)
                if server_logs:
                    print("\n" + "-" * 80)
                    print("SERVER LOGS (Last 20 lines):")
                    print("-" * 80)
                    print(server_logs)
            except Exception:
                pass  # Server log collection optional

            print("=" * 80 + "\n")

    async def call_tool(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Call MCP tool and return normalized result.

        Args:
            tool_name: Name of the MCP tool
            arguments: Tool arguments/parameters

        Returns:
            {
                "success": bool,
                "result": Any,
                "duration_ms": float,
                "error": Optional[str],
                "request_params": Optional[Dict] (only on failure)
            }
        """
        arguments = arguments or {}
        self._call_count += 1
        self._last_call_log = []  # Reset log buffer
        start = time.perf_counter()

        try:
            self._log(
                f"[CLIENT-{self._call_count}] Calling {tool_name} with args={arguments!r}"[:200]
            )
            result = await self.client.call_tool(tool_name, arguments=arguments)
            self._log(f"[CLIENT-{self._call_count}] Result type: {type(result)}")

            duration_ms = (time.perf_counter() - start) * 1000
            self._total_duration_ms += duration_ms

            # Check if result is None
            if result is None:
                self._log(f"[CLIENT-{self._call_count}] Tool returned None")
                self._print_logs_on_error()
                return {
                    "success": False,
                    "result": None,
                    "duration_ms": duration_ms,
                    "error": "Tool returned None",
                }

            # Check for content
            if hasattr(result, "content") and result.content:
                text = result.content[0].text
                self._log(f"[CLIENT-{self._call_count}] Response length: {len(text)} chars")

                try:
                    parsed = json.loads(text)
                    tool_success = parsed.get("success", True)

                    if not tool_success:
                        # Failure - print full logs
                        self._log(f"[CLIENT-{self._call_count}] Tool returned success=false")
                        self._log(
                            f"[CLIENT-{self._call_count}] Response: {json.dumps(parsed, indent=2)}"
                        )
                        self._print_logs_on_error()
                    # Success - silent

                    return {
                        "success": tool_success,
                        "result": parsed,
                        "duration_ms": duration_ms,
                        "error": parsed.get("error") if not tool_success else None,
                        "request_params": arguments if not tool_success else None,
                    }

                except json.JSONDecodeError as e:
                    self._log(f"[CLIENT-{self._call_count}] JSON parse failed: {e}")
                    self._print_logs_on_error()
                    return {
                        "success": False,
                        "result": text,
                        "duration_ms": duration_ms,
                        "error": f"JSON parse error: {e}",
                    }

            # No content
            self._log(f"[CLIENT-{self._call_count}] Empty response")
            self._print_logs_on_error()
            return {
                "success": False,
                "result": None,
                "duration_ms": duration_ms,
                "error": "Empty response",
            }

        except Exception as e:
            duration_ms = (time.perf_counter() - start) * 1000
            self._total_duration_ms += duration_ms

            self._log(f"[CLIENT-{self._call_count}] Exception: {type(e).__name__}: {str(e)}")
            self._print_logs_on_error()

            return {
                "success": False,
                "result": None,
                "duration_ms": duration_ms,
                "error": str(e),
                "request_params": arguments,
            }

    async def list_tools(self) -> Dict[str, Any]:
        """List available MCP tools.

        Returns:
            {
                "success": bool,
                "tools": List[Tool],
                "duration_ms": float,
                "error": Optional[str]
            }
        """
        self._call_count += 1
        start = time.perf_counter()

        try:
            tools = await self.client.list_tools()
            duration_ms = (time.perf_counter() - start) * 1000
            self._total_duration_ms += duration_ms

            if self.debug:
                print(
                    f"[CLIENT-{self._call_count}] Listed {len(tools.tools) if hasattr(tools, 'tools') else 0} tools"
                )

            return {
                "success": True,
                "tools": tools.tools if hasattr(tools, "tools") else [],
                "duration_ms": duration_ms,
                "error": None,
            }

        except Exception as e:
            duration_ms = (time.perf_counter() - start) * 1000
            self._total_duration_ms += duration_ms

            if self.debug:
                print(f"[CLIENT-{self._call_count}] list_tools failed: {e}")

            return {
                "success": False,
                "tools": [],
                "duration_ms": duration_ms,
                "error": str(e),
            }

    async def ping(self) -> Dict[str, Any]:
        """Ping server for health check.

        Returns:
            {
                "success": bool,
                "latency_ms": float,
                "error": Optional[str]
            }
        """
        try:
            result = await self.list_tools()
            return {
                "success": result["success"],
                "latency_ms": result["duration_ms"],
                "error": result["error"],
            }
        except Exception as e:
            return {
                "success": False,
                "latency_ms": 0.0,
                "error": str(e),
            }

    def get_stats(self) -> Dict[str, Any]:
        """
        Get adapter statistics.
        """
        avg_duration = self._total_duration_ms / self._call_count if self._call_count > 0 else 0

        return {
            "total_calls": self._call_count,
            "total_duration_ms": self._total_duration_ms,
            "avg_duration_ms": avg_duration,
            "endpoint": self.endpoint,
        }

    def enable_debug(self):
        """
        Enable verbose debug logging.
        """
        self.debug = True
        print("[CLIENT] Debug logging enabled")

    def disable_debug(self):
        """
        Disable debug logging.
        """
        self.debug = False
