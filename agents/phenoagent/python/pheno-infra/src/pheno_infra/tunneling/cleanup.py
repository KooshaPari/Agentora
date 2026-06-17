"""
Cleanup helpers for tunnels and stray cloudflared processes.
"""

from __future__ import annotations

import os
import signal
from typing import TYPE_CHECKING

import psutil

from .registry import tunnel_registry

if TYPE_CHECKING:
    from collections.abc import Iterable


def cleanup_all_tunnels() -> None:
    tunnel_registry.stop_all_sync_tunnels()


async def async_cleanup_all_tunnels() -> None:
    await tunnel_registry.stop_all_async_tunnels()


def cleanup_orphaned_cloudflared_processes(
    grace_period: float = 3.0,
    force_kill: bool = True,
    exclude_pids: Iterable[int] | None = None,
) -> dict[str, int]:
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
            if "cloudflared" not in name and not any(
                "cloudflared" in str(part).lower() for part in cmdline
            ):
                continue
            # Use SIGKILL immediately for cloudflared - they don't respond well to SIGTERM
            proc.kill()
            attempted.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        except Exception:
            continue

    force_killed = 0
    terminated = 0

    if attempted:
        # Since we used SIGKILL immediately, just wait for them to die
        gone, alive = psutil.wait_procs(attempted, timeout=grace_period)
        terminated += len(gone)
        force_killed += len(gone)  # All were force killed

        # Log any that survived (shouldn't happen with SIGKILL)
        for proc in alive:
            try:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"cloudflared process {proc.pid} survived SIGKILL!")
            except Exception:
                pass

    return {
        "inspected": inspected,
        "terminated": terminated,
        "force_killed": force_killed,
        "skipped": skipped,
    }


def cleanup_runtime_environment(
    grace_period: float = 3.0,
    force_kill: bool = True,
    exclude_pids: Iterable[int] | None = None,
) -> dict[str, int]:
    cleanup_all_tunnels()
    return cleanup_orphaned_cloudflared_processes(
        grace_period=grace_period, force_kill=force_kill, exclude_pids=exclude_pids,
    )


# Signal handler registration


def _signal_handler(signum: int, frame: object) -> None:  # pragma: no cover
    cleanup_all_tunnels()
    os._exit(0)


signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT, _signal_handler)
