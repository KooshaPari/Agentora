"""
Main CI/CD generator implementation.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .adapters import (
    DefaultConfigProvider,
)
from .core import (
    CICDConfig,
    CICDGenerator,
    CICDPipeline,
    PipelineStage,
    ProjectType,
)
from .quality import QualityGateIntegrator
from .templates import TemplateRegistry


class PhenoCICDGenerator(CICDGenerator):
    """
    Pheno CI/CD generator implementation.
    """

    def __init__(self, config: CICDConfig):
        super().__init__(config)
        self.template_registry = TemplateRegistry()
        self.quality_integrator = QualityGateIntegrator()
        self._load_templates()

    def _load_templates(self):
        """
        Load all available templates.
        """
        # Templates are loaded by the TemplateRegistry

    def generate_pipeline(self, project_path: Path) -> CICDPipeline:
        """
        Generate a complete CI/CD pipeline.
        """
        pipeline = CICDPipeline(
            name=f"{self.config.project_name}-cicd", project_path=project_path, config=self.config,
        )

        # Generate GitHub Actions workflows
        self._generate_github_workflows(pipeline)

        # Generate Docker files
        self._generate_docker_files(pipeline)

        # Generate Makefile
        self._generate_makefile(pipeline)

        # Generate configuration files
        self._generate_config_files(pipeline)

        # Integrate quality checks
        return self.quality_integrator.integrate_quality_checks(pipeline)


    def generate_workflow(self, stage: PipelineStage) -> str:
        """
        Generate a specific workflow file.
        """
        context = self._create_template_context()

        if stage in (PipelineStage.LINT, PipelineStage.TEST, PipelineStage.BUILD, PipelineStage.SECURITY, PipelineStage.QUALITY, PipelineStage.DEPLOY, PipelineStage.RELEASE, PipelineStage.CLEANUP):
            return self.template_registry.render_template("github-ci", context)
        return self.template_registry.render_template("github-ci", context)

    def generate_dockerfile(self) -> str:
        """
        Generate Dockerfile.
        """
        context = self._create_template_context()
        return self.template_registry.render_template("docker", context)

    def generate_docker_compose(self) -> str:
        """
        Generate docker-compose.yml.
        """
        context = self._create_template_context()
        return self.template_registry.render_template("docker-compose", context)

    def generate_makefile(self) -> str:
        """
        Generate Makefile.
        """
        context = self._create_template_context()
        return self.template_registry.render_template("makefile", context)

    def _generate_github_workflows(self, pipeline: CICDPipeline):
        """
        Generate GitHub Actions workflows.
        """
        context = self._create_template_context()

        # Main CI workflow
        ci_workflow = self.template_registry.render_template("github-ci", context)
        pipeline.add_file(".github/workflows/ci.yml", ci_workflow)

        # Additional workflows based on project type
        if self.config.project_type == ProjectType.PHENO_SDK:
            # Pheno-SDK specific workflows
            self._generate_pheno_sdk_workflows(pipeline, context)
        elif self.config.project_type == ProjectType.ZEN_MCP_SERVER:
            # Zen-MCP-Server specific workflows
            self._generate_zen_mcp_workflows(pipeline, context)
        elif self.config.project_type == ProjectType.ATOMS_MCP_OLD:
            # Atoms-MCP-Old specific workflows
            self._generate_atoms_mcp_workflows(pipeline, context)

    def _generate_pheno_sdk_workflows(self, pipeline: CICDPipeline, context: dict[str, Any]):
        """
        Generate Pheno-SDK specific workflows.
        """
        # Code quality workflow
        quality_workflow = """name: Code Quality Gates

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  quality-full:
    name: Full Quality Analysis
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[quality,test]"

      - name: Run comprehensive quality analysis
        run: |
          make quality-full

      - name: Upload quality reports
        uses: actions/upload-artifact@v3
        with:
          name: quality-reports
          path: reports/
"""
        pipeline.add_file(".github/workflows/quality-full.yml", quality_workflow)

        # Performance workflow
        performance_workflow = """name: Performance Analysis

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  performance:
    name: Performance Tests
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[quality,test]"

      - name: Run performance tests
        run: |
          make performance

      - name: Upload performance reports
        uses: actions/upload-artifact@v3
        with:
          name: performance-reports
          path: reports/performance/
"""
        pipeline.add_file(".github/workflows/performance.yml", performance_workflow)

    def _generate_zen_mcp_workflows(self, pipeline: CICDPipeline, context: dict[str, Any]):
        """
        Generate Zen-MCP-Server specific workflows.
        """
        # Docker build workflow
        docker_workflow = """name: Docker Build

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  docker-build:
    name: Build Docker Image
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build Docker image
        run: |
          docker build -t zen-mcp-server:latest .

      - name: Test Docker image
        run: |
          docker run --rm zen-mcp-server:latest --help
