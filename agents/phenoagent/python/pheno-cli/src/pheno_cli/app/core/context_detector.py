"""
Context detection engine for multi-context CLI.
"""

import os
import sys
from pathlib import Path

from .config import PhenoConfig, get_project_config


class ContextDetector:
    """
    Detects the appropriate context for the CLI based on various signals.
    """

    def __init__(self, config: PhenoConfig):
        """
        Initialize the context detector.
        """
        self.config = config

    def detect_from_entry_point(self, argv0: str | None = None) -> str | None:
        """
        Detect context from command name (atoms, zen, byteport).
        """

        if argv0 is None:
            argv0 = sys.argv[0] if sys.argv else ""

        # Get the command name from the path
        command_name = Path(argv0).name

        # Check for known context entry points
        context_map = {
            "atoms": "atoms",
            "zen": "zen",
            "byteport": "byteport",
            "pheno": "pheno",
            "pheno-cli": "pheno",
        }

        return context_map.get(command_name)

    def detect_from_project(self, path: Path | None = None) -> str | None:
        """
        Detect context from project files and patterns.
        """

        if path is None:
            path = Path.cwd()

        # Look for project configuration first
        project_config = get_project_config(path)
        if project_config and "project" in project_config:
            explicit_context = project_config["project"].get("context")
            if explicit_context:
                return explicit_context

        # Check for context-specific files and patterns
        context_indicators = {
            "atoms": ["atoms_server.py", "fastmcp.py", "authkit_client", "vercel.json"],
            "zen": [
                "zen_launcher.py",
                "zen_config.yaml",
                "providers/",
                "workflows/",
                "systemprompts/",
            ],
            "byteport": ["byteport.yaml", "platform.yaml", "k8s/", "infrastructure/"],
        }

        # Check for indicator files
        for context, indicators in context_indicators.items():
            for indicator in indicators:
                indicator_path = path / indicator
                if indicator_path.exists():
                    return context

        # Check project name patterns
        project_name = path.name.lower()
        for context_name, context_config in self.config.context_system.contexts.items():
            for pattern in context_config.project_patterns:
                # Simple pattern matching (replace * with anything)
                if self._matches_pattern(project_name, pattern.lower()):
                    return context_name

        return None

    def detect_from_environment(self) -> str | None:
        """
        Detect context from environment variables.
        """

        # Check for explicit context override
        env_context = os.environ.get("PHENO_CONTEXT")
        if env_context:
            return env_context

        # Check for context-specific environment variables
        if os.environ.get("ATOMS_SERVER_URL"):
            return "atoms"

        if os.environ.get("ZEN_CONFIG_PATH"):
            return "zen"

        if os.environ.get("BYTEPORT_PLATFORM"):
            return "byteport"

        return None

    def detect_from_config(self, path: Path | None = None) -> str | None:
        """
        Detect context from configuration files.
        """

        if path is None:
            path = Path.cwd()

        # Check .pheno.toml
        project_config_path = path / ".pheno.toml"
        if project_config_path.exists():
            try:
                from pheno.config.core import Config

                temp_config = Config.from_file(project_config_path)
                config = temp_config.model_dump()
                return config.get("project", {}).get("context")
            except Exception:
                pass

        # Check pyproject.toml for context hints
        pyproject_path = path / "pyproject.toml"
        if pyproject_path.exists():
            try:
                from pheno.config.core import Config

                temp_config = Config.from_file(pyproject_path)
                config = temp_config.model_dump()
                project_name = config.get("project", {}).get("name", "")

                # Check for context-specific dependencies
                dependencies = config.get("project", {}).get("dependencies", [])

                for dep in dependencies:
                    dep_str = str(dep).lower()
                    if "fastmcp" in dep_str or "authkit" in dep_str:
                        return "atoms"
                    if "temporalio" in dep_str or "nats-py" in dep_str:
                        return "zen"

                # Check project name
                for context_name, context_config in self.config.context_system.contexts.items():
                    for pattern in context_config.project_patterns:
                        if self._matches_pattern(project_name.lower(), pattern.lower()):
                            return context_name

            except Exception:
                pass

        return None

    def detect_context(self, path: Path | None = None, argv0: str | None = None) -> str:
        """
        Main detection logic with fallbacks.
        """

        # Priority order for context detection:

        # 1. Entry point detection (highest priority)
        if context := self.detect_from_entry_point(argv0):
            return context

        # 2. Environment variables
        if context := self.detect_from_environment():
            return context

        # 3. Project files and configuration
        if context := self.detect_from_project(path):
            return context

        # 4. Configuration files
        if context := self.detect_from_config(path):
            return context

        # 5. Current context from config
        if self.config.context_system.current_context:
            return self.config.context_system.current_context

        # 6. Default context (fallback)
        return self.config.context_system.default_context

    def _matches_pattern(self, text: str, pattern: str) -> bool:
        """
        Simple pattern matching with * wildcard support.
        """

        if "*" not in pattern:
            return text == pattern

        # Split pattern by * and check each part
        parts = pattern.split("*")

        # First part must be at the beginning
        if parts[0] and not text.startswith(parts[0]):
            return False

        # Last part must be at the end
        if parts[-1] and not text.endswith(parts[-1]):
            return False

        # Check middle parts
        current_pos = len(parts[0]) if parts[0] else 0

        for part in parts[1:-1]:
            if part:
                pos = text.find(part, current_pos)
                if pos == -1:
                    return False
                current_pos = pos + len(part)

        return True
