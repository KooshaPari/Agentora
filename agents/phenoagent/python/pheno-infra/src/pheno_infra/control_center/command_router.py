"""Command routing and context switching for Pheno Control Center.

Provides CommandRouter for dispatching commands to appropriate project contexts with
environment switching and command preprocessing.
"""

import logging
import shlex
from pathlib import Path
from typing import Any

from pheno.infra.control_center.command_executor import CLIBridge

logger = logging.getLogger(__name__)


class CommandRouter:
    """Router for dispatching commands to appropriate project contexts.

    Provides routing logic for pheno-cli commands to different projects with environment
    context switching and command preprocessing.
    """

    def __init__(self, cli_bridge: CLIBridge):
        """
        Initialize command router.
        """
        self.cli_bridge = cli_bridge

        # Project context mappings
        self.project_contexts: dict[str, dict[str, Any]] = {}

        # Command aliases and shortcuts
        self.aliases: dict[str, list[str]] = {
            "a": ["atoms"],
            "z": ["zen"],
            "start": ["start"],
            "stop": ["stop"],
            "restart": ["restart"],
            "status": ["status"],
            "logs": ["logs"],
        }

        logger.info("Command router initialized")

    def register_project_context(
        self,
        project_name: str,
        working_dir: Path | None = None,
        env_vars: dict[str, str] | None = None,
        cli_prefix: list[str] | None = None,
    ) -> None:
        """Register context for a project.

        Args:
            project_name: Project name
            working_dir: Working directory for commands
            env_vars: Environment variables
            cli_prefix: Default CLI prefix (e.g., ['atoms'])
        """
        self.project_contexts[project_name] = {
            "working_dir": working_dir,
            "env_vars": env_vars or {},
            "cli_prefix": cli_prefix or [],
        }
        logger.debug(f"Registered context for project: {project_name}")

    def route_command(
        self,
        command_input: str,
        default_project: str | None = None,
    ) -> str | None:
        """Route a command input to appropriate project context.

        Args:
            command_input: Raw command input from user
            default_project: Default project if not specified

        Returns:
            Command ID if successfully routed, None otherwise
        """
        # Parse command
        parts = shlex.split(command_input.strip())
        if not parts:
            return None

        # Expand aliases
        first_part = parts[0].lower()
        if first_part in self.aliases:
            parts = self.aliases[first_part] + parts[1:]

        # Determine target project
        project_name = None
        command_parts = parts

        # Check if first part is a known project
        if parts[0] in self.project_contexts:
            project_name = parts[0]
            command_parts = parts[1:]
        elif default_project and default_project in self.project_contexts:
            project_name = default_project

        if not project_name:
            # Try to infer from common commands
            if "atoms" in command_input.lower():
                project_name = "atoms"
            elif "zen" in command_input.lower():
                project_name = "zen"
            else:
                # Use global context
                project_name = None

        # Get project context
        context = self.project_contexts.get(project_name, {}) if project_name else {}

        # Build full command
        if project_name and context.get("cli_prefix"):
            full_command = context["cli_prefix"] + command_parts
        else:
            full_command = command_parts

        # Execute command
        try:
            command_id = self.cli_bridge.execute_command(
                command=full_command,
                project_name=project_name,
                working_dir=context.get("working_dir"),
                env_vars=context.get("env_vars"),
                stream_output=True,
            )

            logger.info(f"Routed command to {project_name or 'global'}: {' '.join(full_command)}")
            return command_id

        except Exception as e:
            logger.exception(f"Failed to route command: {e}")
            return None

    def get_command_suggestions(self, partial_input: str) -> list[str]:
        """Get command suggestions for autocomplete.

        Args:
            partial_input: Partial command input

        Returns:
            List of suggested completions
        """
        suggestions = []

        # Add project names
        for project in self.project_contexts:
            if project.startswith(partial_input.lower()):
                suggestions.append(project)

        # Add aliases
        for alias in self.aliases:
            if alias.startswith(partial_input.lower()):
                suggestions.append(alias)

        # Add common commands
        common_commands = ["start", "stop", "restart", "status", "logs", "help"]
        for cmd in common_commands:
            if cmd.startswith(partial_input.lower()):
                suggestions.append(cmd)

        return sorted(set(suggestions))

    def get_project_commands(self, project_name: str) -> list[str]:
        """
        Get available commands for a project.
        """
        # This could be enhanced to introspect actual CLI capabilities
        base_commands = ["start", "stop", "restart", "status", "logs", "help"]
        return [f"{project_name} {cmd}" for cmd in base_commands]


__all__ = [
    "CommandRouter",
]
