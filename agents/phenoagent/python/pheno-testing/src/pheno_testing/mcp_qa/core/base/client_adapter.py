"""Base Client Adapter for MCP Testing.

Abstract base class that provides common functionality for MCP client adapters.
Projects extend this to implement project-specific tool call patterns and error handling.

Example:
    class MyProjectAdapter(BaseClientAdapter):
        def _process_result(self, result, tool_name, params):
            # Project-specific result processing
            return result.content if hasattr(result, 'content') else result

        def _log_error(self, error, tool_name, params):
            # Project-specific error logging
            logger.error(f"{tool_name} failed: {error}")
"""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional


class BaseClientAdapter(ABC):
    """Abstract base class for MCP client adapters.

    Provides common functionality:
    - Tool call orchestration with error handling
    - Call statistics tracking
    - Result processing hook
    - Error logging hook

    Projects extend this and implement:
    - _process_result(): Project-specific result transformation
    - _log_error(): Project-specific error logging
    """

    def __init__(self, client: Any, verbose_on_fail: bool = False):
        """Initialize adapter.

        Args:
            client: FastMCP Client instance
            verbose_on_fail: Show detailed error output on failures
        """
        self.client = client
        self.verbose_on_fail = verbose_on_fail
        self._call_count = 0
        self._error_count = 0
        self._call_history: List[Dict[str, Any]] = []
        self._last_error: Optional[Exception] = None

    async def call_tool(self, name: str, params: Dict[str, Any]) -> Any:
        """Call a tool with error handling and statistics tracking.

        Args:
            name: Tool name
            params: Tool parameters

        Returns:
            Processed result from tool call

        Raises:
            Exception: If tool call fails
        """
        self._call_count += 1
        call_start = datetime.now()

        try:
            result = await self.client.call_tool(name, params)
            processed_result = self._process_result(result, name, params)

            # Track successful call
            self._call_history.append(
                {
                    "tool": name,
                    "params": params,
                    "success": True,
                    "duration": (datetime.now() - call_start).total_seconds(),
                    "timestamp": call_start.isoformat(),
                }
            )

            return processed_result

        except Exception as e:
            self._error_count += 1
            self._last_error = e

            # Track failed call
            self._call_history.append(
                {
                    "tool": name,
                    "params": params,
                    "success": False,
                    "error": str(e),
                    "duration": (datetime.now() - call_start).total_seconds(),
                    "timestamp": call_start.isoformat(),
                }
            )

            if self.verbose_on_fail:
                self._log_error(e, name, params)

            raise

    @abstractmethod
    def _process_result(self, result: Any, tool_name: str, params: Dict[str, Any]) -> Any:
        """Process tool result (project-specific logic).

        This method should transform the raw FastMCP result into the format
        expected by your project's tests.

        Args:
            result: Raw result from FastMCP client
            tool_name: Name of tool that was called
            params: Parameters passed to tool

        Returns:
            Processed result in project-specific format
        """
        pass

    @abstractmethod
    def _log_error(self, error: Exception, tool_name: str, params: Dict[str, Any]) -> None:
        """Log error with project-specific format.

        Args:
            error: Exception that was raised
            tool_name: Name of tool that failed
            params: Parameters that were passed to tool
        """
        pass

    def get_stats(self) -> Dict[str, Any]:
        """Get adapter statistics.

        Returns:
            Dict with call statistics:
            - total_calls: Total number of tool calls
            - errors: Number of failed calls
            - success_rate: Percentage of successful calls
            - last_error: Most recent error (if any)
        """
        success_rate = (
            (self._call_count - self._error_count) / self._call_count * 100
            if self._call_count > 0
            else 0
        )

        return {
            "total_calls": self._call_count,
            "errors": self._error_count,
            "success_rate": f"{success_rate:.2f}%",
            "last_error": str(self._last_error) if self._last_error else None,
        }

    def get_call_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get recent call history.

        Args:
            limit: Maximum number of calls to return (most recent first)

        Returns:
            List of call records
        """
        history = self._call_history[::-1]  # Reverse for most recent first
        if limit:
            history = history[:limit]
        return history

    def clear_stats(self) -> None:
        """
        Clear all statistics and call history.
        """
        self._call_count = 0
        self._error_count = 0
        self._call_history = []
        self._last_error = None


class SimpleClientAdapter(BaseClientAdapter):
    """Simple implementation of BaseClientAdapter for basic use cases.

    Returns results as-is and logs errors to stdout. Use this as a template or for
    testing.
    """

    def _process_result(self, result: Any, tool_name: str, params: Dict[str, Any]) -> Any:
        """
        Return result as-is.
        """
        # Handle FastMCP result format
        if hasattr(result, "content"):
            return result.content
        return result

    def _log_error(self, error: Exception, tool_name: str, params: Dict[str, Any]) -> None:
        """
        Log error to stdout.
        """
        print(f"❌ Tool call failed: {tool_name}")
        print(f"   Params: {json.dumps(params, indent=2, default=str)}")
        print(f"   Error: {error}")


__all__ = ["BaseClientAdapter", "SimpleClientAdapter"]
