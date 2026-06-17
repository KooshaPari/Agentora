"""
CI/CD system adapters implementing the ports.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from .core import CICDConfig, CICDPipeline, CICDTemplate, ProjectType
from .ports import (
    CICDConfigProvider,
    CICDRepository,
    CICDSyncProvider,
    CICDTemplateProvider,
)


class FileSystemRepository(CICDRepository):
    """
    File system implementation of CI/CD repository.
    """

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.config_file = "cicd-config.json"
        self.pipeline_file = "cicd-pipeline.json"

    def save_config(self, project_path: Path, config: CICDConfig) -> bool:
        """
        Save CI/CD configuration.
        """
        try:
            config_path = project_path / self.config_file
            with open(config_path, "w") as f:
                json.dump(config.to_dict(), f, indent=2)
            return True
        except Exception:
            return False

    def load_config(self, project_path: Path) -> CICDConfig | None:
        """
        Load CI/CD configuration.
        """
        try:
            config_path = project_path / self.config_file
            if not config_path.exists():
                return None

            with open(config_path) as f:
                data = json.load(f)
            return CICDConfig.from_dict(data)
        except Exception:
            return None

    def save_pipeline(self, project_path: Path, pipeline: CICDPipeline) -> bool:
        """
        Save generated pipeline.
        """
        try:
            pipeline_path = project_path / self.pipeline_file
            with open(pipeline_path, "w") as f:
                json.dump(pipeline.to_dict(), f, indent=2)

            # Save individual files
            for file_path, content in pipeline.files.items():
                full_path = project_path / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                with open(full_path, "w") as f:
                    f.write(content)

            return True
        except Exception:
            return False

    def load_pipeline(self, project_path: Path) -> CICDPipeline | None:
        """
        Load generated pipeline.
        """
        try:
            pipeline_path = project_path / self.pipeline_file
            if not pipeline_path.exists():
                return None

            with open(pipeline_path) as f:
                data = json.load(f)

            # Reconstruct pipeline
            pipeline = CICDPipeline(
                name=data["name"],
                project_path=Path(data["project_path"]),
                config=CICDConfig.from_dict(data["config"]),
                metadata=data.get("metadata", {}),
                generated_at=datetime.fromisoformat(data["generated_at"]),
            )

            # Load files
            for file_path, content in data.get("files", {}).items():
                pipeline.add_file(file_path, content)

            return pipeline
        except Exception:
            return None

    def list_projects(self) -> list[Path]:
        """
        List all projects with CI/CD configuration.
        """
        projects = []
        for config_file in self.base_path.rglob(self.config_file):
            projects.append(config_file.parent)
        return projects

    def delete_config(self, project_path: Path) -> bool:
        """
        Delete CI/CD configuration.
        """
        try:
            config_path = project_path / self.config_file
            pipeline_path = project_path / self.pipeline_file

            if config_path.exists():
                config_path.unlink()
            if pipeline_path.exists():
                pipeline_path.unlink()

            return True
        except Exception:
            return False


class DefaultConfigProvider(CICDConfigProvider):
    """
    Default configuration provider.
    """

    def __init__(self):
        self.default_configs = self._load_default_configs()

    def _load_default_configs(self) -> dict[ProjectType, CICDConfig]:
        """
        Load default configurations for each project type.
        """
        configs = {}

        # Pheno-SDK configuration
        configs[ProjectType.PHENO_SDK] = CICDConfig(
            project_name="pheno-sdk",
            project_type=ProjectType.PHENO_SDK,
            python_versions=["3.11", "3.12", "3.13"],
            os_versions=["ubuntu-latest", "macos-latest", "windows-latest"],
            quality_thresholds={
                "coverage_threshold": 65.0,
                "loc_threshold": 70000,
                "complexity_threshold": 10,
            },
            security_checks=["bandit", "safety", "semgrep"],
            test_commands=["pytest", "pytest-cov"],
            build_commands=["python -m build"],
            deploy_commands=["make deploy"],
            dependencies=["pheno-sdk[quality,test]"],
            environment_variables={"PYTHON_VERSION": "3.12", "CACHE_VERSION": "v1"},
            secrets=["PYPI_TOKEN", "GITHUB_TOKEN"],
            artifacts=["dist/", "coverage.xml", "test-results.xml"],
        )

        # Zen-MCP-Server configuration
        configs[ProjectType.ZEN_MCP_SERVER] = CICDConfig(
            project_name="zen-mcp-server",
            project_type=ProjectType.ZEN_MCP_SERVER,
            python_versions=["3.10", "3.11", "3.12"],
            os_versions=["ubuntu-latest"],
            quality_thresholds={
                "coverage_threshold": 75.0,
                "loc_threshold": 50000,
                "complexity_threshold": 15,
            },
            security_checks=["bandit", "safety"],
            test_commands=["pytest", "pytest-cov"],
            build_commands=["python -m build"],
            deploy_commands=["docker build", "docker push"],
            dependencies=["../pheno-sdk"],
            environment_variables={"PYTHON_VERSION": "3.10", "CACHE_VERSION": "v1"},
            secrets=["DOCKER_TOKEN", "PYPI_TOKEN"],
            artifacts=["dist/", "coverage.xml", "*.whl"],
        )

        # Atoms-MCP-Old configuration
        configs[ProjectType.ATOMS_MCP_OLD] = CICDConfig(
            project_name="atoms_mcp-old",
            project_type=ProjectType.ATOMS_MCP_OLD,
            python_versions=["3.11", "3.12", "3.13"],
            os_versions=["ubuntu-latest", "macos-latest", "windows-latest"],
            quality_thresholds={
                "coverage_threshold": 70.0,
                "loc_threshold": 8500,
                "complexity_threshold": 20,
            },
            security_checks=["bandit", "safety"],
            test_commands=["pytest", "pytest-cov"],
            build_commands=["python -m build"],
            deploy_commands=["make deploy"],
            dependencies=["../pheno-sdk"],
            environment_variables={"PYTHON_VERSION": "3.11", "CACHE_VERSION": "v1"},
            secrets=["PYPI_TOKEN", "GITHUB_TOKEN"],
            artifacts=["dist/", "coverage.xml", "test-results.xml"],
        )

        return configs

    def get_default_config(self, project_type: ProjectType) -> CICDConfig:
        """
        Get default configuration for project type.
        """
        return self.default_configs.get(
            project_type, CICDConfig(project_name="unknown", project_type=project_type),
        )

    def get_project_config(self, project_path: Path) -> CICDConfig | None:
        """
        Get project-specific configuration.
        """
        config_file = project_path / "cicd-config.json"
        if not config_file.exists():
            return None

        try:
            with open(config_file) as f:
                data = json.load(f)
            return CICDConfig.from_dict(data)
        except Exception:
            return None

    def update_config(self, project_path: Path, config: CICDConfig) -> bool:
        """
        Update project configuration.
        """
        try:
            config_file = project_path / "cicd-config.json"
            with open(config_file, "w") as f:
                json.dump(config.to_dict(), f, indent=2)
            return True
        except Exception:
            return False

    def validate_config(self, config: CICDConfig) -> list[str]:
        """
        Validate configuration and return errors.
        """
        errors = []

        if not config.project_name:
            errors.append("Project name is required")

        if not config.python_versions:
            errors.append("At least one Python version is required")

        if not config.os_versions:
            errors.append("At least one OS version is required")

        if config.quality_thresholds:
            for key, value in config.quality_thresholds.items():
                if not isinstance(value, (int, float)):
                    errors.append(f"Quality threshold '{key}' must be numeric")

        return errors

    def merge_configs(self, base_config: CICDConfig, override_config: CICDConfig) -> CICDConfig:
        """
        Merge two configurations.
        """
        return CICDConfig(
            project_name=override_config.project_name or base_config.project_name,
            project_type=override_config.project_type or base_config.project_type,
            python_versions=override_config.python_versions or base_config.python_versions,
            os_versions=override_config.os_versions or base_config.os_versions,
            quality_thresholds={
                **base_config.quality_thresholds,
                **override_config.quality_thresholds,
            },
            security_checks=list(
                set(base_config.security_checks + override_config.security_checks),
            ),
            test_commands=override_config.test_commands or base_config.test_commands,
            build_commands=override_config.build_commands or base_config.build_commands,
            deploy_commands=override_config.deploy_commands or base_config.deploy_commands,
            dependencies=list(set(base_config.dependencies + override_config.dependencies)),
            environment_variables={
                **base_config.environment_variables,
                **override_config.environment_variables,
            },
            secrets=list(set(base_config.secrets + override_config.secrets)),
            artifacts=list(set(base_config.artifacts + override_config.artifacts)),
            notifications={**base_config.notifications, **override_config.notifications},
            custom_stages=list(set(base_config.custom_stages + override_config.custom_stages)),
        )



class FileSystemSyncProvider(CICDSyncProvider):
    """
    File system implementation of sync provider.
    """

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.backup_dir = base_path / ".cicd-backups"
        self.backup_dir.mkdir(exist_ok=True)

    def sync_pipeline(self, source_path: Path, target_path: Path) -> bool:
        """
        Sync pipeline from source to target.
        """
        try:
            # Copy CI/CD files
            cicd_files = [
                ".github/workflows/",
                "Dockerfile",
                "docker-compose.yml",
                "Makefile",
                "cicd-config.json",
            ]

            for file_pattern in cicd_files:
                source_file = source_path / file_pattern
                target_file = target_path / file_pattern

                if source_file.exists():
                    if source_file.is_dir():
                        shutil.copytree(source_file, target_file, dirs_exist_ok=True)
                    else:
                        target_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source_file, target_file)

            return True
        except Exception:
            return False

    def detect_changes(self, source_path: Path, target_path: Path) -> list[str]:
        """
        Detect changes between source and target.
        """
        changes = []

        # Check CI/CD specific files
        cicd_files = [
            ".github/workflows/",
            "Dockerfile",
            "docker-compose.yml",
            "Makefile",
            "cicd-config.json",
        ]

        for file_pattern in cicd_files:
            source_file = source_path / file_pattern
            target_file = target_path / file_pattern

            if source_file.exists() and target_file.exists():
                if self._files_differ(source_file, target_file):
                    changes.append(f"Modified: {file_pattern}")
            elif source_file.exists() and not target_file.exists():
                changes.append(f"Added: {file_pattern}")
            elif not source_file.exists() and target_file.exists():
                changes.append(f"Removed: {file_pattern}")

        return changes

    def backup_pipeline(self, project_path: Path) -> bool:
        """
        Backup current pipeline.
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"{project_path.name}_{timestamp}"

            # Copy CI/CD files
            cicd_files = [
                ".github/workflows/",
                "Dockerfile",
                "docker-compose.yml",
                "Makefile",
                "cicd-config.json",
            ]

            for file_pattern in cicd_files:
                source_file = project_path / file_pattern
                if source_file.exists():
                    target_file = backup_path / file_pattern
                    target_file.parent.mkdir(parents=True, exist_ok=True)

                    if source_file.is_dir():
                        shutil.copytree(source_file, target_file)
                    else:
                        shutil.copy2(source_file, target_file)

            return True
        except Exception:
            return False

    def restore_pipeline(self, project_path: Path, backup_id: str) -> bool:
        """
        Restore pipeline from backup.
        """
        try:
            backup_path = self.backup_dir / backup_id
            if not backup_path.exists():
                return False

            # Restore CI/CD files
            for file_path in backup_path.rglob("*"):
                if file_path.is_file():
                    relative_path = file_path.relative_to(backup_path)
                    target_path = project_path / relative_path
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, target_path)

            return True
        except Exception:
            return False

    def get_sync_status(self, project_path: Path) -> dict[str, Any]:
        """
        Get synchronization status.
        """
        status = {
            "last_sync": None,
            "has_changes": False,
            "backup_count": 0,
            "config_exists": (project_path / "cicd-config.json").exists(),
        }

        # Check for backups
        project_backups = [
            b for b in self.backup_dir.iterdir() if b.name.startswith(project_path.name)
        ]
        status["backup_count"] = len(project_backups)

        if project_backups:
            latest_backup = max(project_backups, key=lambda x: x.stat().st_mtime)
            status["last_sync"] = datetime.fromtimestamp(latest_backup.stat().st_mtime).isoformat()

        return status

    def _files_differ(self, file1: Path, file2: Path) -> bool:
        """
        Check if two files differ.
        """
        try:
            if file1.is_dir() and file2.is_dir():
                return self._dirs_differ(file1, file2)
            if file1.is_file() and file2.is_file():
                return file1.read_text() != file2.read_text()
            return True
        except Exception:
            return True

    def _dirs_differ(self, dir1: Path, dir2: Path) -> bool:
        """
        Check if two directories differ.
        """
        try:
            files1 = {f.relative_to(dir1) for f in dir1.rglob("*") if f.is_file()}
            files2 = {f.relative_to(dir2) for f in dir2.rglob("*") if f.is_file()}

            if files1 != files2:
                return True

            for file_path in files1:
                if self._files_differ(dir1 / file_path, dir2 / file_path):
                    return True

            return False
        except Exception:
            return True


