"""Configuration and Project Registry for Pheno Control Center.

Provides centralized configuration management for multi-project orchestration with
validation, schema definitions, and plugin extensibility.
"""

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from pheno.shared.project_framework.config import ProjectConfig as BaseProjectConfig
from pheno.shared.project_framework.config import (
    ProjectType,
)

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """
    Raised when configuration validation fails.
    """



@dataclass
class ProjectConfig(BaseProjectConfig):
    """
    Control Center project configuration built on the shared project model.
    """

    project_type: ProjectType = ProjectType.CUSTOM
    cli_entry: list[str] = field(default_factory=list)
    base_port: int = 50000
    fallback_port_offset: int = 0
    proxy_port_offset: int = 0
    health_endpoint: str | None = None
    tunnel_domain: str | None = "kooshapari.com"
    env_vars: dict[str, str] = field(default_factory=dict)
    working_directory: str | None = None
    auto_start: bool = False
    dependencies: list[str] = field(default_factory=list)
    plugins: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """
        Run shared validation and extend with Control Center specifics.
        """

        super().validate()

        if not self.cli_entry:
            raise ValidationError(f"Project {self.name} must have cli_entry defined")

        if not isinstance(self.cli_entry, list):
            raise ValidationError(f"Project {self.name} cli_entry must be a list")

        if self.base_port < 1024 or self.base_port > 65535:
            raise ValidationError(f"Project {self.name} base_port must be between 1024-65535")

        for dep in self.dependencies:
            if not dep or not isinstance(dep, str):
                raise ValidationError(f"Invalid dependency in project {self.name}: {dep}")

    def get_fallback_port(self, base_fallback_port: int = 9000) -> int:
        """
        Get the fallback port for this project.
        """
        return base_fallback_port + self.fallback_port_offset

    def get_proxy_port(self, base_proxy_port: int = 9100) -> int:
        """
        Get the proxy port for this project.
        """
        return base_proxy_port + self.proxy_port_offset


@dataclass
class ControlCenterConfig:
    """
    Main configuration for the Pheno Control Center.
    """

    projects: dict[str, ProjectConfig] = field(default_factory=dict)
    """
    Registered projects by name.
    """

    base_fallback_port: int = 9000
    """
    Base port for fallback servers.
    """

    base_proxy_port: int = 9100
    """
    Base port for proxy servers.
    """

    monitor_refresh_interval: float = 2.0
    """
    UI refresh interval in seconds.
    """

    log_retention_days: int = 7
    """
    How long to keep log files.
    """

    enable_desktop_gui: bool = True
    """
    Enable PyQt desktop application.
    """

    enable_tui_monitor: bool = True
    """
    Enable enhanced TUI monitor.
    """

    config_dir: Path | None = None
    """
    Configuration directory (defaults to ~/.kinfra/control_center)
    """

    plugins_dir: Path | None = None
    """
    Directory to search for plugins.
    """

    telemetry_endpoint: str | None = None
    """
    Optional telemetry/metrics endpoint.
    """

    metadata: dict[str, Any] = field(default_factory=dict)
    """
    Additional configuration metadata.
    """

    def __post_init__(self):
        """
        Initialize default paths.
        """
        if self.config_dir is None:
            self.config_dir = Path.home() / ".kinfra" / "control_center"

        if self.plugins_dir is None:
            self.plugins_dir = self.config_dir / "plugins"

        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.plugins_dir.mkdir(parents=True, exist_ok=True)

    def validate(self) -> None:
        """
        Validate the control center configuration.
        """
        if self.base_fallback_port < 1024 or self.base_fallback_port > 65535:
            raise ValidationError("base_fallback_port must be between 1024-65535")

        if self.base_proxy_port < 1024 or self.base_proxy_port > 65535:
            raise ValidationError("base_proxy_port must be between 1024-65535")

        if self.monitor_refresh_interval <= 0:
            raise ValidationError("monitor_refresh_interval must be positive")

        # Validate all projects
        for name, project in self.projects.items():
            if project.name != name:
                raise ValidationError(
                    f"Project key '{name}' doesn't match project name '{project.name}'",
                )
            project.validate()

        # Validate project dependencies
        self._validate_dependencies()

    def _validate_dependencies(self) -> None:
        """
        Validate that all project dependencies exist and don't create cycles.
        """
        project_names = set(self.projects.keys())

        for name, project in self.projects.items():
            for dep in project.dependencies:
                if dep not in project_names:
                    raise ValidationError(f"Project {name} depends on unknown project: {dep}")

        # Check for circular dependencies using DFS
        def has_cycle(start: str, visited: set, rec_stack: set) -> bool:
            visited.add(start)
            rec_stack.add(start)

            project = self.projects.get(start)
            if project:
                for dep in project.dependencies:
                    if dep not in visited:
                        if has_cycle(dep, visited, rec_stack):
                            return True
                    elif dep in rec_stack:
                        return True

            rec_stack.remove(start)
            return False

        visited = set()
        for name in project_names:
            if name not in visited:
                if has_cycle(name, visited, set()):
                    raise ValidationError(f"Circular dependency detected involving project: {name}")


