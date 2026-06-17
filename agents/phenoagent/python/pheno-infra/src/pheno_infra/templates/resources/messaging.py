"""
Messaging/streaming resource templates.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


def nats(
    port: int = 4222,
    enable_jetstream: bool = True,
    version: str = "latest",
    data_dir: Path | None = None,
    **kwargs,
) -> dict[str, Any]:
    command = []
    if enable_jetstream:
        command = ["-js"]
        if data_dir:
            command.extend(["-sd", "/data"])
    config: dict[str, Any] = {
        "type": "docker",
        "image": f"nats:{version}",
        "container_name": kwargs.get("container_name", f"kinfra-nats-{port}"),
        "ports": {port: 4222},
        "command": command if command else None,
        "health_check": {"type": "tcp", "port": port},
        "cleanup_on_stop": kwargs.get("cleanup_on_stop", True),
        "restart_policy": kwargs.get("restart_policy", "unless-stopped"),
    }
    if data_dir and enable_jetstream:
        config["volumes"] = {str(data_dir): "/data"}
    config.update({k: v for k, v in kwargs.items() if k not in config})
    return config
