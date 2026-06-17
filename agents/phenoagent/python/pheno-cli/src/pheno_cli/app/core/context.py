"""
Context management for Pheno-CLI commands.
"""

from pathlib import Path
from typing import Any

from .config import load_config
from .context_detector import ContextDetector


class PhenoContext:
    """
    Context object passed between CLI commands.
    """

    def __init__(
        self,
        verbose: bool = False,
        debug: bool = False,
        config_path: Path | None = None,
        workspace: Path | None = None,
        context: str | None = None,
        argv0: str | None = None,
    ):
        """
        Initialize the context.
        """
        self.verbose = verbose
        self.debug = debug
        self.config_path = config_path
        self.workspace_override = workspace
        self.context_override = context

        # Load configuration
        self.config = load_config(config_path)

        # Initialize context detector
        self.context_detector = ContextDetector(self.config)

        # Detect and set current context
        if context:
            self.current_context = context
        else:
            self.current_context = self.context_detector.detect_context(
                path=workspace or Path.cwd(), argv0=argv0,
            )

        # Get context configuration
        self.context_config = self.config.context_system.get_context(self.current_context)
        if not self.context_config:
            # Fallback to pheno context
            self.current_context = "pheno"
            self.context_config = self.config.context_system.get_context("pheno")

        # Set workspace based on context
        if workspace:
            self._workspace = workspace.expanduser().resolve()
        elif self.context_config and self.context_config.workspace_path:
            self._workspace = self.context_config.workspace_path.expanduser().resolve()
        elif self.config.workspace_path:
            self._workspace = self.config.workspace_path.expanduser().resolve()
        else:
            self._workspace = Path.cwd()

    @property
    def workspace(self) -> Path:
        """
        Get the current workspace directory.
        """
        return self._workspace

    @workspace.setter
    def workspace(self, path: Path) -> None:
        """
        Set the workspace directory.
        """
        self._workspace = path.expanduser().resolve()

    @property
    def templates_dir(self) -> Path:
        """
        Get the templates directory.
        """
        if self.config.templates.custom_path:
            return self.config.templates.custom_path
        # Default to templates in pheno-sdk
        base_dir = Path(__file__).parent.parent.parent.parent / "templates"

        # Check for context-specific template directory
        context_templates = base_dir / self.current_context
        if context_templates.exists():
            return context_templates

        return base_dir

    @property
    def context_templates_dir(self) -> Path:
        """
        Get the context-specific templates directory.
        """
        base_dir = Path(__file__).parent.parent.parent.parent / "templates"
        return base_dir / self.current_context

    @property
    def shared_templates_dir(self) -> Path:
        """
        Get the shared templates directory.
        """
        base_dir = Path(__file__).parent.parent.parent.parent / "templates"
        return base_dir / "shared"

    def get_current_project_path(self) -> Path | None:
        """
        Get the current project path if we're inside one.
        """
        current = Path.cwd()

        # Look for pyproject.toml or .pheno.toml
        while current != current.parent:
            if (current / "pyproject.toml").exists() or (current / ".pheno.toml").exists():
                return current
            current = current.parent

        return None

    def is_pheno_project(self, path: Path) -> bool:
        """
        Check if a path is a pheno project.
        """
        return (path / ".pheno.toml").exists() or self._has_pheno_markers(path)

    def _has_pheno_markers(self, path: Path) -> bool:
        """
        Check for common pheno project markers.
        """
        pyproject_path = path / "pyproject.toml"
        if not pyproject_path.exists():
            return False

        try:
            import toml

            with open(pyproject_path) as f:
                pyproject = toml.load(f)

            # Check for pheno-sdk dependencies or project structure
            dependencies = pyproject.get("project", {}).get("dependencies", [])
            for dep in dependencies:
                if "pheno-sdk" in str(dep) or "-kit @" in str(dep):
                    return True

            # Check for context-specific naming patterns
            project_name = pyproject.get("project", {}).get("name", "")
            if self.context_config:
                return any(
                    self.context_detector._matches_pattern(project_name.lower(), pattern.lower())
                    for pattern in self.context_config.project_patterns
                )

            return any(
                pattern.replace("*", "") in project_name
                for pattern in self.config.workspace.project_patterns
            )

        except Exception:
            return False

    def switch_context(self, context_name: str) -> bool:
        """
        Switch to a different context.
        """
        if context_name not in self.config.context_system.contexts:
            return False

        self.current_context = context_name
        self.context_config = self.config.context_system.get_context(context_name)

        # Update workspace if context has specific workspace
        if (
            self.context_config
            and self.context_config.workspace_path
            and not self.workspace_override
        ):
            self._workspace = self.context_config.workspace_path.expanduser().resolve()

        return True

    def get_available_contexts(self) -> dict[str, str]:
        """
        Get all available contexts with descriptions.
        """
        return {
            name: config.description for name, config in self.config.context_system.contexts.items()
        }

    def get_context_info(self) -> dict[str, Any]:
        """
        Get information about the current context.
        """
        if not self.context_config:
            return {}

        return {
            "name": self.current_context,
            "display_name": self.context_config.name,
            "description": self.context_config.description,
            "workspace": str(self.workspace),
            "default_template": self.context_config.default_template,
            "deployment_targets": self.context_config.deployment_targets,
        }
