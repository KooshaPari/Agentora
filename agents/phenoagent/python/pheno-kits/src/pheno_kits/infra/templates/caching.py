"""Caching resource templates."""

from pathlib import Path
from typing import Any


def redis(
    port: int = 6379,
    enable_persistence: bool = True,
    version: str = "7-alpine",
    data_dir: Path | None = None,
    scope: str | None = None,
    mode: str | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Redis template."""
    command = []
    if enable_persistence:
        command = ["redis-server", "--appendonly", "yes"]

    config = {
        "type": "docker",
        "image": f"redis:{version}",
        "container_name": kwargs.get("container_name", f"kinfra-redis-{port}"),
        "ports": {port: 6379},
        "command": command if command else None,
        "health_check": {"type": "tcp", "port": port},
        "cleanup_on_stop": kwargs.get("cleanup_on_stop", True),
        "restart_policy": kwargs.get("restart_policy", "unless-stopped"),
    }

    if data_dir and enable_persistence:
        config["volumes"] = {str(data_dir): "/data"}

    if scope is not None:
        config["scope"] = scope
    if mode is not None:
        config["mode"] = mode

    config.update({k: v for k, v in kwargs.items() if k not in config})

    return config

