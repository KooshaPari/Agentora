"""
Synchronous tunnel manager implementation.
"""

from __future__ import annotations

import subprocess
import time
from contextlib import contextmanager
from typing import TYPE_CHECKING

from .base import BaseTunnelManager
from .types import (
    TunnelConfig,
    TunnelInfo,
    TunnelOperationError,
    TunnelStatus,
    TunnelType,
)

if TYPE_CHECKING:
    from collections.abc import Iterator


class SyncTunnelManager(BaseTunnelManager):
    def __init__(self, config: TunnelConfig, cloudflared_path: str | None = None):
        super().__init__(config, cloudflared_path)
        self._running = False

    def start(self) -> bool:
        if self._running:
            self.logger.warning(f"Tunnel {self.config.name} is already running")
            return True
        try:
            self.logger.info(f"Starting tunnel: {self.config.name}")
            if self.config.tunnel_type == TunnelType.QUICK:
                return self._start_quick_tunnel()
            return self._start_persistent_tunnel()
        except Exception as e:
            self.logger.exception(f"Failed to start tunnel {self.config.name}: {e}")
            raise TunnelOperationError(f"Failed to start tunnel: {e}")

    def _start_quick_tunnel(self) -> bool:
        cmd = [
            self.cloudflared_path,
            "tunnel",
            "--url",
            self.config.local_url,
            "--name",
            self.config.name,
            "--logfile",
            "-",
            "--loglevel",
            self.config.log_level,
        ]
        if self.config.hostname:
            cmd.extend(["--hostname", self.config.hostname])
        if self.config.no_autoupdate:
            cmd.append("--no-autoupdate")

        self.logger.debug(f"Executing command: {' '.join(cmd)}")
        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )
            time.sleep(2)
            if self._process.poll() is not None:
                _stdout, stderr = self._process.communicate()
                raise TunnelOperationError(
                    f"Process exited with code {self._process.returncode}: {stderr}",
                )
            self._running = True
            self.logger.info(f"Quick tunnel {self.config.name} started successfully")
            return True
        except subprocess.SubprocessError as e:
            self.logger.exception(f"Failed to start quick tunnel: {e}")
            return False

    def _start_persistent_tunnel(self) -> bool:
        config_data = {
            "tunnel": self.config.name,
            "credentials-file": (
                str(self.config.credentials_file) if self.config.credentials_file else None
            ),
            "ingress": self.config.ingress_rules
            or [
                {"hostname": self.config.hostname, "service": self.config.local_url},
                {"service": "http_status:404"},
            ],
        }
        config_file = self._create_temp_config(config_data)
        cmd = [self.cloudflared_path, "tunnel", "--config", str(config_file), "run"]
        if self.config.tunnel_token:
            cmd.extend(["--token", self.config.tunnel_token])
        self.logger.debug(f"Executing command: {' '.join(cmd)}")
        try:
            self._process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            time.sleep(2)
            if self._process.poll() is not None:
                _stdout, stderr = self._process.communicate()
                raise TunnelOperationError(
                    f"Process exited with code {self._process.returncode}: {stderr}",
                )
            self._running = True
            self.logger.info(f"Persistent tunnel {self.config.name} started successfully")
            return True
        except subprocess.SubprocessError as e:
            self.logger.exception(f"Failed to start persistent tunnel: {e}")
            return False

    def stop(self) -> bool:
        if not self._running or not self._process:
            self.logger.warning(f"Tunnel {self.config.name} is not running")
            return True
        try:
            self.logger.info(f"Stopping tunnel: {self.config.name}")
            self._process.terminate()
            try:
                self._process.wait(timeout=self.config.grace_period)
            except subprocess.TimeoutExpired:
                self.logger.warning("Graceful shutdown failed, forcing termination")
                self._process.kill()
                self._process.wait()
            self._running = False
            self._process = None
            self.cleanup()
            self.logger.info(f"Tunnel {self.config.name} stopped successfully")
            return True
        except Exception as e:
            self.logger.exception(f"Failed to stop tunnel {self.config.name}: {e}")
            return False

    def get_status(self) -> TunnelStatus:
        if not self._process:
            return TunnelStatus.STOPPED
        poll_result = self._process.poll()
        if poll_result is None:
            return TunnelStatus.RUNNING if self._running else TunnelStatus.STARTING
        if poll_result == 0:
            self._running = False
            return TunnelStatus.STOPPED
        self._running = False
        return TunnelStatus.ERROR

    def get_info(self) -> TunnelInfo:
        return TunnelInfo(
            name=self.config.name,
            status=self.get_status(),
            process_id=self._process.pid if self._process else None,
            config=self.config,
        )

    @contextmanager
    def managed_tunnel(self) -> Iterator[SyncTunnelManager]:
        try:
            self.start()
            yield self
        finally:
            self.stop()
            self.cleanup()
