"""
Utility helpers for collecting recent server logs during test failures.
"""

from __future__ import annotations

import os
import subprocess
from typing import Optional


def collect_server_logs(lines: int = 20) -> Optional[str]:
    """
    Collect recent server logs for diagnostics.
    """

    for getter in (_docker_logs, _pm2_logs, _file_logs, _vercel_logs):
        try:
            output = getter(lines)
        except Exception:  # pragma: no cover - best effort helpers
            output = None
        if output:
            return output
    return None


def _docker_logs(lines: int) -> Optional[str]:
    container = os.getenv(
        "MCP_SERVER_DOCKER_CONTAINER", os.getenv("ZEN_DOCKER_CONTAINER", "zen-mcp-server")
    )
    if not container:
        return None
    try:
        result = subprocess.run(
            ["docker", "logs", "--tail", str(lines), container],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except Exception:
        return None
    if result.returncode == 0:
        return result.stdout + result.stderr
    return None


def _pm2_logs(lines: int) -> Optional[str]:
    process = os.getenv("MCP_SERVER_PM2_PROCESS", "zen-mcp")
    try:
        result = subprocess.run(
            ["pm2", "logs", process, "--lines", str(lines), "--nostream"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except Exception:
        return None
    if result.returncode == 0:
        return result.stdout
    return None


def _file_logs(lines: int) -> Optional[str]:
    logfile = (
        os.getenv("MCP_SERVER_LOG_FILE")
        or os.getenv("ZEN_LOG_FILE")
        or "/var/log/zen-mcp/server.log"
    )
    if not os.path.exists(logfile):
        return None
    try:
        with open(logfile, "r", encoding="utf-8", errors="ignore") as handle:
            return "".join(handle.readlines()[-lines:])
    except Exception:
        return None


def _vercel_logs(lines: int) -> Optional[str]:
    project = os.getenv("VERCEL_PROJECT", "zen-mcp-server")
    try:
        result = subprocess.run(
            ["vercel", "logs", project, "--output", "raw", f"--lines={lines}"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return None
    if result.returncode == 0:
        return result.stdout
    return None


__all__ = ["collect_server_logs"]