class ProjectRegistry:
    """
    Registry for managing pheno-sdk project configurations.
    """

    def __init__(self, config_dir: Path | None = None):
        """
        Initialize the project registry.
        """
        self.config_dir = config_dir or Path.home() / ".kinfra" / "control_center"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.registry_file = self.config_dir / "projects.yaml"
        self.runtime_state_file = self.config_dir / "runtime_state.json"

        self.config = ControlCenterConfig(config_dir=self.config_dir)
        self._load_config()

        # Runtime state for active projects
        self.runtime_state: dict[str, dict[str, Any]] = {}
        self._load_runtime_state()

        logger.info(f"Project registry initialized with {len(self.config.projects)} projects")

    def _load_config(self) -> None:
        """
        Load configuration from disk.
        """
        if not self.registry_file.exists():
            # Create default configuration
            self._create_default_config()
            return

        try:
            with open(self.registry_file) as f:
                data = yaml.safe_load(f) or {}

            # Parse projects
            projects = {}
            for name, project_data in data.get("projects", {}).items():
                try:
                    projects[name] = ProjectConfig(**project_data)
                except Exception as e:
                    logger.warning(f"Failed to load project {name}: {e}")

            # Update config
            self.config.projects = projects

            # Load other config fields
            for key, value in data.items():
                if key != "projects" and hasattr(self.config, key):
                    setattr(self.config, key, value)

            # Validate
            self.config.validate()

        except Exception as e:
            logger.exception(f"Failed to load registry configuration: {e}")
            self._create_default_config()

    def _create_default_config(self) -> None:
        """
        Create default configuration with common pheno-sdk projects.
        """
        logger.info("Creating default project registry configuration")

        # Default projects for pheno-sdk
        default_projects = {
            "atoms": ProjectConfig(
                name="atoms",
                cli_entry=["atoms", "start"],
                base_port=50000,
                fallback_port_offset=1,
                proxy_port_offset=1,
                health_endpoint="/health",
                tunnel_domain="kooshapari.com",
                auto_start=False,
            ),
            "zen": ProjectConfig(
                name="zen",
                cli_entry=["zen", "start"],
                base_port=50001,
                fallback_port_offset=2,
                proxy_port_offset=2,
                health_endpoint="/health",
                tunnel_domain="kooshapari.com",
                auto_start=False,
            ),
        }

        self.config.projects = default_projects
        self.save_config()

    def save_config(self) -> None:
        """
        Save configuration to disk.
        """
        try:
            # Validate before saving
            self.config.validate()

            data = {
                "projects": {
                    name: asdict(project) for name, project in self.config.projects.items()
                },
                "base_fallback_port": self.config.base_fallback_port,
                "base_proxy_port": self.config.base_proxy_port,
                "monitor_refresh_interval": self.config.monitor_refresh_interval,
                "log_retention_days": self.config.log_retention_days,
                "enable_desktop_gui": self.config.enable_desktop_gui,
                "enable_tui_monitor": self.config.enable_tui_monitor,
                "telemetry_endpoint": self.config.telemetry_endpoint,
                "metadata": self.config.metadata,
            }

            with open(self.registry_file, "w") as f:
                yaml.dump(data, f, default_flow_style=False, indent=2)

            logger.debug(f"Saved project registry with {len(self.config.projects)} projects")

        except Exception as e:
            logger.exception(f"Failed to save project registry: {e}")
            raise

    def _load_runtime_state(self) -> None:
        """
        Load runtime state from disk.
        """
        if not self.runtime_state_file.exists():
            self.runtime_state = {}
            return

        try:
            with open(self.runtime_state_file) as f:
                self.runtime_state = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load runtime state: {e}")
            self.runtime_state = {}

    def _save_runtime_state(self) -> None:
        """
        Save runtime state to disk.
        """
        try:
            with open(self.runtime_state_file, "w") as f:
                json.dump(self.runtime_state, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Failed to save runtime state: {e}")

    def register_project(self, config: ProjectConfig) -> None:
        """
        Register a new project.
        """
        config.validate()
        self.config.projects[config.name] = config
        self.save_config()
        logger.info(f"Registered project: {config.name}")

    def unregister_project(self, name: str) -> bool:
        """
        Unregister a project.
        """
        if name in self.config.projects:
            del self.config.projects[name]
            self.save_config()

            # Clean up runtime state
            self.runtime_state.pop(name, None)
            self._save_runtime_state()

            logger.info(f"Unregistered project: {name}")
            return True
        return False

    def get_project(self, name: str) -> ProjectConfig | None:
        """
        Get project configuration by name.
        """
        return self.config.projects.get(name)

    def list_projects(self) -> list[str]:
        """
        List all registered project names.
        """
        return list(self.config.projects.keys())

    def get_startup_order(self) -> list[str]:
        """
        Get project startup order respecting dependencies.
        """
        # Topological sort for dependency ordering
        visited = set()
        temp_visited = set()
        order = []

        def visit(name: str):
            if name in temp_visited:
                raise ValidationError(f"Circular dependency detected: {name}")
            if name in visited:
                return

            temp_visited.add(name)

            project = self.config.projects.get(name)
            if project:
                for dep in project.dependencies:
                    visit(dep)

            temp_visited.remove(name)
            visited.add(name)
            order.append(name)

        for name in self.config.projects:
            visit(name)

        return order

    def update_runtime_state(self, project_name: str, state_data: dict[str, Any]) -> None:
        """
        Update runtime state for a project.
        """
        if project_name not in self.runtime_state:
            self.runtime_state[project_name] = {}

        self.runtime_state[project_name].update(state_data)
        self.runtime_state[project_name]["last_updated"] = time.time()
        self._save_runtime_state()

    def get_runtime_state(self, project_name: str) -> dict[str, Any]:
        """
        Get runtime state for a project.
        """
        return self.runtime_state.get(project_name, {})
