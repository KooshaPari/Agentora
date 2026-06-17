"""
Structured formatter for MCP-QA logs.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Optional

_LEVEL_COLORS = {
    "DEBUG": "\033[36m",
    "INFO": "\033[32m",
    "WARNING": "\033[33m",
    "ERROR": "\033[31m",
    "CRITICAL": "\033[35m",
}
_RESET = "\033[0m"


class StructuredFormatter(logging.Formatter):
    def __init__(
        self,
        *,
        json_mode: bool = False,
        color: bool = True,
        show_time: bool = True,
        json_indent: Optional[int] = None,
    ) -> None:
        super().__init__()
        self.json_mode = json_mode
        self.color = color
        self.show_time = show_time
        self.json_indent = json_indent

    def format(self, record: logging.LogRecord) -> str:
        context: Dict[str, Any] = getattr(record, "context", {}) or {}
        payload: Dict[str, Any] = {
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }

        if self.show_time:
            payload["time"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record.created))

        if context:
            payload.update(context)

        if self.json_mode:
            return json.dumps(payload, ensure_ascii=False, indent=self.json_indent)

        level = payload.pop("level")
        timestamp = payload.pop("time", "") if self.show_time else ""
        name = payload.pop("name")
        message = payload.pop("message")

        level_display = level
        if self.color:
            color_code = _LEVEL_COLORS.get(level)
            if color_code:
                level_display = f"{color_code}{level}{_RESET}"

        segments = []
        if timestamp:
            segments.append(timestamp)
        segments.append(level_display)
        segments.append(name)
        segments.append(message)

        context_str = "".join(
            f" {key}={value}" for key, value in payload.items() if value is not None
        )

        return " | ".join(segments) + context_str
