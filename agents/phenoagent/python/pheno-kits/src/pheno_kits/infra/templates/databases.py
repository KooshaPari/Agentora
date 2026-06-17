"""Database resource templates."""

from pathlib import Path
from typing import Any


def postgres(
    port: int = 5432,
    password: str = "postgres",
    database: str = "postgres",
    user: str = "postgres",
    version: str = "16-alpine",
    data_dir: Path | None = None,
    scope: str | None = None,
    mode: str | None = None,
    **kwargs,
) -> dict[str, Any]:
    """PostgreSQL template."""
    config = {
        "type": "docker",
        "image": f"postgres:{version}",
        "container_name": kwargs.get("container_name", f"kinfra-postgres-{port}"),
        "ports": {port: 5432},
        "environment": {
            "POSTGRES_PASSWORD": password,
            "POSTGRES_DB": database,
            "POSTGRES_USER": user,
        },
        "health_check": {"type": "tcp", "port": port},
        "cleanup_on_stop": kwargs.get("cleanup_on_stop", True),
        "restart_policy": kwargs.get("restart_policy", "unless-stopped"),
    }

    if data_dir:
        config["volumes"] = {str(data_dir): "/var/lib/postgresql/data"}

    if scope is not None:
        config["scope"] = scope
    if mode is not None:
        config["mode"] = mode

    config.update({k: v for k, v in kwargs.items() if k not in config})

    return config


def mongodb(
    port: int = 27017,
    version: str = "7",
    data_dir: Path | None = None,
    scope: str | None = None,
    mode: str | None = None,
    **kwargs,
) -> dict[str, Any]:
    """MongoDB template."""
    config = {
        "type": "docker",
        "image": f"mongo:{version}",
        "container_name": kwargs.get("container_name", f"kinfra-mongodb-{port}"),
        "ports": {port: 27017},
        "health_check": {"type": "tcp", "port": port},
        "cleanup_on_stop": kwargs.get("cleanup_on_stop", True),
        "restart_policy": kwargs.get("restart_policy", "unless-stopped"),
    }

    if data_dir:
        config["volumes"] = {str(data_dir): "/data/db"}

    if scope is not None:
        config["scope"] = scope
    if mode is not None:
        config["mode"] = mode

    config.update({k: v for k, v in kwargs.items() if k not in config})

    return config


def mysql(
    port: int = 3306,
    password: str = "mysql",
    database: str = "mysql",
    version: str = "8",
    data_dir: Path | None = None,
    scope: str | None = None,
    mode: str | None = None,
    **kwargs,
) -> dict[str, Any]:
    """MySQL template."""
    config = {
        "type": "docker",
        "image": f"mysql:{version}",
        "container_name": kwargs.get("container_name", f"kinfra-mysql-{port}"),
        "ports": {port: 3306},
        "environment": {"MYSQL_ROOT_PASSWORD": password, "MYSQL_DATABASE": database},
        "health_check": {"type": "tcp", "port": port},
        "cleanup_on_stop": kwargs.get("cleanup_on_stop", True),
        "restart_policy": kwargs.get("restart_policy", "unless-stopped"),
    }

    if data_dir:
        config["volumes"] = {str(data_dir): "/var/lib/mysql"}

    if scope is not None:
        config["scope"] = scope
    if mode is not None:
        config["mode"] = mode

    config.update({k: v for k, v in kwargs.items() if k not in config})

    return config

