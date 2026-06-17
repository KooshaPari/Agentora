"""Enhanced MCP-specific logging formatter with rich formatting for tool calls and
responses.

Provides beautiful, intuitive formatting for:
- Tool call requests
- Tool responses (success/failure)
- Error details
- Performance metrics
- JSON payloads
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional


# Color codes for rich terminal output
class Colors:
    """
    ANSI color codes for terminal output.
    """

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Status colors
    SUCCESS = "\033[32m"  # Green
    ERROR = "\033[31m"  # Red
    WARNING = "\033[33m"  # Yellow
    INFO = "\033[36m"  # Cyan
    DEBUG = "\033[90m"  # Gray

    # Component colors
    TOOL = "\033[35m"  # Magenta
    PARAM = "\033[34m"  # Blue
    VALUE = "\033[36m"  # Cyan
    KEY = "\033[33m"  # Yellow

    # Special
    EMOJI = "\033[0m"  # No color for emojis
    TIMESTAMP = "\033[90m"  # Gray


# Emoji indicators
class Emoji:
    """
    Emoji indicators for different log types.
    """

    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    DEBUG = "🔍"
    TOOL_CALL = "🔧"
    RESPONSE = "📦"
    TIMING = "⏱️"
    NETWORK = "🌐"
    DATABASE = "💾"
    AUTH = "🔐"


@dataclass
class ToolCallContext:
    """
    Context information for a tool call.
    """

    tool_name: str
    params: Dict[str, Any]
    call_id: Optional[str] = None
    duration_ms: Optional[float] = None
    success: Optional[bool] = None
    error: Optional[str] = None
    response: Optional[Any] = None


class MCPFormatter(logging.Formatter):
    """Enhanced formatter for MCP tool calls and responses.

    Features:
    - Rich color-coded output
    - Emoji indicators for quick scanning
    - Structured JSON formatting
    - Performance metrics
    - Error highlighting
    - Compact mode for CI/production

    Example output:
        🔧 TOOL CALL | entity_tool | operation=create entity_type=project
        ✅ SUCCESS   | 1.2s | Created project-123
        📦 RESPONSE  | {"id": "project-123", "name": "My Project"}
    """

    def __init__(
        self,
        *,
        use_color: bool = True,
        use_emoji: bool = True,
        show_timestamp: bool = True,
        compact: bool = False,
        max_json_length: int = 500,
        indent_json: bool = True,
    ):
        """Initialize MCP formatter.

        Args:
            use_color: Enable ANSI color codes
            use_emoji: Enable emoji indicators
            show_timestamp: Show timestamps in output
            compact: Use compact single-line format
            max_json_length: Maximum length for JSON output before truncation
            indent_json: Pretty-print JSON responses
        """
        super().__init__()
        self.use_color = use_color
        self.use_emoji = use_emoji
        self.show_timestamp = show_timestamp
        self.compact = compact
        self.max_json_length = max_json_length
        self.indent_json = indent_json

    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record with MCP-specific enhancements.
        """
        # Check if this is a tool call/response log
        tool_context = getattr(record, "tool_context", None)

        if tool_context:
            return self._format_tool_log(record, tool_context)
        else:
            return self._format_standard_log(record)

    def _format_tool_log(self, record: logging.LogRecord, ctx: ToolCallContext) -> str:
        """
        Format a tool call or response log.
        """
        parts = []

        # Timestamp
        if self.show_timestamp:
            ts = self._colorize(self._format_timestamp(record), Colors.TIMESTAMP)
            parts.append(ts)

        # Emoji indicator
        if self.use_emoji:
            if ctx.success is None:
                emoji = Emoji.TOOL_CALL
            elif ctx.success:
                emoji = Emoji.SUCCESS
            else:
                emoji = Emoji.ERROR
            parts.append(emoji)

        # Log level / type
        if ctx.success is None:
            label = "CALL"
            color = Colors.INFO
        elif ctx.success:
            label = "SUCCESS"
            color = Colors.SUCCESS
        else:
            label = "FAILED"
            color = Colors.ERROR

        parts.append(self._colorize(label.ljust(8), color))

        # Tool name
        tool_name = self._colorize(ctx.tool_name, Colors.TOOL)
        parts.append(tool_name)

        # Call ID (if available)
        if ctx.call_id:
            call_id = self._colorize(f"[{ctx.call_id}]", Colors.DIM)
            parts.append(call_id)

        # Duration (if available)
        if ctx.duration_ms is not None:
            duration = self._format_duration(ctx.duration_ms)
            parts.append(self._colorize(duration, Colors.TIMESTAMP))

        # Main message
        message = record.getMessage()
        parts.append(message)

        # Build the main line
        if self.compact:
            result = " ".join(parts)
        else:
            result = " | ".join(parts)

        # Add parameters (for tool calls)
        if ctx.params and ctx.success is None:
            param_str = self._format_params(ctx.params)
            result += f"\n  {self._colorize('Params:', Colors.KEY)} {param_str}"

        # Add error details (for failures)
        if ctx.error:
            error_str = self._colorize(f"Error: {ctx.error}", Colors.ERROR)
            result += f"\n  {error_str}"

        # Add response (for successes)
        if ctx.response is not None and not self.compact:
            response_str = self._format_response(ctx.response)
            result += f"\n  {self._colorize('Response:', Colors.KEY)} {response_str}"

        return result

    def _format_standard_log(self, record: logging.LogRecord) -> str:
        """
        Format a standard (non-tool) log record.
        """
        parts = []

        # Timestamp
        if self.show_timestamp:
            ts = self._colorize(self._format_timestamp(record), Colors.TIMESTAMP)
            parts.append(ts)

        # Level with emoji
        level_str = record.levelname
        if self.use_emoji:
            emoji_map = {
                "DEBUG": Emoji.DEBUG,
                "INFO": Emoji.INFO,
                "WARNING": Emoji.WARNING,
                "ERROR": Emoji.ERROR,
                "CRITICAL": Emoji.ERROR,
            }
            emoji = emoji_map.get(level_str, "")
            if emoji:
                parts.append(emoji)

        # Colored level
        color_map = {
            "DEBUG": Colors.DEBUG,
            "INFO": Colors.INFO,
            "WARNING": Colors.WARNING,
            "ERROR": Colors.ERROR,
            "CRITICAL": Colors.ERROR,
        }
        color = color_map.get(level_str, Colors.RESET)
        parts.append(self._colorize(level_str.ljust(8), color))

        # Logger name
        parts.append(self._colorize(record.name, Colors.DIM))

        # Message
        parts.append(record.getMessage())

        # Context (if any)
        context = getattr(record, "context", {})
        if context:
            context_str = self._format_params(context)
            parts.append(context_str)

        return " | ".join(parts)

    def _format_params(self, params: Dict[str, Any]) -> str:
        """
        Format parameters as key=value pairs.
        """
        items = []
        for key, value in params.items():
            key_str = self._colorize(key, Colors.KEY)
            value_str = self._colorize(self._format_value(value), Colors.VALUE)
            items.append(f"{key_str}={value_str}")
        return " ".join(items)

    def _format_value(self, value: Any) -> str:
        """
        Format a value for display.
        """
        if isinstance(value, str):
            if len(value) > 50:
                return f'"{value[:47]}..."'
            return f'"{value}"'
        elif isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        else:
            return str(value)

    def _format_response(self, response: Any) -> str:
        """
        Format a response payload.
        """
        if isinstance(response, (dict, list)):
            json_str = json.dumps(
                response, ensure_ascii=False, indent=2 if self.indent_json else None
            )

            # Truncate if too long
            if len(json_str) > self.max_json_length:
                json_str = json_str[: self.max_json_length] + "..."

            return json_str
        else:
            return str(response)

    def _format_duration(self, duration_ms: float) -> str:
        """
        Format duration in human-readable form.
        """
        if duration_ms < 1000:
            return f"{duration_ms:.0f}ms"
        else:
            return f"{duration_ms/1000:.2f}s"

    def _format_timestamp(self, record: logging.LogRecord) -> str:
        """
        Format timestamp.
        """
        import time

        return time.strftime("%H:%M:%S", time.localtime(record.created))

    def _colorize(self, text: str, color: str) -> str:
        """
        Apply color to text if colors are enabled.
        """
        if self.use_color:
            return f"{color}{text}{Colors.RESET}"
        return text


def create_mcp_logger(
    name: str,
    *,
    level: str = "INFO",
    use_color: bool = True,
    use_emoji: bool = True,
    compact: bool = False,
) -> logging.Logger:
    """Create a logger configured with MCP formatter.

    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        use_color: Enable colored output
        use_emoji: Enable emoji indicators
        compact: Use compact format

    Returns:
        Configured logger instance

    Example:
        logger = create_mcp_logger("atoms.mcp")

        # Log a tool call
        logger.info(
            "Calling entity_tool",
            extra={
                "tool_context": ToolCallContext(
                    tool_name="entity_tool",
                    params={"operation": "create", "entity_type": "project"},
                    call_id="123"
                )
            }
        )
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    logger.handlers.clear()

    # Add MCP formatter
    handler = logging.StreamHandler()
    handler.setFormatter(
        MCPFormatter(
            use_color=use_color,
            use_emoji=use_emoji,
            compact=compact,
        )
    )
    logger.addHandler(handler)

    return logger
