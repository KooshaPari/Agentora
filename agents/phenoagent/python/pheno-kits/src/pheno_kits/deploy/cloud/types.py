"""
Deployment types for cloud platforms.
"""

from enum import Enum
from pathlib import Path
from typing import Any


class DeploymentStatus(Enum):
    """
    Deployment status enumeration.
    """

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DeploymentConfig:
    """
    Configuration for cloud deployments.
    """

    def __init__(
        self,
        environment: str,
        project_root: Path,
        env_file: Path | None = None,
        domain: str | None = None,
        build_command: str | None = None,
        install_command: str | None = None,
        **kwargs,
    ):
        self.environment = environment
        self.project_root = project_root
        self.env_file = env_file
        self.domain = domain
        self.build_command = build_command
        self.install_command = install_command
        self.extra_config = kwargs

    def to_dict(self) -> dict[str, Any]:
        """
        Convert config to dictionary.
        """
        return {
            "environment": self.environment,
            "project_root": str(self.project_root),
            "env_file": str(self.env_file) if self.env_file else None,
            "domain": self.domain,
            "build_command": self.build_command,
            "install_command": self.install_command,
            **self.extra_config,
        }
