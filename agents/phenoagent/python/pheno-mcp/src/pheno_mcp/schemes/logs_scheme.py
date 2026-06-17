"""Logs Scheme Handler.

Provides access to application logs via logs:// URIs.
"""

from collections import deque
from datetime import datetime
from typing import Any

from pheno.ports.mcp import ResourceSchemeHandler


class LogsSchemeHandler(ResourceSchemeHandler):
    """Handler for logs:// scheme.

    Provides access to application logs.

    URI Format:
        logs://app/errors  (get error logs)
        logs://app/all?limit=100  (get last 100 logs)
        logs://app/all?level=ERROR  (get ERROR level logs)
        logs://app/all?since=2024-01-01  (get logs since date)

    Example:
        >>> handler = LogsSchemeHandler()
        >>> errors = await handler.get_resource("logs://app/errors")
        >>> recent = await handler.get_resource("logs://app/all?limit=50")
    """

    def __init__(self, max_logs: int = 10000):
        """Initialize logs scheme handler.

        Args:
            max_logs: Maximum number of logs to keep in memory
        """
        self.max_logs = max_logs
        self._logs: deque = deque(maxlen=max_logs)

    def add_log(self, level: str, message: str, **context) -> None:
        """Add a log entry.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            **context: Additional context
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "context": context,
        }
        self._logs.append(log_entry)

    async def get_resource(self, uri: str) -> Any:
        """Get logs.

        Args:
            uri: URI in format logs://app/category?filters

        Returns:
            List of log entries

        Example:
            >>> logs = await handler.get_resource("logs://app/errors?limit=10")
        """
        # Parse URI
        parts = uri.split("://", 1)[1].split("?")
        path = parts[0]
        query = self._parse_query(parts[1] if len(parts) > 1 else "")

        # Get category
        category = path.split("/")[-1] if "/" in path else "all"

        # Filter logs
        logs = list(self._logs)

        # Filter by category
        if category == "errors":
            logs = [log for log in logs if log["level"] in ["ERROR", "CRITICAL"]]
        elif category == "warnings":
            logs = [log for log in logs if log["level"] == "WARNING"]

        # Apply query filters
        if "level" in query:
            logs = [log for log in logs if log["level"] == query["level"]]

        if "since" in query:
            since = datetime.fromisoformat(query["since"])
            logs = [log for log in logs if datetime.fromisoformat(log["timestamp"]) >= since]

        if "limit" in query:
            limit = int(query["limit"])
            logs = logs[-limit:]

        return logs

    async def list_resources(self, uri: str) -> list[str]:
        """List available log categories.

        Args:
            uri: URI pattern

        Returns:
            List of log category URIs

        Example:
            >>> categories = await handler.list_resources("logs://app/*")
        """
        return [
            "logs://app/all",
            "logs://app/errors",
            "logs://app/warnings",
        ]

    def supports_scheme(self, scheme: str) -> bool:
        """
        Check if scheme is supported.
        """
        return scheme == "logs"

    def _parse_query(self, query_string: str) -> dict[str, str]:
        """
        Parse query string into dict.
        """
        if not query_string:
            return {}

        params = {}
        for param in query_string.split("&"):
            if "=" in param:
                key, value = param.split("=", 1)
                params[key] = value

        return params


__all__ = ["LogsSchemeHandler"]
