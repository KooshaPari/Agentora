"""Platform-specific shims and cross-platform utilities.

Provides port checking, process detection, and cross-platform compatibility utilities
for different operating systems.
"""

import logging
import shutil
import socket
import subprocess
import time

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

logger = logging.getLogger(__name__)

_LSOF_MISSING_LOGGED = False


def _resolve_lsof() -> str | None:
    """Resolve path to lsof binary.

    Order:
    - KINFRA_LSOF_PATH env var
    - shutil.which("lsof")
    - common path /usr/sbin/lsof if exists
    """
    import os

    path = os.environ.get("KINFRA_LSOF_PATH")
    if path:
        return path
    exe = shutil.which("lsof")
    if exe:
        return exe
    # Try common path implicitly present on macOS
    try:
        import os

        if os.path.exists("/usr/sbin/lsof"):
            return "/usr/sbin/lsof"
    except Exception:
        pass
    return None


def is_port_free(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is free by attempting to bind to it.

    Args:
        port: Port number to check
        host: Host address to bind to (default: '127.0.0.1')

    Returns:
        True if port is free, False otherwise

    Examples:
        >>> is_port_free(8080)
        True
        >>> is_port_free(80)  # May be in use
        False
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
            return True
    except OSError:
        return False


def get_port_occupant(port: int) -> dict | None:
    """Get information about process occupying a port.

    Uses lsof (if available) for fast lookups, falls back to psutil scan.

    Args:
        port: Port number to check

    Returns:
        Dictionary with process information if found:
        - pid: Process ID
        - name: Process name
        - cmdline: Full command line
        - cwd: Current working directory (if available)
        - create_time: Process creation time

        None if no process found or permission denied.

    Examples:
        >>> info = get_port_occupant(8080)
        >>> if info:
        ...     print(f"Port occupied by PID {info['pid']}: {info['name']}")
    """
    if not PSUTIL_AVAILABLE:
        logger.warning("psutil not available, cannot detect port occupant")
        return None

    # Try lsof first (faster on Unix systems)
    lsof = _resolve_lsof()
    if lsof:
        try:
            result = subprocess.run(
                [lsof, "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
                check=False, capture_output=True,
                text=True,
                timeout=2.0,
            )
            if result.returncode == 0 and result.stdout.strip():
                pid = int(result.stdout.strip().split("\n")[0])
                try:
                    proc = psutil.Process(pid)
                    return {
                        "pid": pid,
                        "name": proc.name(),
                        "cmdline": " ".join(proc.cmdline()) if proc.cmdline() else "",
                        "cwd": proc.cwd() if hasattr(proc, "cwd") else None,
                        "create_time": proc.create_time(),
                    }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except (subprocess.TimeoutExpired, ValueError, OSError):
            pass
    else:
        global _LSOF_MISSING_LOGGED
        if not _LSOF_MISSING_LOGGED:
            logger.info(
                "lsof not found in PATH; set KINFRA_LSOF_PATH or install lsof for faster and more reliable port detection",
            )
            _LSOF_MISSING_LOGGED = True

    # Fallback to psutil scan
    try:
        for conn in psutil.net_connections(kind="inet"):
            if (
                hasattr(conn, "laddr")
                and conn.laddr
                and conn.laddr.port == port
                and conn.status == psutil.CONN_LISTEN
            ) and conn.pid:
                try:
                    proc = psutil.Process(conn.pid)
                    return {
                        "pid": conn.pid,
                        "name": proc.name(),
                        "cmdline": " ".join(proc.cmdline()) if proc.cmdline() else "",
                        "cwd": proc.cwd() if hasattr(proc, "cwd") else None,
                        "create_time": proc.create_time(),
                    }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
    except psutil.AccessDenied:
        # On macOS and some systems, psutil.net_connections requires elevated privileges.
        # Fall back silently; try lsof fast path next time. Use DEBUG to avoid noisy logs.
        logger.debug(
            "Insufficient permissions to scan network connections; try running with lsof available or elevated privileges",
        )

    return None


def kill_processes_on_port(port: int, timeout: float = 5.0) -> bool:
    """Kill all processes listening on a specific port.

    Args:
        port: Port number to clear
        timeout: Timeout for graceful termination (default: 5.0)

    Returns:
        True if any processes were killed, False otherwise

    Examples:
        >>> kill_processes_on_port(8080)
        True  # Killed processes on port 8080
        >>> kill_processes_on_port(9999)
        False  # No processes on port 9999
    """
    logger.info(f"Checking for processes on port {port}")

    if not PSUTIL_AVAILABLE:
        logger.warning("psutil not available, cannot kill processes")
        return False

    killed = False
    found_processes = []

    try:
        # Need root privileges for net_connections on some systems
        connections = psutil.net_connections(kind="inet")
        for conn in connections:
            if (
                hasattr(conn, "laddr")
                and conn.laddr
                and conn.laddr.port == port
                and conn.status == psutil.CONN_LISTEN
            ) and conn.pid:
                try:
                    proc = psutil.Process(conn.pid)
                    proc_info = f"{conn.pid} ({proc.name()})"
                    found_processes.append(proc_info)

                    logger.info(f"Killing process {proc_info} on port {port}")

                    if terminate_process(conn.pid, timeout=timeout):
                        killed = True

                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    logger.exception(f"Could not kill process {conn.pid}: {e}")
    except psutil.AccessDenied:
        # Can't get connections without sudo on some systems - try alternative
        logger.debug("Access denied checking connections, trying lsof")
        killed = _kill_via_lsof(port)
    except Exception as e:
        logger.exception(f"Error checking port {port}: {e}")

    if killed:
        # Wait a bit for port to be released
        time.sleep(0.1)

    return killed


def _kill_via_lsof(port: int) -> bool:
    """Kill processes using lsof (fallback for permission issues).

    Internal helper function.
    """
    try:
        lsof = _resolve_lsof()
        if not lsof:
            return False
        result = subprocess.run(
            [lsof, "-ti", f":{port}"], check=False, capture_output=True, text=True, timeout=5,
        )

        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            for pid_str in pids:
                try:
                    pid = int(pid_str)
                    logger.info(f"Killing process {pid} on port {port} via lsof")
                    subprocess.run(["kill", "-9", str(pid)], check=False, timeout=5)
                except Exception as e:
                    logger.exception(f"Could not kill process {pid_str}: {e}")
            return True
    except Exception as e:
        logger.debug(f"lsof fallback failed: {e}")

    return False


def _is_likely_our_cmd(cmdline: str, name: str | None = None) -> bool:
    """Best-effort detection that a process belongs to our dev stack.

    Uses simple substring checks; intentionally conservative to avoid terminating
    unrelated processes.
    """
    s = (cmdline or "").lower()
    n = (name or "").lower()
    indicators = {
        # Core project markers
        "kinfra",
        "tunnel_manager",
        "tunnel_sync",
        "cloudflared",
        # Common service names in this workspace
        "mcp",
        "fastmcp",
        "zen",
        "atoms",
        # Fallback/proxy components
        "fallback_server",
        "proxy_server",
        "smart proxy",
        # Python entrypoints
        "python",
        "uvicorn",
        "gunicorn",
    }
    return any(tok in s or tok in n for tok in indicators)


import contextlib

from ..port_registry import PortRegistry
from .identity import get_project_id

# Import for circular dependency
from .process_lifecycle import terminate_process


def free_port_if_likely_ours(port: int, *, timeout: float = 5.0) -> bool:
    """If the given port is occupied by a same-project process, terminate it.

    Uses PortRegistry to determine ownership. Only terminates when the occupying process
    is registered to this project. Falls back to conservative heuristics if no registry
    info is available.

    Returns True if port is free after the attempt (either was free, or the occupant was
    terminated successfully).
    """
    if is_port_free(port):
        return True

    occ = get_port_occupant(port)
    if not occ:
        return False

    # Registry-based ownership check
    try:
        registry = PortRegistry()
        service_name = registry.is_port_registered(port)
    except Exception:
        service_name = None

    our_project = None
    with contextlib.suppress(Exception):
        our_project = get_project_id()

    # If registry says someone owns this port, only proceed if it's ours
    if service_name and our_project:
        # Expect service names like "fallback:<project>" or "proxy:<project>"
        owned_project = service_name.split(":", 1)[1] if ":" in service_name else service_name
        if owned_project != our_project:
            logger.debug(
                "Port %s registered to '%s' (ours: '%s'); not terminating",
                port,
                service_name,
                our_project,
            )
            return False

    pid = occ.get("pid")
    name = occ.get("name") or ""
    cmd = occ.get("cmdline") or ""

    # If no registry info, fall back to conservative heuristic
    if service_name is None and not _is_likely_our_cmd(cmd, name):
        logger.debug("Port %s occupied by non-matching process %s; not terminating", port, name)
        return False

    if pid is None:
        return False

    logger.info(
        "Attempting to free port %s by terminating process PID %s (%s)",
        port,
        pid,
        name,
    )
    if terminate_process(pid, timeout=timeout, force_kill=True):
        # Small grace period for socket teardown
        time.sleep(0.3)
        return is_port_free(port)

    return False


__all__ = [
    "_is_likely_our_cmd",
    "_kill_via_lsof",
    "free_port_if_likely_ours",
    "get_port_occupant",
    "is_port_free",
    "kill_processes_on_port",
]
