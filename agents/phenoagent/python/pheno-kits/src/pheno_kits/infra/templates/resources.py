"""
Resource Templates - Pre-configured templates for common system resources.

Provides easy-to-use templates that can be customized as needed. All templates
return config dictionaries that can be passed to ResourceFactory.
"""

from typing import Any

from .caching import redis
from .cloud import neon_database, supabase_project, vercel_deployment
from .databases import mongodb, mysql, postgres
from .messaging import nats

__all__ = [
    "api_resource",
    "aws_rds_instance",
    "custom_api",
    "custom_command",
    "custom_docker",
    "kubernetes_deployment",
    "mongodb",
    "mysql",
    "nats",
    "neon_database",
    "postgres",
    "railway_service",
    "redis",
    "render_service",
    "supabase_project",
    "systemd_service",
    "vercel_deployment",
]


def custom_docker(
    image: str,
    port: int | None = None,
    ports: dict[int, int] | None = None,
    environment: dict[str, str] | None = None,
    volumes: dict[str, str] | None = None,
    command: list | None = None,
    health_check_port: int | None = None,
    health_check_type: str = "tcp",
    scope: str | None = None,
    mode: str | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Generic Docker container template."""
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

    if scope is not None:
        config["scope"] = scope
    if mode is not None:
        config["mode"] = mode

    config.update({k: v for k, v in kwargs.items() if k not in config})

    return config


def systemd_service(
    service_name: str,
    health_check_port: int | None = None,
    scope: str | None = None,
    mode: str | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Systemd service template."""
    config: dict[str, Any] = {
        "type": "systemd",
        "service_name": service_name,
        "use_sudo": kwargs.get("use_sudo", True),
    }

    if health_check_port:
        config["health_check"] = {"type": "tcp", "port": health_check_port}

    if scope is not None:
        config["scope"] = scope
    if mode is not None:
        config["mode"] = mode

    config.update({k: v for k, v in kwargs.items() if k not in config})

    return config


def custom_command(
    start_command: list,
    stop_command: list,
    status_command: list | None = None,
    health_check_port: int | None = None,
    scope: str | None = None,
    mode: str | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Custom command-based resource template."""
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

    if scope is not None:
        config["scope"] = scope
    if mode is not None:
        config["mode"] = mode

    config.update({k: v for k, v in kwargs.items() if k not in config})

    return config


def api_resource(
    api_base_url: str,
    auth_type: str = "none",
    auth_token: str | None = None,
    api_key: str | None = None,
    start_endpoint: str = "/start",
    stop_endpoint: str = "/stop",
    health_endpoint: str = "/health",
    scope: str | None = None,
    mode: str | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Generic API-based resource template."""
    config: dict[str, Any] = {
        "type": "api",
        "api_base_url": api_base_url,
        "start_endpoint": start_endpoint,
        "stop_endpoint": stop_endpoint,
        "status_endpoint": kwargs.get("status_endpoint", "/status"),
        "health_endpoint": health_endpoint,
    }

    auth_config: dict[str, Any] = {"type": auth_type}
    if auth_type == "bearer" and auth_token:
        auth_config["token"] = auth_token
    elif auth_type == "api_key" and api_key:
        auth_config["api_key"] = api_key
        auth_config["header_name"] = kwargs.get("api_key_header", "X-API-Key")
    elif auth_type == "basic":
        auth_config["username"] = kwargs.get("username", "")
        auth_config["password"] = kwargs.get("password", "")

    config["auth"] = auth_config

    if scope is not None:
        config["scope"] = scope
    if mode is not None:
        config["mode"] = mode

    config.update({k: v for k, v in kwargs.items() if k not in config})

    return config


def render_service(
    service_id: str,
    api_key: str,
    scope: str | None = None,
    mode: str | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Render.com service template."""
    return api_resource(
        api_base_url=f"https://api.render.com/v1/services/{service_id}",
        auth_type="bearer",
        auth_token=api_key,
        start_endpoint="/resume",
        stop_endpoint="/suspend",
        health_endpoint="",
        status_endpoint="",
        scope=scope,
        mode=mode,
        **kwargs,
    )


def aws_rds_instance(
    instance_id: str,
    region: str = "us-east-1",
    aws_access_key: str | None = None,
    aws_secret_key: str | None = None,
    scope: str | None = None,
    mode: str | None = None,
    **kwargs,
) -> dict[str, Any]:
    """AWS RDS instance template (requires boto3)."""
    config: dict[str, Any] = {
        "type": "api",
        "api_base_url": f"https://rds.{region}.amazonaws.com",
        "start_endpoint": f"/?Action=StartDBInstance&DBInstanceIdentifier={instance_id}",
        "stop_endpoint": f"/?Action=StopDBInstance&DBInstanceIdentifier={instance_id}",
        "status_endpoint": f"/?Action=DescribeDBInstances&DBInstanceIdentifier={instance_id}",
        "auth": {
            "type": "custom",
            "headers": {
                "X-Amz-Access-Key": aws_access_key or "",
                "X-Amz-Secret-Key": aws_secret_key or "",
            },
        },
    }

    if scope is not None:
        config["scope"] = scope
    if mode is not None:
        config["mode"] = mode

    config.update(kwargs)
    return config


def railway_service(
    service_id: str,
    api_key: str,
    scope: str | None = None,
    mode: str | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Railway service template."""
    return api_resource(
        api_base_url="https://backboard.railway.app/graphql/v2",
        auth_type="bearer",
        auth_token=api_key,
        start_endpoint="/",
        start_method="POST",
        start_body={
            "query": "mutation { serviceInstanceRedeploy(serviceId: $serviceId) { id } }",
            "variables": {"serviceId": service_id},
        },
        scope=scope,
        mode=mode,
        **kwargs,
    )


def kubernetes_deployment(
    deployment_name: str,
    namespace: str = "default",
    kubeconfig: str | None = None,
    scope: str | None = None,
    mode: str | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Kubernetes deployment template (via kubectl)."""
    config: dict[str, Any] = {
        "type": "command",
        "start_command": [
            "kubectl",
            "scale",
            "deployment",
            deployment_name,
            "--namespace",
            namespace,
            "--replicas=1",
        ],
        "stop_command": [
            "kubectl",
            "scale",
            "deployment",
            deployment_name,
            "--namespace",
            namespace,
            "--replicas=0",
        ],
        "status_command": [
            "kubectl",
            "get",
            "deployment",
            deployment_name,
            "--namespace",
            namespace,
            "-o",
            "jsonpath={.status.readyReplicas}",
        ],
    }

    if kubeconfig:
        for cmd in ["start_command", "stop_command", "status_command"]:
            config[cmd].extend(["--kubeconfig", kubeconfig])

    if scope is not None:
        config["scope"] = scope
    if mode is not None:
        config["mode"] = mode

    config.update(kwargs)
    return config


def custom_api(
    base_url: str,
    auth_token: str | None = None,
    scope: str | None = None,
    mode: str | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Generic custom API resource."""
    config: dict[str, Any] = {"type": "api", "api_base_url": base_url}

    if auth_token:
        config["auth"] = {"type": "bearer", "token": auth_token}

    if scope is not None:
        config["scope"] = scope
    if mode is not None:
        config["mode"] = mode

    config.update(kwargs)
    return config

