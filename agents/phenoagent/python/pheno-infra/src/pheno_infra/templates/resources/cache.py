"""
Cache resource templates.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


def redis(
    port: int = 6379,
    enable_persistence: bool = True,
    version: str = "7-alpine",
    data_dir: Path | None = None,
    **kwargs,
) -> dict[str, Any]:
    command = ["redis-server", "--appendonly", "yes"] if enable_persistence else []
    config: dict[str, Any] = {
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
    config.update({k: v for k, v in kwargs.items() if k not in config})
    return config
