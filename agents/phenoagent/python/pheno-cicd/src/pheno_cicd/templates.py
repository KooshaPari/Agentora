"""
CI/CD template engine and registry.
"""

from typing import Any

try:
    from jinja2 import BaseLoader, Environment, FileSystemLoader, Template
    from jinja2.exceptions import TemplateError

    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

    # Mock classes for when jinja2 is not available
    class Environment:
        def __init__(self, *args, **kwargs):
            pass

        def from_string(self, template_string):
            return MockTemplate(template_string)

        def get_template(self, name):
            return MockTemplate("")

    class BaseLoader:
        pass

    class TemplateError(Exception):
        pass

    class MockTemplate:
        def __init__(self, template_string):
            self.template_string = template_string

        def render(self, **kwargs):
            # Simple template rendering without jinja2
            result = self.template_string
            for key, value in kwargs.items():
                result = result.replace(f"{{{{ {key} }}}}", str(value))
                result = result.replace(f"{{ {key} }}", str(value))
            return result


from .core import CICDTemplate, ProjectType


class TemplateLoader(BaseLoader):
    """
    Custom template loader for CI/CD templates.
    """

    def __init__(self, templates: dict[str, CICDTemplate]):
        self.templates = templates

    def get_source(self, environment, template):
        """
        Get template source.
        """
        if template in self.templates:
            return self.templates[template].template_content, None, None
        raise TemplateError(f"Template '{template}' not found")

    def list_templates(self):
        """
        List available templates.
        """
        return list(self.templates.keys())


class TemplateEngine:
    """
    Template engine for CI/CD generation.
    """

    def __init__(self, templates: dict[str, CICDTemplate]):
        self.templates = templates
        self.loader = TemplateLoader(templates)
        self.env = Environment(loader=self.loader)

        # Add custom filters if jinja2 is available
        if JINJA2_AVAILABLE:
            self.env.filters["yaml_dump"] = self._yaml_dump
            self.env.filters["json_dump"] = self._json_dump
            self.env.filters["join_lines"] = self._join_lines
            self.env.filters["indent"] = self._indent

    def render_template(self, template_name: str, context: dict[str, Any]) -> str:
        """
        Render a template with context.
        """
        try:
            template = self.env.get_template(template_name)
            return template.render(**context)
        except TemplateError as e:
            raise ValueError(f"Template rendering error: {e}")

    def render_string(self, template_string: str, context: dict[str, Any]) -> str:
        """
        Render a template string with context.
        """
        try:
            template = self.env.from_string(template_string)
            return template.render(**context)
        except TemplateError as e:
            raise ValueError(f"Template rendering error: {e}")

    def validate_template(self, template_name: str, context: dict[str, Any]) -> list[str]:
        """
        Validate template with context.
        """
        errors = []
        try:
            template = self.env.get_template(template_name)
            template.render(**context)
        except TemplateError as e:
            errors.append(f"Template error: {e}")
        except Exception as e:
            errors.append(f"Rendering error: {e}")

        return errors

    def get_template_variables(self, template_name: str) -> list[str]:
        """
        Get variables used in template.
        """
        try:
            template = self.env.get_template(template_name)
            return list(template.get_corresponding_lineno(template.source))
        except TemplateError:
            return []

    def _yaml_dump(self, data: Any, indent: int = 2) -> str:
        """
        YAML dump filter.
        """
        import yaml

        return yaml.dump(data, default_flow_style=False, indent=indent)

    def _json_dump(self, data: Any, indent: int = 2) -> str:
        """
        JSON dump filter.
        """
        import json

        return json.dumps(data, indent=indent)

    def _join_lines(self, lines: list[str], separator: str = "\n") -> str:
        """
        Join lines filter.
        """
        return separator.join(lines)

    def _indent(self, text: str, spaces: int = 2) -> str:
        """
        Indent text filter.
        """
        lines = text.split("\n")
        indented = [(" " * spaces + line) for line in lines]
        return "\n".join(indented)


