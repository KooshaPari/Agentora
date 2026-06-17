"""Cloud resource templates."""

from typing import Any


def supabase_project(
    project_id: str,
    access_token: str | None = None,
    database_password: str | None = None,
    use_sdk: bool = True,
    scope: str | None = None,
    mode: str | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Supabase project template with native SDK support."""
    config = {"type": "supabase", "project_id": project_id, "use_sdk": use_sdk}

    if access_token:
        config["access_token"] = access_token
    if database_password:
        config["database_password"] = database_password
    if scope is not None:
        config["scope"] = scope
    if mode is not None:
        config["mode"] = mode

    config.update(kwargs)
    return config


def vercel_deployment(
    project_name: str | None = None,
    deployment_id: str | None = None,
    team_id: str | None = None,
    access_token: str | None = None,
    target: str = "production",
    use_sdk: bool = True,
    scope: str | None = None,
    mode: str | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Vercel deployment template with native SDK support."""
    config = {"type": "vercel", "target": target, "use_sdk": use_sdk}

    if project_name:
        config["project_name"] = project_name
    if deployment_id:
        config["deployment_id"] = deployment_id
    if team_id:
        config["team_id"] = team_id
    if access_token:
        config["access_token"] = access_token
    if scope is not None:
        config["scope"] = scope
    if mode is not None:
        config["mode"] = mode

    config.update(kwargs)
    return config


def neon_database(
    project_id: str,
    api_key: str | None = None,
    branch_name: str = "main",
    region: str | None = None,
    use_sdk: bool = True,
    scope: str | None = None,
    mode: str | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Neon serverless Postgres template with native SDK support."""
    config = {
        "type": "neon",
        "project_id": project_id,
        "branch_name": branch_name,
        "use_sdk": use_sdk,
    }

    if api_key:
        config["api_key"] = api_key
    if region:
        config["region"] = region
    if scope is not None:
        config["scope"] = scope
    if mode is not None:
        config["mode"] = mode

    config.update(kwargs)
    return config

