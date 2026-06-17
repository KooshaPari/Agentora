"""Messaging resource templates."""

from pathlib import Path
from typing import Any


def nats(
    port: int = 4222,
    enable_jetstream: bool = True,
    version: str = "latest",
    data_dir: Path | None = None,
    scope: str | None = None,
    mode: str | None = None,
    **kwargs,
) -> dict[str, Any]:
    """NATS template."""
    command = []
    if enable_jetstream:
        command = ["-js"]
        if data_dir:
            command.extend(["-sd", "/data"])

    config = {
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

    if scope is not None:
        config["scope"] = scope
    if mode is not None:
        config["mode"] = mode

    config.update({k: v for k, v in kwargs.items() if k not in config})

    return config

