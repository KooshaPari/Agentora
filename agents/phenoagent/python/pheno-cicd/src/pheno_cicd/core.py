"""
Core CI/CD generation classes and domain models.
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class ProjectType(Enum):
    """
    Project type enumeration.
    """

    PHENO_SDK = "pheno-sdk"
    ZEN_MCP_SERVER = "zen-mcp-server"
    ATOMS_MCP_OLD = "atoms_mcp-old"
    MORPH = "morph"
    ROUTER = "router"
    EXAMPLE = "example"


class PipelineStage(Enum):
    """
    Pipeline stage enumeration.
    """

    LINT = "lint"
    TEST = "test"
    BUILD = "build"
    SECURITY = "security"
    QUALITY = "quality"
    DEPLOY = "deploy"
    RELEASE = "release"
    CLEANUP = "cleanup"


class CICDEvent(Enum):
    """
    CI/CD event enumeration.
    """

    PUSH = "push"
    PULL_REQUEST = "pull_request"
    RELEASE = "release"
    SCHEDULE = "schedule"
    WORKFLOW_DISPATCH = "workflow_dispatch"


@dataclass
class CICDConfig:
    """
    CI/CD configuration for a project.
    """

    project_name: str
    project_type: ProjectType
    python_versions: list[str] = field(default_factory=lambda: ["3.11", "3.12"])
    os_versions: list[str] = field(default_factory=lambda: ["ubuntu-latest"])
    quality_thresholds: dict[str, Any] = field(default_factory=dict)
    security_checks: list[str] = field(default_factory=lambda: ["bandit", "safety"])
    test_commands: list[str] = field(default_factory=list)
    build_commands: list[str] = field(default_factory=list)
    deploy_commands: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    environment_variables: dict[str, str] = field(default_factory=dict)
    secrets: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    notifications: dict[str, Any] = field(default_factory=dict)
    custom_stages: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary.
        """
        return {
            "project_name": self.project_name,
            "project_type": self.project_type.value,
            "python_versions": self.python_versions,
            "os_versions": self.os_versions,
            "quality_thresholds": self.quality_thresholds,
            "security_checks": self.security_checks,
            "test_commands": self.test_commands,
            "build_commands": self.build_commands,
            "deploy_commands": self.deploy_commands,
            "dependencies": self.dependencies,
            "environment_variables": self.environment_variables,
            "secrets": self.secrets,
            "artifacts": self.artifacts,
            "notifications": self.notifications,
            "custom_stages": self.custom_stages,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CICDConfig":
        """
        Create from dictionary.
        """
        return cls(
            project_name=data["project_name"],
            project_type=ProjectType(data["project_type"]),
            python_versions=data.get("python_versions", ["3.11", "3.12"]),
            os_versions=data.get("os_versions", ["ubuntu-latest"]),
            quality_thresholds=data.get("quality_thresholds", {}),
            security_checks=data.get("security_checks", ["bandit", "safety"]),
            test_commands=data.get("test_commands", []),
            build_commands=data.get("build_commands", []),
            deploy_commands=data.get("deploy_commands", []),
            dependencies=data.get("dependencies", []),
            environment_variables=data.get("environment_variables", {}),
            secrets=data.get("secrets", []),
            artifacts=data.get("artifacts", []),
            notifications=data.get("notifications", {}),
            custom_stages=data.get("custom_stages", []),
        )


@dataclass
class CICDTemplate:
    """
    CI/CD template definition.
    """

    name: str
    description: str
    project_types: list[ProjectType]
    stages: list[PipelineStage]
    template_content: str
    variables: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary.
        """
        return {
            "name": self.name,
            "description": self.description,
            "project_types": [pt.value for pt in self.project_types],
            "stages": [stage.value for stage in self.stages],
            "template_content": self.template_content,
            "variables": self.variables,
            "dependencies": self.dependencies,
            "version": self.version,
        }


@dataclass
class CICDPipeline:
    """
    Generated CI/CD pipeline.
    """

    name: str
    project_path: Path
    config: CICDConfig
    files: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.now)

    def add_file(self, file_path: str, content: str) -> None:
        """
        Add a file to the pipeline.
        """
        self.files[file_path] = content

    def get_file(self, file_path: str) -> str | None:
        """
        Get file content.
        """
        return self.files.get(file_path)

    def list_files(self) -> list[str]:
        """
        List all files in the pipeline.
        """
        return list(self.files.keys())

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary.
        """
        return {
            "name": self.name,
            "project_path": str(self.project_path),
            "config": self.config.to_dict(),
            "files": self.files,
            "metadata": self.metadata,
            "generated_at": self.generated_at.isoformat(),
        }


class CICDGenerator(ABC):
    """
    Abstract base class for CI/CD generators.
    """

    def __init__(self, config: CICDConfig):
        self.config = config
        self.templates: dict[str, CICDTemplate] = {}
        self.generated_pipelines: list[CICDPipeline] = []

    @abstractmethod
    def generate_pipeline(self, project_path: Path) -> CICDPipeline:
        """
        Generate a complete CI/CD pipeline.
        """

    @abstractmethod
    def generate_workflow(self, stage: PipelineStage) -> str:
        """
        Generate a specific workflow file.
        """

    @abstractmethod
    def generate_dockerfile(self) -> str:
        """
        Generate Dockerfile.
        """

    @abstractmethod
    def generate_docker_compose(self) -> str:
        """
        Generate docker-compose.yml.
        """

    @abstractmethod
    def generate_makefile(self) -> str:
        """
        Generate Makefile.
        """

    def register_template(self, template: CICDTemplate) -> None:
        """
        Register a template.
        """
        self.templates[template.name] = template

    def get_template(self, name: str) -> CICDTemplate | None:
        """
        Get a template by name.
        """
        return self.templates.get(name)

    def list_templates(self) -> list[str]:
        """
        List available templates.
        """
        return list(self.templates.keys())

    def validate_config(self) -> list[str]:
        """
        Validate configuration and return errors.
        """
        errors = []

        if not self.config.project_name:
            errors.append("Project name is required")

        if not self.config.python_versions:
            errors.append("At least one Python version is required")

        if not self.config.os_versions:
            errors.append("At least one OS version is required")

        return errors

    def generate_all(self, project_path: Path) -> CICDPipeline:
        """
        Generate complete CI/CD pipeline.
        """
        errors = self.validate_config()
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")

        pipeline = self.generate_pipeline(project_path)

        # Generate all workflow files
        for stage in PipelineStage:
            if self._should_generate_stage(stage):
                workflow_content = self.generate_workflow(stage)
                pipeline.add_file(f".github/workflows/{stage.value}.yml", workflow_content)

        # Generate supporting files
        pipeline.add_file("Dockerfile", self.generate_dockerfile())
        pipeline.add_file("docker-compose.yml", self.generate_docker_compose())
        pipeline.add_file("Makefile", self.generate_makefile())

        # Generate configuration files
        pipeline.add_file(".github/cicd-config.json", json.dumps(self.config.to_dict(), indent=2))

        self.generated_pipelines.append(pipeline)
        return pipeline

    def _should_generate_stage(self, stage: PipelineStage) -> bool:
        """
        Determine if a stage should be generated.
        """
        # Default implementation - can be overridden
        return True

    def get_generated_pipelines(self) -> list[CICDPipeline]:
        """
        Get all generated pipelines.
        """
        return self.generated_pipelines.copy()

    def clear_generated_pipelines(self) -> None:
        """
        Clear generated pipelines.
        """
        self.generated_pipelines.clear()
