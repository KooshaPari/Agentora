"""
Deployment orchestrator abstraction.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types import ProjectConfig, ProjectDeployment, ProjectStatus


class DeploymentOrchestrator(ABC):
    """
    High-level orchestrator responsible for multi-provider deployments.
    """

    @abstractmethod
    async def deploy_project(self, config: ProjectConfig) -> ProjectDeployment: ...

    @abstractmethod
    async def update_project(self, project_id: str, config: ProjectConfig) -> ProjectDeployment: ...

    @abstractmethod
    async def get_project_status(self, project_id: str) -> ProjectStatus: ...

    @abstractmethod
    async def delete_project(self, project_id: str) -> None: ...

    @abstractmethod
    async def rollback_project(self, project_id: str) -> None: ...


__all__ = ["DeploymentOrchestrator"]
