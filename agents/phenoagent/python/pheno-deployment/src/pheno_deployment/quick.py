from __future__ import annotations

import contextlib
from pathlib import Path

from .base import DeploymentConfig, DeploymentEnvironment, DeploymentResult
from .platforms import HTTPHealthCheckProvider, VercelDeploymentProvider


def _to_env(environment: str | DeploymentEnvironment) -> DeploymentEnvironment:
    if isinstance(environment, DeploymentEnvironment):
        return environment
    env = str(environment).lower().strip()
    if env == "preview":
        return DeploymentEnvironment.PREVIEW
    if env == "production":
        return DeploymentEnvironment.PRODUCTION
    if env == "staging":
        return DeploymentEnvironment.STAGING
    if env == "local":
        return DeploymentEnvironment.LOCAL
    raise ValueError(f"Invalid environment: {environment}")


def deploy_vercel(
    environment: str | DeploymentEnvironment,
    project_root: Path | None = None,
    domain: str | None = None,
    env_file: Path | None = None,
    build_command: str = "bash build.sh",
    install_command: str = "pip install --upgrade pip && pip install -r requirements.txt",
    health_path: str = "/health",
    retries: int = 5,
    delay: int = 2,
    timeout: int = 10,
    logger=None,
) -> DeploymentResult:
    """One-call deploy to Vercel with optional health check.

    Returns a DeploymentResult. On success, attaches simple health metadata if a URL is
    available.
    """
    env = _to_env(environment)
    cfg = DeploymentConfig(
        environment=env,
        project_root=project_root or Path.cwd(),
        env_file=env_file,
        domain=domain,
        build_command=build_command,
        install_command=install_command,
    )

    res = VercelDeploymentProvider(config=cfg, logger=logger).deploy()
    if not getattr(res, "success", False):
        return res

    url = getattr(res, "url", None) or (f"https://{cfg.domain}" if cfg.domain else None)
    if url:
        health_url = f"{url.rstrip('/')}{health_path}"
        ok = HTTPHealthCheckProvider(logger=logger).check_with_retries(
            url=health_url, max_retries=retries, retry_delay=delay, timeout=timeout,
        )
        md = getattr(res, "metadata", None) or {}
        md.update({"health_ok": ok, "health_url": health_url})
        with contextlib.suppress(Exception):
            res.metadata = md

    return res


def rollback(
    deployment_id: str,
    environment: str | DeploymentEnvironment,
    project_root: Path | None = None,
    logger=None,
):
    cfg = DeploymentConfig(
        environment=_to_env(environment), project_root=project_root or Path.cwd(),
    )
    return VercelDeploymentProvider(config=cfg, logger=logger).rollback(deployment_id)


def get_deployments(
    limit: int = 10,
    environment: str | DeploymentEnvironment = "preview",
    project_root: Path | None = None,
    logger=None,
):
    cfg = DeploymentConfig(
        environment=_to_env(environment), project_root=project_root or Path.cwd(),
    )
    return VercelDeploymentProvider(config=cfg, logger=logger).get_deployments(limit=limit)
