"""
CI/CD system ports (interfaces) following hexagonal architecture.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .core import CICDConfig, CICDPipeline, CICDTemplate, ProjectType


class CICDRepository(ABC):
    """
    Repository port for CI/CD configuration storage.
    """

    @abstractmethod
    def save_config(self, project_path: Path, config: CICDConfig) -> bool:
        """
        Save CI/CD configuration.
        """

    @abstractmethod
    def load_config(self, project_path: Path) -> CICDConfig | None:
        """
        Load CI/CD configuration.
        """

    @abstractmethod
    def save_pipeline(self, project_path: Path, pipeline: CICDPipeline) -> bool:
        """
        Save generated pipeline.
        """

    @abstractmethod
    def load_pipeline(self, project_path: Path) -> CICDPipeline | None:
        """
        Load generated pipeline.
        """

    @abstractmethod
    def list_projects(self) -> list[Path]:
        """
        List all projects with CI/CD configuration.
        """

    @abstractmethod
    def delete_config(self, project_path: Path) -> bool:
        """
        Delete CI/CD configuration.
        """


class CICDConfigProvider(ABC):
    """
    Configuration provider port.
    """

    @abstractmethod
    def get_default_config(self, project_type: ProjectType) -> CICDConfig:
        """
        Get default configuration for project type.
        """

    @abstractmethod
    def get_project_config(self, project_path: Path) -> CICDConfig | None:
        """
        Get project-specific configuration.
        """

    @abstractmethod
    def update_config(self, project_path: Path, config: CICDConfig) -> bool:
        """
        Update project configuration.
        """

    @abstractmethod
    def validate_config(self, config: CICDConfig) -> list[str]:
        """
        Validate configuration and return errors.
        """

    @abstractmethod
    def merge_configs(self, base_config: CICDConfig, override_config: CICDConfig) -> CICDConfig:
        """
        Merge two configurations.
        """


class CICDSyncProvider(ABC):
    """
    Synchronization provider port.
    """

    @abstractmethod
    def sync_pipeline(self, source_path: Path, target_path: Path) -> bool:
        """
        Sync pipeline from source to target.
        """

    @abstractmethod
    def detect_changes(self, source_path: Path, target_path: Path) -> list[str]:
        """
        Detect changes between source and target.
        """

    @abstractmethod
    def backup_pipeline(self, project_path: Path) -> bool:
        """
        Backup current pipeline.
        """

    @abstractmethod
    def restore_pipeline(self, project_path: Path, backup_id: str) -> bool:
        """
        Restore pipeline from backup.
        """

    @abstractmethod
    def get_sync_status(self, project_path: Path) -> dict[str, Any]:
        """
        Get synchronization status.
        """


class CICDTemplateProvider(ABC):
    """
    Template provider port.
    """

    @abstractmethod
    def get_template(self, name: str) -> CICDTemplate | None:
        """
        Get template by name.
        """

    @abstractmethod
    def list_templates(self) -> list[str]:
        """
        List available templates.
        """

    @abstractmethod
    def register_template(self, template: CICDTemplate) -> bool:
        """
        Register a new template.
        """

    @abstractmethod
    def update_template(self, name: str, template: CICDTemplate) -> bool:
        """
        Update existing template.
        """

    @abstractmethod
    def delete_template(self, name: str) -> bool:
        """
        Delete template.
        """


class CICDQualityProvider(ABC):
    """
    Quality integration provider port.
    """

    @abstractmethod
    def integrate_quality_checks(self, pipeline: CICDPipeline) -> CICDPipeline:
        """
        Integrate quality checks into pipeline.
        """

    @abstractmethod
    def get_quality_config(self, project_type: ProjectType) -> dict[str, Any]:
        """
        Get quality configuration for project type.
        """

    @abstractmethod
    def validate_quality_integration(self, pipeline: CICDPipeline) -> list[str]:
        """
        Validate quality integration.
        """

    @abstractmethod
    def update_quality_thresholds(
        self, pipeline: CICDPipeline, thresholds: dict[str, Any],
    ) -> CICDPipeline:
        """
        Update quality thresholds in pipeline.
        """


class CICDNotificationProvider(ABC):
    """
    Notification provider port.
    """

    @abstractmethod
    def send_notification(self, event: str, data: dict[str, Any]) -> bool:
        """
        Send notification.
        """

    @abstractmethod
    def configure_notifications(self, project_path: Path, config: dict[str, Any]) -> bool:
        """
        Configure notifications for project.
        """

    @abstractmethod
    def get_notification_config(self, project_path: Path) -> dict[str, Any] | None:
        """
        Get notification configuration.
        """


class CICDArtifactProvider(ABC):
    """
    Artifact management provider port.
    """

    @abstractmethod
    def store_artifact(
        self, project_path: Path, artifact_path: Path, metadata: dict[str, Any],
    ) -> str:
        """
        Store artifact and return ID.
        """

    @abstractmethod
    def retrieve_artifact(self, artifact_id: str) -> Path | None:
        """
        Retrieve artifact by ID.
        """

    @abstractmethod
    def list_artifacts(self, project_path: Path) -> list[dict[str, Any]]:
        """
        List artifacts for project.
        """

    @abstractmethod
    def delete_artifact(self, artifact_id: str) -> bool:
        """
        Delete artifact.
        """


class CICDDeploymentProvider(ABC):
    """
    Deployment provider port.
    """

    @abstractmethod
    def deploy(self, project_path: Path, environment: str, config: dict[str, Any]) -> bool:
        """
        Deploy project to environment.
        """

    @abstractmethod
    def rollback(self, project_path: Path, environment: str, version: str) -> bool:
        """
        Rollback deployment.
        """

    @abstractmethod
    def get_deployment_status(self, project_path: Path, environment: str) -> dict[str, Any]:
        """
        Get deployment status.
        """

    @abstractmethod
    def list_environments(self, project_path: Path) -> list[str]:
        """
        List available environments.
        """
