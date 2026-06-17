"""Process lifecycle management for Pheno infrastructure.

Provides process termination, cleanup of orphaned processes, and safe process lifecycle
operations.
"""

import logging

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

logger = logging.getLogger(__name__)


def terminate_process(pid: int, timeout: float = 5.0, force_kill: bool = True) -> bool:
    """Safely terminate a process with graceful shutdown attempt.

    First attempts graceful termination (SIGTERM), then force kills (SIGKILL)
    if process doesn't terminate within the timeout.

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
    attempted: List[psutil.Process] = []

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


__all__ = [
    "cleanup_orphaned_processes",
    "terminate_process",
]
