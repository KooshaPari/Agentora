"""
Generic local resource templates: docker, systemd, and custom commands.
"""

from __future__ import annotations

from typing import Any


def custom_docker(
    image: str,
    port: int | None = None,
    ports: dict[int, int] | None = None,
    environment: dict[str, str] | None = None,
    volumes: dict[str, str] | None = None,
    command: list | None = None,
    health_check_port: int | None = None,
    health_check_type: str = "tcp",
    **kwargs,
) -> dict[str, Any]:
    config: dict[str, Any] = {
        "type": "docker",
        "image": image,
        "health_check": {},
        "cleanup_on_stop": kwargs.get("cleanup_on_stop", True),
        "restart_policy": kwargs.get("restart_policy", "unless-stopped"),
    }
    if ports:
        config["ports"] = ports
    elif port:
        config["ports"] = {port: port}
    if environment:
        config["environment"] = environment
    if volumes:
        config["volumes"] = volumes
    if command:
        config["command"] = command
    if health_check_port:
        config["health_check"] = {"type": health_check_type, "port": health_check_port}
        if "health_check_path" in kwargs:
            config["health_check"]["path"] = kwargs.pop("health_check_path")
    config.update({k: v for k, v in kwargs.items() if k not in config})
    return config


def systemd_service(
    service_name: str, health_check_port: int | None = None, **kwargs,
) -> dict[str, Any]:
    config: dict[str, Any] = {
        "type": "systemd",
        "service_name": service_name,
        "use_sudo": kwargs.get("use_sudo", True),
    }
    if health_check_port:
        config["health_check"] = {"type": "tcp", "port": health_check_port}
    config.update({k: v for k, v in kwargs.items() if k not in config})
    return config


def custom_command(
    start_command: list,
    stop_command: list,
    status_command: list | None = None,
    health_check_port: int | None = None,
    **kwargs,
) -> dict[str, Any]:
    config: dict[str, Any] = {
        "type": "command",
        "start_command": start_command,
        "stop_command": stop_command,
        "run_in_background": kwargs.get("run_in_background", True),
    }
    if status_command:
        config["status_command"] = status_command
    if health_check_port:
        config["health_check"] = {"type": "tcp", "port": health_check_port}
    config.update({k: v for k, v in kwargs.items() if k not in config})
    return config
