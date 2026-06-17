"""
Base class for tunnel managers.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .types import CloudflareTunnelError


class BaseTunnelManager:
    def __init__(self, config, cloudflared_path: str | None = None):
        self.config = config
        self.cloudflared_path = cloudflared_path or self._find_cloudflared()
        self._process = None
        self._temp_files: list[Path] = []

        import logging

        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger.setLevel(getattr(logging, getattr(config, "log_level", "info").upper(), 20))

    def _find_cloudflared(self) -> str:
        cloudflared = shutil.which("cloudflared")
        if not cloudflared:
            raise CloudflareTunnelError(
                "cloudflared binary not found in PATH. Please install cloudflared.",
            )
        return cloudflared

    def _create_temp_config(self, config_data: dict[str, Any]) -> Path:
        temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False, encoding="utf-8",
        )
        try:
            import yaml  # type: ignore

            yaml.dump(config_data, temp_file, default_flow_style=False)
        except Exception:
            json.dump(config_data, temp_file, indent=2)
        temp_path = Path(temp_file.name)
        self._temp_files.append(temp_path)
        return temp_path

    def cleanup(self) -> None:
        for temp_file in self._temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception as e:
                self.logger.warning(f"Failed to clean up temp file {temp_file}: {e}")
        self._temp_files.clear()
