"""
Factory helpers for deployment pipelines.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .pipelines.docker import DockerDeployment
from .pipelines.npm import NPMDeployment
from .pipelines.pypi import PyPIDeployment
from .pipelines.system_service import SystemServiceDeployment

if TYPE_CHECKING:
    from pathlib import Path

    from .base import BaseDeployment


def create_deployment(
    deployment_type: str, project_path: Path, config: dict[str, Any],
) -> BaseDeployment:
    """Factory function to create deployment pipelines.

    Args:
        deployment_type: Key identifying the deployment pipeline ('pypi',
            'npm', 'docker', or 'system-service').
        project_path: Path to the project root.
        config: Deployment configuration dictionary forwarded to the pipeline.

    Returns:
        Instance of :class:`BaseDeployment` subclass.
    """
    deployments = {
        "pypi": PyPIDeployment,
        "npm": NPMDeployment,
        "docker": DockerDeployment,
        "system-service": SystemServiceDeployment,
    }

    if deployment_type not in deployments:
        raise ValueError(f"Unknown deployment type: {deployment_type}")

    return deployments[deployment_type](project_path, config)


__all__ = ["create_deployment"]