"""
        pipeline.add_file(".github/workflows/docker-build.yml", docker_workflow)

    def _generate_atoms_mcp_workflows(self, pipeline: CICDPipeline, context: dict[str, Any]):
        """
        Generate Atoms-MCP-Old specific workflows.
        """
        # Legacy compatibility workflow
        legacy_workflow = """name: Legacy Compatibility

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  legacy-check:
    name: Legacy Compatibility Check
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Check legacy imports
        run: |
          python scripts/check_legacy_imports.py

      - name: Run compatibility tests
        run: |
          pytest tests/compatibility/
"""
        pipeline.add_file(".github/workflows/legacy-compatibility.yml", legacy_workflow)

    def _generate_docker_files(self, pipeline: CICDPipeline):
        """
        Generate Docker files.
        """
        dockerfile = self.generate_dockerfile()
        pipeline.add_file("Dockerfile", dockerfile)

        docker_compose = self.generate_docker_compose()
        pipeline.add_file("docker-compose.yml", docker_compose)

        # Generate additional Docker files based on project type
        if self.config.project_type == ProjectType.ZEN_MCP_SERVER:
            # Production Dockerfile
            prod_dockerfile = """# Production Dockerfile for zen-mcp-server
FROM python:3.10-slim as builder

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \\
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

CMD ["python", "-m", "zen_mcp_server"]
"""
            pipeline.add_file("Dockerfile.production", prod_dockerfile)

    def _generate_makefile(self, pipeline: CICDPipeline):
        """
        Generate Makefile.
        """
        makefile = self.generate_makefile()
        pipeline.add_file("Makefile", makefile)

    def _generate_config_files(self, pipeline: CICDPipeline):
        """
        Generate configuration files.
        """
        # CI/CD configuration
        cicd_config = json.dumps(self.config.to_dict(), indent=2)
        pipeline.add_file(".github/cicd-config.json", cicd_config)

        # GitHub Actions configuration
        github_config = {
            "workflows": {
                "ci": {
                    "enabled": True,
                    "triggers": ["push", "pull_request"],
                    "branches": ["main", "develop"],
                },
                "quality": {"enabled": True, "triggers": ["push"], "branches": ["main"]},
            },
            "environments": {
                "production": {
                    "protection_rules": ["required_reviewers"],
                    "secrets": ["DEPLOY_TOKEN"],
                },
            },
        }

        github_config_json = json.dumps(github_config, indent=2)
        pipeline.add_file(".github/config.json", github_config_json)

    def _create_template_context(self) -> dict[str, Any]:
        """
        Create template context.
        """
        return {
            "project_name": self.config.project_name,
            "project_type": self.config.project_type.value,
            "python_versions": self.config.python_versions,
            "os_versions": self.config.os_versions,
            "quality_thresholds": self.config.quality_thresholds,
            "security_checks": self.config.security_checks,
            "test_commands": self.config.test_commands,
            "build_commands": self.config.build_commands,
            "deploy_commands": self.config.deploy_commands,
            "dependencies": self.config.dependencies,
            "environment_variables": self.config.environment_variables,
            "secrets": self.config.secrets,
            "artifacts": self.config.artifacts,
            "notifications": self.config.notifications,
            "custom_stages": self.config.custom_stages,
            "generated_at": datetime.now().isoformat(),
        }

    def _should_generate_stage(self, stage: PipelineStage) -> bool:
        """
        Determine if a stage should be generated.
        """
        # Always generate core stages
        core_stages = [PipelineStage.LINT, PipelineStage.TEST, PipelineStage.BUILD]
        if stage in core_stages:
            return True

        # Generate quality stage if quality checks are enabled
        if stage == PipelineStage.QUALITY and self.config.quality_thresholds:
            return True

        # Generate security stage if security checks are enabled
        if stage == PipelineStage.SECURITY and self.config.security_checks:
            return True

        # Generate deploy stage if deploy commands are defined
        if stage == PipelineStage.DEPLOY and self.config.deploy_commands:
            return True

        # Generate release stage for certain project types
        return bool(stage == PipelineStage.RELEASE and self.config.project_type in [ProjectType.PHENO_SDK, ProjectType.ZEN_MCP_SERVER])


class CICDGeneratorFactory:
    """
    Factory for creating CI/CD generators.
    """

    @staticmethod
    def create_generator(
        project_type: ProjectType, custom_config: CICDConfig | None = None,
    ) -> PhenoCICDGenerator:
        """
        Create a CI/CD generator for a project type.
        """
        config_provider = DefaultConfigProvider()
        base_config = config_provider.get_default_config(project_type)

        if custom_config:
            config = config_provider.merge_configs(base_config, custom_config)
        else:
            config = base_config

        return PhenoCICDGenerator(config)

    @staticmethod
    def create_generator_from_config(config: CICDConfig) -> PhenoCICDGenerator:
        """
        Create a CI/CD generator from configuration.
        """
        return PhenoCICDGenerator(config)