class TemplateRegistry:
    """
    Registry for CI/CD templates.
    """

    def __init__(self):
        self.templates: dict[str, CICDTemplate] = {}
        self.engines: dict[str, TemplateEngine] = {}
        self._load_default_templates()

    def _load_default_templates(self):
        """
        Load default templates.
        """
        # GitHub Actions CI template
        github_ci_template = CICDTemplate(
            name="github-ci",
            description="GitHub Actions CI pipeline",
            project_types=[
                ProjectType.PHENO_SDK,
                ProjectType.ZEN_MCP_SERVER,
                ProjectType.ATOMS_MCP_OLD,
            ],
            stages=["lint", "test", "build", "security", "quality"],
            template_content="""name: {{ project_name | title }} CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  workflow_dispatch:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

env:
  PYTHON_VERSION: "{{ python_versions[0] }}"
  CACHE_VERSION: v1

jobs:
  lint:
    name: Lint & Format Check
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install ruff black isort mypy

      - name: Run Ruff
        run: ruff check . --output-format=github

      - name: Check formatting (Black)
        run: black --check .

      - name: Check import sorting (isort)
        run: isort --check-only .

      - name: Type check (MyPy)
        run: mypy .
        continue-on-error: true

  test:
    name: Tests (Python ${{ matrix.python-version }})
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: {{ os_versions | yaml_dump }}
        python-version: {{ python_versions | yaml_dump }}

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-xdist

      - name: Run tests
        run: pytest -n auto --cov=. --cov-report=xml --cov-report=term-missing

      - name: Upload coverage to Codecov
        if: matrix.os == 'ubuntu-latest' && matrix.python-version == '{{ python_versions[0] }}'
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          fail_ci_if_error: false

  security:
    name: Security Scan
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install bandit safety

      - name: Run Bandit
        run: bandit -r . -f json -o bandit-report.json || true

      - name: Check dependencies (Safety)
        run: safety check --json || true

  quality:
    name: Quality Gates
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run quality analysis
        run: |
          python -c "
          from pheno.quality.manager import quality_manager
          from pheno.quality.config import get_config

          config = get_config('{{ project_type.value }}')
          manager = quality_manager
          manager.config = config

          report = manager.analyze_project('.')
          summary = manager.generate_summary(report)

          print(f'Quality Score: {{summary[\"quality_score\"]:.1f}}/100')
          print(f'Total Issues: {{summary[\"total_issues\"]}}')

          if summary['quality_score'] < {{ quality_thresholds.get('quality_score_threshold', 70) }}:
              print('❌ Quality score below threshold')
              exit(1)
          else:
              print('✅ Quality score meets threshold')
          "

  build:
    name: Build Package
    runs-on: ubuntu-latest
    needs: [lint, test, security, quality]
    if: github.event_name == 'push' || github.event_name == 'release'

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install build dependencies
        run: |
          python -m pip install --upgrade pip
          pip install build twine

      - name: Build package
        run: python -m build

      - name: Check package
        run: twine check dist/*

      - name: Upload build artifacts
        uses: actions/upload-artifact@v3
        with:
          name: dist
          path: dist/

  all-checks:
    name: All Checks Passed
    runs-on: ubuntu-latest
    needs: [lint, test, security, quality, build]
    if: always()
    steps:
      - name: All checks passed
        run: |
          if [[ "${{ needs.lint.result }}" == "success" &&
                "${{ needs.test.result }}" == "success" &&
                "${{ needs.security.result }}" == "success" &&
                "${{ needs.quality.result }}" == "success" &&
                "${{ needs.build.result }}" == "success" ]]; then
            echo "✅ All CI checks passed!"
          else
            echo "❌ Some checks failed"
            exit 1
          fi""",
            variables={
                "project_name": "{{ project_name }}",
                "project_type": "{{ project_type }}",
                "python_versions": "{{ python_versions }}",
                "os_versions": "{{ os_versions }}",
                "quality_thresholds": "{{ quality_thresholds }}",
            },
        )

        self.templates["github-ci"] = github_ci_template

        # Docker template
        docker_template = CICDTemplate(
            name="docker",
            description="Docker configuration",
            project_types=[
                ProjectType.PHENO_SDK,
                ProjectType.ZEN_MCP_SERVER,
                ProjectType.ATOMS_MCP_OLD,
            ],
            stages=["build"],
            template_content="""# Multi-stage Dockerfile for {{ project_name }}
FROM python:{{ python_versions[0] }}-slim as builder

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:{{ python_versions[0] }}-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install runtime dependencies
RUN apt-get update && apt-get install -y \\
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set work directory
WORKDIR /app

# Copy Python dependencies from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Change ownership to appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \\
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run application
CMD ["python", "-m", "{{ project_name }}"]""",
            variables={
                "project_name": "{{ project_name }}",
                "python_versions": "{{ python_versions }}",
            },
        )

        self.templates["docker"] = docker_template

        # Docker Compose template
        docker_compose_template = CICDTemplate(
            name="docker-compose",
            description="Docker Compose configuration",
            project_types=[
                ProjectType.PHENO_SDK,
                ProjectType.ZEN_MCP_SERVER,
                ProjectType.ATOMS_MCP_OLD,
            ],
            stages=["build"],
            template_content="""version: '3.8'

services:
  {{ project_name }}:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - PYTHON_VERSION={{ python_versions[0] }}
      - ENVIRONMENT=development
    volumes:
      - .:/app
      - /app/__pycache__
    depends_on:
      - redis
      - postgres
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB={{ project_name }}
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  redis_data:
  postgres_data:""",
            variables={
                "project_name": "{{ project_name }}",
                "python_versions": "{{ python_versions }}",
            },
        )

        self.templates["docker-compose"] = docker_compose_template

        # Makefile template
        makefile_template = CICDTemplate(
            name="makefile",
            description="Makefile for project automation",
            project_types=[
                ProjectType.PHENO_SDK,
                ProjectType.ZEN_MCP_SERVER,
                ProjectType.ATOMS_MCP_OLD,
            ],
            stages=["build", "test", "deploy"],
            template_content="""# {{ project_name | title }} Makefile

.PHONY: help install test lint format build clean deploy

# Default target
help: ## Show this help message
\t@echo "Available targets:"
\t@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \\033[36m%-15s\\033[0m %s\\n", $$1, $$2}'

install: ## Install dependencies
\tpython -m pip install --upgrade pip
\tpip install -r requirements.txt
\tpip install -e .

install-dev: ## Install development dependencies
\tpython -m pip install --upgrade pip
\tpip install -r requirements.txt
\tpip install -r requirements-dev.txt
\tpip install -e .

test: ## Run tests
\tpytest -v --cov=. --cov-report=html --cov-report=term-missing

test-fast: ## Run tests without coverage
\tpytest -v

lint: ## Run linting
\truff check .
\tblack --check .
\tisort --check-only .
\tmypy .

format: ## Format code
\tblack .
\tisort .

build: ## Build package
\tpython -m build

clean: ## Clean build artifacts
\trm -rf build/
\trm -rf dist/
\trm -rf *.egg-info/
\tfind . -type d -name __pycache__ -exec rm -rf {} +
\tfind . -type f -name "*.pyc" -delete

deploy: ## Deploy application
\t@echo "Deploying {{ project_name }}..."
\t# Add deployment commands here

docker-build: ## Build Docker image
\tdocker build -t {{ project_name }}:latest .

docker-run: ## Run Docker container
\tdocker run -p 8000:8000 {{ project_name }}:latest

docker-compose-up: ## Start services with Docker Compose
\tdocker-compose up -d

docker-compose-down: ## Stop services with Docker Compose
\tdocker-compose down

quality: ## Run quality analysis
\tpython -c "
\tfrom pheno.quality.manager import quality_manager
\tfrom pheno.quality.config import get_config
\t
\tconfig = get_config('{{ project_type.value }}')
\tmanager = quality_manager
\tmanager.config = config
\t
\treport = manager.analyze_project('.')
\tsummary = manager.generate_summary(report)
\t
\tprint(f'Quality Score: {summary[\"quality_score\"]:.1f}/100')
\tprint(f'Total Issues: {summary[\"total_issues\"]}')
\t"

ci: ## Run CI pipeline locally
\tmake lint
\tmake test
\tmake quality
\tmake build

all: ## Run all checks
\tmake ci""",
            variables={"project_name": "{{ project_name }}", "project_type": "{{ project_type }}"},
        )

        self.templates["makefile"] = makefile_template

    def register_template(self, template: CICDTemplate) -> None:
        """
        Register a template.
        """
        self.templates[template.name] = template
        self.engines[template.name] = TemplateEngine({template.name: template})

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

    def get_engine(self, name: str) -> TemplateEngine | None:
        """
        Get template engine by name.
        """
        return self.engines.get(name)

    def render_template(self, name: str, context: dict[str, Any]) -> str:
        """
        Render template with context.
        """
        template = self.templates.get(name)
        if not template:
            raise ValueError(f"Template '{name}' not found")

        engine = self.engines.get(name)
        if not engine:
            engine = TemplateEngine({name: template})
            self.engines[name] = engine

        return engine.render_template(name, context)

    def validate_template(self, name: str, context: dict[str, Any]) -> list[str]:
        """
        Validate template with context.
        """
        template = self.templates.get(name)
        if not template:
            return [f"Template '{name}' not found"]

        engine = self.engines.get(name)
        if not engine:
            engine = TemplateEngine({name: template})
            self.engines[name] = engine

        return engine.validate_template(name, context)
