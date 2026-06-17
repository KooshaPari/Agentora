"""
Cloud/API resource templates (SDK or CLI-backed).
"""

from __future__ import annotations

from typing import Any


def api_resource(
    api_base_url: str,
    auth_type: str = "none",
    auth_token: str | None = None,
    api_key: str | None = None,
    start_endpoint: str = "/start",
    stop_endpoint: str = "/stop",
    health_endpoint: str = "/health",
    **kwargs,
) -> dict[str, Any]:
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
    config.update({k: v for k, v in kwargs.items() if k not in config})
    return config


def supabase_project(
    project_id: str,
    access_token: str | None = None,
    database_password: str | None = None,
    use_sdk: bool = True,
    **kwargs,
) -> dict[str, Any]:
    config: dict[str, Any] = {"type": "supabase", "project_id": project_id, "use_sdk": use_sdk}
    if access_token:
        config["access_token"] = access_token
    if database_password:
        config["database_password"] = database_password
    config.update(kwargs)
    return config


def render_service(service_id: str, api_key: str, **kwargs) -> dict[str, Any]:
    return api_resource(
        api_base_url=f"https://api.render.com/v1/services/{service_id}",
        auth_type="bearer",
        auth_token=api_key,
        start_endpoint="/resume",
        stop_endpoint="/suspend",
        health_endpoint="",
        status_endpoint="",
        **kwargs,
    )


def aws_rds_instance(
    instance_id: str,
    region: str = "us-east-1",
    aws_access_key: str | None = None,
    aws_secret_key: str | None = None,
    **kwargs,
) -> dict[str, Any]:
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
    config.update(kwargs)
    return config


def vercel_deployment(
    project_name: str | None = None,
    deployment_id: str | None = None,
    team_id: str | None = None,
    access_token: str | None = None,
    target: str = "production",
    use_sdk: bool = True,
    **kwargs,
) -> dict[str, Any]:
    config: dict[str, Any] = {"type": "vercel", "target": target, "use_sdk": use_sdk}
    if project_name:
        config["project_name"] = project_name
    if deployment_id:
        config["deployment_id"] = deployment_id
    if team_id:
        config["team_id"] = team_id
    if access_token:
        config["access_token"] = access_token
    config.update(kwargs)
    return config


def neon_database(
    project_id: str,
    api_key: str | None = None,
    branch_name: str = "main",
    region: str | None = None,
    use_sdk: bool = True,
    **kwargs,
) -> dict[str, Any]:
    config: dict[str, Any] = {
        "type": "neon",
        "project_id": project_id,
        "branch_name": branch_name,
        "use_sdk": use_sdk,
    }
    if api_key:
        config["api_key"] = api_key
    if region:
        config["region"] = region
    config.update(kwargs)
    return config


def railway_service(service_id: str, api_key: str, **kwargs) -> dict[str, Any]:
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
        **kwargs,
    )


def kubernetes_deployment(
    deployment_name: str, namespace: str = "default", kubeconfig: str | None = None, **kwargs,
) -> dict[str, Any]:
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
    config.update(kwargs)
    return config


def custom_api(base_url: str, auth_token: str | None = None, **kwargs) -> dict[str, Any]:
    config: dict[str, Any] = {"type": "api", "api_base_url": base_url}
    if auth_token:
        config["auth"] = {"type": "bearer", "token": auth_token}
    config.update(kwargs)
    return config
