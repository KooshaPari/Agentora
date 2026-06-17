"""
Logging configuration helpers.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Literal, Optional

from .formatter import StructuredFormatter

LogFormat = Literal["plain", "json"]


@dataclass
class LogConfig:
    level: str = "INFO"
    fmt: LogFormat = "plain"
    color: bool = True
    timestamp: bool = True
    json_indent: Optional[int] = None

    @classmethod
    def from_env(cls) -> "LogConfig":
        level = os.getenv("MCP_QA_LOG_LEVEL", "INFO").upper()
        fmt = os.getenv("MCP_QA_LOG_FORMAT", "plain").lower()
        fmt_value: LogFormat = "json" if fmt == "json" else "plain"
        color = os.getenv("MCP_QA_LOG_COLOR", "1") not in {"0", "false", "False"}
        timestamp = os.getenv("MCP_QA_LOG_TIMESTAMP", "1") not in {"0", "false", "False"}
        indent_value = os.getenv("MCP_QA_LOG_JSON_INDENT")
        json_indent = int(indent_value) if indent_value and indent_value.isdigit() else None
        return cls(
            level=level, fmt=fmt_value, color=color, timestamp=timestamp, json_indent=json_indent
        )


_configured = False


def configure_logging(config: Optional[LogConfig] = None, *, force: bool = False) -> None:
    global _configured
    if _configured and not force:
        return

    config = config or LogConfig.from_env()
    level = getattr(logging, config.level, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)

    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(
        StructuredFormatter(
            json_mode=config.fmt == "json",
            color=config.color,
            show_time=config.timestamp,
            json_indent=config.json_indent,
        )
    )

    root_logger.addHandler(handler)
    _configured = True
