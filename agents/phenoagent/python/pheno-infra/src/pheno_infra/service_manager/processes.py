"""
Subprocess management, log capture, reloads.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shlex
import time
from datetime import datetime
from typing import TYPE_CHECKING

from pheno.infra.utils.process import get_port_occupant, is_port_free, terminate_process

if TYPE_CHECKING:
    from .models import ServiceConfig

logger = logging.getLogger(__name__)


class ProcessMixin:
    _max_log_lines: int = 400

    def _format_env(self, config: ServiceConfig) -> dict[str, str]:
        env = dict(os.environ)
        if config.env:
            env.update(config.env)
        if config.port:
            env.setdefault("PORT", str(config.port))
        return env

    async def _spawn(self, config: ServiceConfig) -> asyncio.subprocess.Process:
        cmd = (
            config.command
            if isinstance(config.command, (list, tuple))
            else shlex.split(" ".join(config.command))
        )
        env = self._format_env(config)
        # Ensure the desired port is free (terminate stale processes if needed)
        if config.port and not is_port_free(config.port):
            occupant = get_port_occupant(config.port)
            if occupant and occupant.get("pid"):
                logger.warning(
                    "Port %s occupied by PID %s (%s); attempting to terminate",
                    config.port,
                    occupant["pid"],
                    occupant.get("cmdline", "unknown"),
                )
                if terminate_process(occupant["pid"]):
                    await asyncio.sleep(0.5)

        return await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(config.cwd) if config.cwd else None,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

    def _emit_live_log(self, name: str, raw_line: str, stream_type: str) -> None:
        """Emit a live log line to stdout to appear above the TUI.

        ServiceManager owns the subprocess streams, so we stream here to avoid competing
        readers and ensure live output regardless of monitor wiring.
        """
        try:
            ts = time.strftime("%H:%M:%S")
            prefix = f"[{name}:{stream_type}]"
            print(f"{ts} {prefix} {raw_line}")
        except Exception:
            pass

    async def _capture_stream_logs(self, name: str, stream, stream_type: str):
        status = self.service_status.get(name)
        if not status:
            return
        try:
            while not self._shutdown:
                line = await stream.readline()
                if not line:
                    break
                decoded = line.decode("utf-8", errors="ignore")
                raw_line = decoded.rstrip("\n")
                text = raw_line.strip()
                if not text:
                    continue
                level = "info"
                lower = text.lower()
                if any(k in lower for k in ("error", "exception", "traceback")):
                    level = "error"
                elif any(k in lower for k in ("warn", "warning")):
                    level = "warn"
                elif "debug" in lower:
                    level = "debug"
                if stream_type == "stderr" and level == "info":
                    level = "warn"
                entry = {
                    "timestamp": datetime.now().isoformat(),
                    "level": level,
                    "message": text,
                    "source": stream_type,
                }
                status.logs.append(entry)
                if len(status.logs) > self._max_log_lines:
                    status.logs = status.logs[-self._max_log_lines :]
                # Route log updates to fallback (local or remote) via emit_status if available
                try:
                    if hasattr(self, "emit_status"):
                        self.emit_status(name, logs=status.logs, last_output=raw_line)  # type: ignore[attr-defined]
                    elif self.fallback_server:  # type: ignore[attr-defined]
                        self.fallback_server.update_service_status(service_name=name, logs=status.logs, last_output=raw_line)  # type: ignore[attr-defined]
                except Exception:
                    logger.debug("log emit_status failed", exc_info=True)
                status.last_output = raw_line
                if level == "error":
                    logger.error("[%s] %s", name, text)
                elif level == "warn":
                    logger.warning("[%s] %s", name, text)
                else:
                    logger.debug("[%s] %s", name, text)

                # Optional: infer lifecycle stages from logs
                try:
                    service_patterns = getattr(self, "_service_log_stage_patterns", {})
                    patterns = service_patterns.get(name) or getattr(
                        self, "_default_log_stage_patterns", None,
                    )
                    if patterns:
                        lower = text.lower()
                        for needle, stage_text, stage_status in patterns:
                            if needle in lower:
                                if hasattr(self, "emit_stage"):
                                    self.emit_stage(name, stage_text, stage_status)  # type: ignore[attr-defined]
                                break
                except Exception:
                    logger.debug("emit_stage from logs failed", exc_info=True)

                # Live stream to console above the TUI
                self._emit_live_log(name, raw_line, stream_type)
        except Exception as e:
            logger.exception("Error capturing %s for %s: %s", stream_type, name, e)

    def _start_log_capture(self, name: str) -> None:
        proc = self.processes.get(name)
        if not proc:
            return
        if name in self._log_capture_tasks:
            for t in self._log_capture_tasks[name]:
                t.cancel()
        stdout_task = asyncio.create_task(self._capture_stream_logs(name, proc.stdout, "stdout"))
        stderr_task = asyncio.create_task(self._capture_stream_logs(name, proc.stderr, "stderr"))
        self._log_capture_tasks[name] = [stdout_task, stderr_task]

    def _stop_log_capture(self, name: str) -> None:
        if name in self._log_capture_tasks:
            for t in self._log_capture_tasks[name]:
                t.cancel()
            del self._log_capture_tasks[name]
        status = self.service_status.get(name)
        if status:
            status.last_output = None

    async def reload_service(self, name: str) -> bool:
        logger.info("Reloading service: %s", name)
        status = self.service_status[name]
        status.state = "reloading"
        await self.stop_service(name)  # type: ignore[misc]
        await asyncio.sleep(1.0)
        return await self.start_service(name)  # type: ignore[misc]
