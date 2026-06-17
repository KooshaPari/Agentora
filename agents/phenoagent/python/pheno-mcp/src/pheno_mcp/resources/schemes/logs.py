"""
Log access resource scheme.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .base import ResourceSchemeHandler
from .common import LOGGER

if TYPE_CHECKING:
    from ..template_engine import ResourceContext


class LogsResourceScheme(ResourceSchemeHandler):
    """Handler for logs:// resources - log access."""

    def __init__(self):
        super().__init__("logs")
        self.log_directory = Path("logs")

    async def handle_request(self, context: ResourceContext) -> dict[str, Any]:
        """
        Default to listing logs when invoked directly.
        """
        return await self.get_log_files(context)

    async def get_logs(self, context: ResourceContext) -> dict[str, Any]:
        """
        Get filtered logs.
        """
        level = context.get_parameter("level", "INFO").upper()
        date_str = context.get_parameter("date")
        limit = int(context.get_parameter("limit", 100))

        log_files: list[Path] = []
        if self.log_directory.exists():
            if date_str:
                log_files = list(self.log_directory.glob(f"*{date_str}*.log"))
            else:
                log_files = sorted(
                    self.log_directory.glob("*.log"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )

        if not log_files:
            return {
                "logs": [],
                "total": 0,
                "level_filter": level,
                "date_filter": date_str,
                "message": "No log files found",
            }

        filtered_logs: list[dict[str, Any]] = []
        try:
            for log_file in log_files[:3]:
                with open(log_file, encoding="utf-8") as fh:
                    lines = fh.readlines()

                for line in reversed(lines):
                    line = line.strip()
                    if not line:
                        continue

                    if level != "ALL" and level not in line:
                        continue

                    filtered_logs.append(
                        {
                            "timestamp": self._extract_timestamp(line),
                            "level": self._extract_level(line),
                            "message": line,
                            "file": log_file.name,
                        },
                    )

                    if len(filtered_logs) >= limit:
                        break

                if len(filtered_logs) >= limit:
                    break

        except Exception as exc:  # pragma: no cover - defensive
            LOGGER.error("Error reading log files: %s", exc)
            return {"error": str(exc)}

        return {
            "logs": filtered_logs,
            "total": len(filtered_logs),
            "level_filter": level,
            "date_filter": date_str,
            "limit": limit,
            "timestamp": int(time.time()),
        }

    async def get_log_files(self, context: ResourceContext) -> dict[str, Any]:
        """
        List available log files.
        """
        if not self.log_directory.exists():
            return {"files": [], "total": 0}

        files: list[dict[str, Any]] = []
        for log_file in self.log_directory.glob("*.log"):
            stat = log_file.stat()
            files.append(
                {
                    "name": log_file.name,
                    "path": str(log_file),
                    "size_bytes": stat.st_size,
                    "modified_time": int(stat.st_mtime),
                    "created_time": int(stat.st_ctime),
                },
            )

        files.sort(key=lambda entry: entry["modified_time"], reverse=True)

        return {
            "files": files,
            "total": len(files),
            "directory": str(self.log_directory),
            "timestamp": int(time.time()),
        }

    def _extract_timestamp(self, log_line: str) -> str | None:
        """
        Extract timestamp from log line.
        """
        import re

        match = re.match(r"^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})", log_line)
        return match.group(1) if match else None

    def _extract_level(self, log_line: str) -> str:
        """
        Extract log level from log line.
        """
        for level in ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]:
            if level in log_line:
                return level
        return "UNKNOWN"


__all__ = ["LogsResourceScheme"]