class InMemoryTemplateProvider(CICDTemplateProvider):
    """
    In-memory implementation of template provider.
    """

    def __init__(self):
        self.templates: dict[str, CICDTemplate] = {}
        self._load_default_templates()

    def _load_default_templates(self):
        """
        Load default templates.
        """
        # Basic CI template
        basic_ci_template = CICDTemplate(
            name="basic-ci",
            description="Basic CI pipeline with lint, test, and build",
            project_types=[
                ProjectType.PHENO_SDK,
                ProjectType.ZEN_MCP_SERVER,
                ProjectType.ATOMS_MCP_OLD,
            ],
            stages=["lint", "test", "build"],
            template_content="""name: Basic CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Lint
        run: ruff check .

  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: {{ python_versions }}
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Test
        run: pytest

  build:
    runs-on: ubuntu-latest
    needs: [lint, test]
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: {{ python_versions[0] }}
      - name: Install dependencies
        run: pip install build
      - name: Build
        run: python -m build""",
            variables={"python_versions": ["3.11", "3.12"]},
        )

        self.templates["basic-ci"] = basic_ci_template

    def get_template(self, name: str) -> CICDTemplate | None:
        """
        Get template by name.
        """
        return self.templates.get(name)

    def list_templates(self) -> list[str]:
        """
        List available templates.
        """
        return list(self.templates.keys())

    def register_template(self, template: CICDTemplate) -> bool:
        """
        Register a new template.
        """
        try:
            self.templates[template.name] = template
            return True
        except Exception:
            return False

    def update_template(self, name: str, template: CICDTemplate) -> bool:
        """
        Update existing template.
        """
        if name not in self.templates:
            return False

        try:
            self.templates[name] = template
            return True
        except Exception:
            return False

    def delete_template(self, name: str) -> bool:
        """
        Delete template.
        """
        if name not in self.templates:
            return False

        try:
            del self.templates[name]
            return True
        except Exception:
            return False
