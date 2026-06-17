"""Process Management Utilities.

Common utilities for port checking, process detection, and termination. Extracted from
smart_allocator.py, service_manager.py, and tunnel_manager.py.
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
    """Get information about the process occupying a port.

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
    if shutil.which("lsof"):
        try:
            result = subprocess.run(
                ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
                capture_output=True,
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
        logger.warning("Insufficient permissions to scan network connections")

    return None


def terminate_process(pid: int, timeout: float = 5.0, force_kill: bool = True) -> bool:
    """Safely terminate a process with graceful shutdown attempt.

    First attempts graceful termination (SIGTERM), then force kills (SIGKILL)
    if the process doesn't terminate within the timeout.

    Args:
        pid: Process ID to terminate
        timeout: Seconds to wait for graceful termination (default: 5.0)
        force_kill: Whether to force kill if graceful termination fails (default: True)

    Returns:
        True if process was terminated successfully, False otherwise

    Examples:
        >>> terminate_process(12345)
        True
        >>> terminate_process(12345, timeout=10.0, force_kill=False)
        False  # Process didn't terminate gracefully
    """
    if not PSUTIL_AVAILABLE:
        logger.warning("psutil not available, cannot terminate process")
        return False

    try:
        proc = psutil.Process(pid)
        logger.info(f"Terminating process {pid} ({proc.name()})")

        # Try graceful termination first
        proc.terminate()

        # Wait for graceful shutdown
        try:
            proc.wait(timeout=timeout)
            logger.info(f"Process {pid} terminated gracefully")
            return True
        except psutil.TimeoutExpired:
            if force_kill:
                # Force kill if graceful termination fails
                logger.warning(f"Force killing process {pid}")
                proc.kill()
                proc.wait(timeout=2.0)
                logger.info(f"Process {pid} force killed")
                return True
            logger.warning(f"Process {pid} did not terminate gracefully within {timeout}s")
            return False

    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired) as e:
        logger.warning(f"Failed to terminate process {pid}: {e}")
        return False


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
        time.sleep(1.0)

    return killed


def _kill_via_lsof(port: int) -> bool:
    """Kill processes using lsof (fallback for permission issues).

    Internal helper function.
    """
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"], capture_output=True, text=True, timeout=5,
        )

        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            for pid_str in pids:
                try:
                    pid = int(pid_str)
                    logger.info(f"Killing process {pid} on port {port} via lsof")
                    subprocess.run(["kill", "-9", str(pid)], timeout=5)
                except Exception as e:
                    logger.exception(f"Could not kill process {pid_str}: {e}")
            return True
    except Exception as e:
        logger.debug(f"lsof fallback failed: {e}")

    return False


def cleanup_orphaned_processes(
    grace_period: float = 3.0,
    force_kill: bool = True,
    exclude_pids: set[int] | None = None,
    process_name_pattern: str = "cloudflared",
) -> dict[str, int]:
    """Terminate orphaned processes matching a pattern.

    Useful for cleaning up stale cloudflared or other background processes
    that were not properly terminated.

    Args:
        grace_period: Seconds to wait after SIGTERM before SIGKILL (default: 3.0)
        force_kill: Whether to force kill stubborn processes (default: True)
        exclude_pids: Set of PIDs to exclude from cleanup (default: None)
        process_name_pattern: Process name pattern to match (default: "cloudflared")

    Returns:
        Dictionary with cleanup statistics:
        - inspected: Total processes inspected
        - terminated: Processes terminated gracefully
        - force_killed: Processes force killed
        - skipped: Processes skipped (excluded)

    Examples:
        >>> cleanup_orphaned_processes()
        {'inspected': 156, 'terminated': 2, 'force_killed': 0, 'skipped': 1}

        >>> cleanup_orphaned_processes(process_name_pattern="python")
        {'inspected': 156, 'terminated': 5, 'force_killed': 1, 'skipped': 2}
    """
    if not PSUTIL_AVAILABLE:
        logger.warning("psutil not available, cannot cleanup orphaned processes")
        return {"inspected": 0, "terminated": 0, "force_killed": 0, "skipped": 0}

    import os

    try:
        current_pid = os.getpid()
    except Exception:
        current_pid = None

    excluded: set[int] = set(exclude_pids or [])
    if current_pid is not None:
        excluded.add(current_pid)

    inspected = 0
    skipped = 0
    attempted: list[psutil.Process] = []

    pattern_lower = process_name_pattern.lower()

    for proc in psutil.process_iter(["pid", "name", "cmdline", "ppid"]):
        inspected += 1

        try:
            pid = proc.info.get("pid")
            if pid is None:
                continue

            if pid in excluded or proc.info.get("ppid") in excluded:
                skipped += 1
                continue

            name = (proc.info.get("name") or "").lower()
            cmdline = proc.info.get("cmdline") or []

            if pattern_lower not in name and not any(
                pattern_lower in str(part).lower() for part in cmdline
            ):
                continue

            logger.info(f"Terminating orphaned {process_name_pattern} process (pid={pid})")
            proc.terminate()
            attempted.append(proc)

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        except Exception as exc:
            logger.debug(f"Unable to inspect process during cleanup: {exc}")
            continue

    force_killed = 0
    terminated = 0

    if attempted:
        gone, alive = psutil.wait_procs(attempted, timeout=grace_period)
        terminated += len(gone)

        for proc in alive:
            if not force_kill:
                logger.warning(
                    f"{process_name_pattern} process (pid={proc.pid}) ignored SIGTERM; "
                    f"leaving running due to force_kill=False",
                )
                continue

            try:
                logger.warning(
                    f"Force killing stubborn {process_name_pattern} process (pid={proc.pid})",
                )
                proc.kill()
                force_killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception as exc:
                logger.exception(
                    f"Failed to force kill {process_name_pattern} process {proc.pid}: {exc}",
                )

        if force_kill and alive:
            gone_after_kill, still_alive = psutil.wait_procs(alive, timeout=grace_period)
            terminated += len(gone_after_kill)
            for proc in still_alive:
                logger.error(
                    f"{process_name_pattern} process (pid={proc.pid}) survived cleanup attempts",
                )

    return {
        "inspected": inspected,
        "terminated": terminated,
        "force_killed": force_killed,
        "skipped": skipped,
    }
