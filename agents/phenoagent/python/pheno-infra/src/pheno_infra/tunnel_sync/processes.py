"""
Cloudflared process management and cleanup.
"""

from __future__ import annotations

import logging
import subprocess
import threading
import time

logger = logging.getLogger(__name__)


class ProcessMixin:
    def _stream_tunnel_pipe(
        self, service_name: str, process: subprocess.Popen, attr: str, stream_type: str,
    ) -> None:
        stream = getattr(process, attr, None)
        if not stream:
            return
        while True:
            try:
                line = stream.readline()
                if not line:
                    if process.poll() is not None:
                        break
                    time.sleep(0.05)
                    continue
                clean_line = line.rstrip()
                if not clean_line:
                    continue

                if getattr(self, "_tunnel_verbose", False):
                    logger.debug("[tunnel:%s:%s] %s", service_name, stream_type, clean_line)
                    if stream_type == "stderr":
                        print(clean_line)
                    continue

                lowered = clean_line.lower()
                if stream_type == "stderr" and any(
                    keyword in lowered for keyword in ("error", "fail", "panic", "fatal")
                ):
                    logger.warning("[tunnel:%s] %s", service_name, clean_line)
            except Exception:
                time.sleep(0.1)

    def _start_tunnel_process(self, service_name: str, config_path):
        self._log_tunnel(
            "Starting tunnel process for '%s' with config: %s",
            service_name,
            config_path,
            verbose=True,
        )
        self._stop_tunnel_process(service_name)
        try:
            process = subprocess.Popen(
                ["cloudflared", "tunnel", "--config", str(config_path), "run"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )
            self._running_processes[service_name] = process

            # Start live log streaming threads for stdout/stderr
            threading.Thread(
                target=self._stream_tunnel_pipe,
                args=(service_name, process, "stdout", "stdout"),
                daemon=True,
            ).start()
            threading.Thread(
                target=self._stream_tunnel_pipe,
                args=(service_name, process, "stderr", "stderr"),
                daemon=True,
            ).start()

            self._log_tunnel(
                "Started tunnel process for '%s' (PID: %s)", service_name, process.pid, verbose=True,
            )
            self.registry.update_service(service_name, pid=process.pid)
        except OSError as e:
            from ..exceptions import TunnelError

            raise TunnelError(f"Failed to start tunnel process for '{service_name}': {e}")

    def _stop_tunnel_process(self, service_name: str) -> bool:
        if service_name in self._running_processes:
            process = self._running_processes[service_name]
            self._log_tunnel(
                "Stopping tunnel process for '%s' (PID: %s)",
                service_name,
                process.pid,
                verbose=True,
            )
            try:
                process.terminate()
                process.wait(timeout=5.0)
                del self._running_processes[service_name]
                self._log_tunnel(
                    "Tunnel process for '%s' stopped gracefully", service_name, verbose=True,
                )
                return True
            except subprocess.TimeoutExpired:
                logger.warning("Force killing tunnel process for '%s'", service_name)
                process.kill()
                process.wait()
                del self._running_processes[service_name]
                return True
            except Exception as e:
                logger.exception("Error stopping tunnel process for '%s': %s", service_name, e)
                return False
        return False

    def _is_tunnel_running(self, tunnel_id: str, hostname: str) -> bool:
        for service_name, process in self._running_processes.items():
            if process and process.poll() is None:
                service_info = self.registry.get_service(service_name)
                if service_info and service_info.tunnel_id == tunnel_id:
                    logger.debug("Tunnel %s is running (PID: %s)", tunnel_id, process.pid)
                    return True
        try:
            result = subprocess.run(
                ["pgrep", "-f", f"cloudflared.*{tunnel_id}"],
                check=False, capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0 and result.stdout.strip():
                logger.debug("Found cloudflared process for tunnel %s", tunnel_id)
                return True
        except Exception as e:
            logger.debug("Error checking for cloudflared process: %s", e)
        logger.debug("Tunnel %s is NOT running", tunnel_id)
        return False

    def cleanup_all(self):
        self._log_tunnel("Cleaning up all tunnel processes", verbose=True)
        for service_name in list(self._running_processes.keys()):
            self._stop_tunnel_process(service_name)
        self._running_processes.clear()
