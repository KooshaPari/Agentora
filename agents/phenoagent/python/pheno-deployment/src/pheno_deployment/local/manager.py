"""
Runtime helpers for orchestrating local development processes.
"""

from __future__ import annotations

import asyncio
import os
import signal
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable, Mapping
    from pathlib import Path


@dataclass(slots=True)
class LocalProcessConfig:
    """
    Declarative configuration for a local process to manage.
    """

    command: list[str]
    cwd: Path | None = None
    env: Mapping[str, str] | None = None
    name: str | None = None
    ready_probe: ReadyProbe | None = None


class ReadyProbe:
    """
    Async hook used to determine when a process is ready.
    """

    def __init__(self, check: Callable[[], Awaitable[bool]]):
        self._check = check

    async def __call__(self) -> bool:
        return await self._check()


class LocalServiceManager:
    """
    Spawn and supervise a collection of local development processes.
    """

    def __init__(self):
        self._processes: dict[str, subprocess.Popen] = {}

    async def start(self, configs: Iterable[LocalProcessConfig]) -> None:
        """
        Start all configured processes sequentially.
        """

        for config in configs:
            name = config.name or "process"
            if name in self._processes:
                raise RuntimeError(f"{name} already started")

            proc = subprocess.Popen(
                config.command,
                cwd=str(config.cwd) if config.cwd else None,
                env=self._build_env(config.env),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            self._processes[name] = proc

            if config.ready_probe is not None:
                await self._wait_for_probe(name, config.ready_probe)

    async def _wait_for_probe(self, name: str, probe: ReadyProbe, timeout: int = 30) -> None:
        try:
            ready = await asyncio.wait_for(probe(), timeout=timeout)
            if not ready:
                raise RuntimeError("probe reported not ready")
        except TimeoutError as exc:  # pragma: no cover - defensive path
            raise RuntimeError(f"{name} failed readiness probe within {timeout}s") from exc
        except Exception as exc:  # pragma: no cover - propagate errors
            raise RuntimeError(f"{name} readiness probe failed: {exc}") from exc

    def stream_logs(self, *, prefix: bool = True) -> None:
        """
        Stream combined stdout/stderr for all processes synchronously.
        """

        for name, proc in self._processes.items():
            if proc.stdout is None:
                continue

            for line in proc.stdout:
                line = line.rstrip()
                if prefix:
                    print(f"[{name}] {line}")
                else:
                    print(line)

    async def stop(self) -> None:
        """
        Terminate all managed processes gracefully.
        """

        for name, proc in list(self._processes.items()):
            if proc.poll() is None:
                proc.send_signal(signal.SIGINT)
                try:
                    await asyncio.wait_for(asyncio.to_thread(proc.wait), timeout=10)
                except TimeoutError:
                    proc.kill()
            self._processes.pop(name, None)

    def status(self) -> dict[str, str]:
        """
        Return status map for each managed process.
        """

        statuses: dict[str, str] = {}
        for name, proc in self._processes.items():
            code = proc.poll()
            statuses[name] = "running" if code is None else f"exited({code})"
        return statuses

    def _build_env(self, extra: Mapping[str, str] | None) -> dict[str, str]:
        env = os.environ.copy()
        if extra:
            env.update(extra)
        return env


__all__ = ["LocalProcessConfig", "LocalServiceManager", "ReadyProbe"]
