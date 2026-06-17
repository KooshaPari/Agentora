"""
CLI Command Registry System Centralized command registration and discovery for all CLI
entry points.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class CommandCategory(Enum):
    """
    Command category enumeration.
    """

    CORE = "core"
    ATLAS = "atlas"
    QUALITY = "quality"
    CICD = "cicd"
    PROJECT = "project"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"
    DEVELOPMENT = "development"


class ProjectType(Enum):
    """
    Project type enumeration.
    """

    PHENO_SDK = "pheno-sdk"
    ZEN_MCP_SERVER = "zen-mcp-server"
    ATOMS_MCP_OLD = "atoms_mcp-old"
    MORPH = "morph"
    ROUTER = "router"
    GLOBAL = "global"


@dataclass
class CLICommand:
    """
    CLI command definition.
    """

    name: str
    description: str
    handler: Callable
    category: CommandCategory
    project_types: set[ProjectType]
    aliases: list[str] = None
    options: list[dict[str, Any]] = None
    arguments: list[dict[str, Any]] = None
    dependencies: list[str] = None
    hidden: bool = False

    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []
        if self.options is None:
            self.options = []
        if self.arguments is None:
            self.arguments = []
        if self.dependencies is None:
            self.dependencies = []


class CommandRegistry:
    """
    Centralized command registry for all CLI systems.
    """

    def __init__(self):
        self.commands: dict[str, CLICommand] = {}
        self.categories: dict[CommandCategory, list[str]] = {cat: [] for cat in CommandCategory}
        self.project_commands: dict[ProjectType, set[str]] = {pt: set() for pt in ProjectType}
        self.aliases: dict[str, str] = {}

    def register_command(self, command: CLICommand) -> None:
        """
        Register a command.
        """
        # Register main command
        self.commands[command.name] = command
        self.categories[command.category].append(command.name)

        # Register for project types
        for project_type in command.project_types:
            self.project_commands[project_type].add(command.name)

        # Register aliases
        for alias in command.aliases:
            self.aliases[alias] = command.name

    def get_command(self, name: str) -> CLICommand | None:
        """
        Get command by name or alias.
        """
        # Check aliases first
        actual_name = self.aliases.get(name, name)
        return self.commands.get(actual_name)

    def get_commands_for_project(self, project_type: ProjectType) -> list[CLICommand]:
        """
        Get all commands available for a project type.
        """
        command_names = self.project_commands[project_type]
        return [self.commands[name] for name in command_names if not self.commands[name].hidden]

    def get_commands_by_category(self, category: CommandCategory) -> list[CLICommand]:
        """
        Get all commands in a category.
        """
        command_names = self.categories[category]
        return [self.commands[name] for name in command_names if not self.commands[name].hidden]

    def list_commands(self, project_type: ProjectType | None = None) -> list[CLICommand]:
        """
        List all commands, optionally filtered by project type.
        """
        if project_type:
            return self.get_commands_for_project(project_type)
        return [cmd for cmd in self.commands.values() if not cmd.hidden]

    def search_commands(self, query: str) -> list[CLICommand]:
        """
        Search commands by name or description.
        """
        query = query.lower()
        results = []

        for command in self.commands.values():
            if (
                query in command.name.lower()
                or query in command.description.lower()
                or any(query in alias.lower() for alias in command.aliases)
            ):
                results.append(command)

        return results


class CLIAdapter(ABC):
    """
    Abstract base class for CLI adapters.
    """

    def __init__(self, registry: CommandRegistry):
        self.registry = registry

    @abstractmethod
    def create_cli(self, project_type: ProjectType, commands: list[CLICommand]) -> Any:
        """
        Create CLI instance for the adapter.
        """

    @abstractmethod
    def add_command(self, cli: Any, command: CLICommand) -> None:
        """
        Add command to CLI instance.
        """

    @abstractmethod
    def run_cli(self, cli: Any, args: list[str]) -> int:
        """
        Run CLI with arguments.
        """


class CLIContext:
    """
    CLI context manager.
    """

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.project_type = self._detect_project_type()
        self.registry = CommandRegistry()
        self._load_commands()

    def _detect_project_type(self) -> ProjectType:
        """
        Detect project type from current path.
        """
        path_name = self.project_path.name

        if "pheno-sdk" in path_name:
            return ProjectType.PHENO_SDK
        if "zen-mcp-server" in path_name:
            return ProjectType.ZEN_MCP_SERVER
        if "atoms_mcp-old" in path_name:
            return ProjectType.ATOMS_MCP_OLD
        if "morph" in path_name:
            return ProjectType.MORPH
        if "router" in path_name:
            return ProjectType.ROUTER
        return ProjectType.GLOBAL

    def _load_commands(self) -> None:
        """
        Load all available commands.
        """
        # Core commands (available everywhere)
        self._register_core_commands()

        # Project-specific commands
        if self.project_type == ProjectType.PHENO_SDK:
            self._register_pheno_commands()
        elif self.project_type == ProjectType.ZEN_MCP_SERVER:
            self._register_zen_commands()
        elif self.project_type == ProjectType.ATOMS_MCP_OLD:
            self._register_atoms_commands()

        # CI/CD commands (available in all projects)
        self._register_cicd_commands()

        # Quality commands (available in all projects)
        self._register_quality_commands()

        # Atlas commands (available in all projects)
        self._register_atlas_commands()

    def _register_core_commands(self) -> None:
        """
        Register core commands available everywhere.
        """
        from .app.commands.status import run_status_check

        # Status command
        self.registry.register_command(
            CLICommand(
                name="status",
                description="Show project status",
                handler=run_status_check,
                category=CommandCategory.CORE,
                project_types={
                    ProjectType.PHENO_SDK,
                    ProjectType.ZEN_MCP_SERVER,
                    ProjectType.ATOMS_MCP_OLD,
                    ProjectType.GLOBAL,
                },
                options=[
                    {"name": "detailed", "flag": True, "help": "Show detailed status"},
                    {"name": "json", "flag": True, "help": "Output as JSON"},
                ],
            ),
        )

        # Help command
        def help_handler(args):
            print("Available commands:")
            for cmd in self.registry.get_commands_for_project(self.project_type):
                print(f"  {cmd.name}: {cmd.description}")
            return 0

        self.registry.register_command(
            CLICommand(
                name="help",
                description="Show help information",
                handler=help_handler,
                category=CommandCategory.CORE,
                project_types={
                    ProjectType.PHENO_SDK,
                    ProjectType.ZEN_MCP_SERVER,
                    ProjectType.ATOMS_MCP_OLD,
                    ProjectType.GLOBAL,
                },
                aliases=["-h", "--help"],
            ),
        )

    def _register_pheno_commands(self) -> None:
        """
        Register Pheno-SDK specific commands.
        """

        # Build command
        def build_handler(args):
            import subprocess

            return subprocess.run(["make", "build"], check=False).returncode

        self.registry.register_command(
            CLICommand(
                name="build",
                description="Build the project",
                handler=build_handler,
                category=CommandCategory.CORE,
                project_types={ProjectType.PHENO_SDK},
            ),
        )

        # Test command
        def test_handler(args):
            import subprocess

            return subprocess.run(["make", "test"], check=False).returncode

        self.registry.register_command(
            CLICommand(
                name="test",
                description="Run tests",
                handler=test_handler,
                category=CommandCategory.CORE,
                project_types={ProjectType.PHENO_SDK},
            ),
        )

    def _register_zen_commands(self) -> None:
        """
        Register Zen-MCP-Server specific commands.
        """

        # Start command
        def start_handler(args):
            print("🚀 Starting Zen MCP Server...")
            import subprocess

            return subprocess.run(["python", "-m", "zen_mcp_server.server"], check=False).returncode

        self.registry.register_command(
            CLICommand(
                name="start",
                description="Start Zen MCP server",
                handler=start_handler,
                category=CommandCategory.PROJECT,
                project_types={ProjectType.ZEN_MCP_SERVER},
                options=[
                    {"name": "port", "type": int, "default": 8000, "help": "Port to run on"},
                    {"name": "dev", "flag": True, "help": "Enable development mode"},
                    {"name": "no-tunnel", "flag": True, "help": "Disable tunnel"},
                ],
            ),
        )

        # Stop command
        def stop_handler(args):
            print("🛑 Stopping Zen MCP Server...")
            # Implementation would stop the server
            return 0

        self.registry.register_command(
            CLICommand(
                name="stop",
                description="Stop Zen MCP server",
                handler=stop_handler,
                category=CommandCategory.PROJECT,
                project_types={ProjectType.ZEN_MCP_SERVER},
            ),
        )

    def _register_atoms_commands(self) -> None:
        """
        Register Atoms-MCP-Old specific commands.
        """

        # Check command
        def check_handler(args):
            print("🔍 Running Atoms check...")
            import subprocess

            return subprocess.run(["./atoms", "check"], check=False).returncode

        self.registry.register_command(
            CLICommand(
                name="check",
                description="Run Atoms check",
                handler=check_handler,
                category=CommandCategory.PROJECT,
                project_types={ProjectType.ATOMS_MCP_OLD},
            ),
        )

    def _register_cicd_commands(self) -> None:
        """
        Register CI/CD commands.
        """
        from ..cicd.cli import CICDCLI

        cicd_cli = CICDCLI()

        # CI/CD Generate
        self.registry.register_command(
            CLICommand(
                name="cicd-generate",
                description="Generate CI/CD pipeline",
                handler=cicd_cli.generate,
                category=CommandCategory.CICD,
                project_types={
                    ProjectType.PHENO_SDK,
                    ProjectType.ZEN_MCP_SERVER,
                    ProjectType.ATOMS_MCP_OLD,
                    ProjectType.GLOBAL,
                },
                options=[
                    {
                        "name": "project-type",
                        "choices": ["pheno-sdk", "zen-mcp-server", "atoms_mcp-old"],
                        "help": "Project type",
                    },
                    {"name": "project-name", "help": "Project name"},
                    {"name": "config", "help": "Configuration file path"},
                ],
                arguments=[{"name": "path", "help": "Project path"}],
            ),
        )

        # CI/CD Sync
        self.registry.register_command(
            CLICommand(
                name="cicd-sync",
                description="Synchronize CI/CD configuration",
                handler=cicd_cli.sync,
                category=CommandCategory.CICD,
                project_types={
                    ProjectType.PHENO_SDK,
                    ProjectType.ZEN_MCP_SERVER,
                    ProjectType.ATOMS_MCP_OLD,
                    ProjectType.GLOBAL,
                },
                options=[
                    {
                        "name": "strategy",
                        "choices": ["overwrite", "merge", "backup_and_overwrite", "manual_review"],
                        "help": "Sync strategy",
                    },
                ],
                arguments=[
                    {"name": "source", "help": "Source project path"},
                    {"name": "targets", "nargs": "+", "help": "Target project paths"},
                ],
            ),
        )

    def _register_quality_commands(self) -> None:
        """
        Register quality commands.
        """

        # Pattern detection
        def pattern_detection_handler(args):
            import subprocess

            return subprocess.run(
                ["python3", "scripts/advanced_pattern_detector.py", ".", "--json"], check=False,
            ).returncode

        self.registry.register_command(
            CLICommand(
                name="pattern-detection",
                description="Run advanced pattern detection",
                handler=pattern_detection_handler,
                category=CommandCategory.QUALITY,
                project_types={
                    ProjectType.PHENO_SDK,
                    ProjectType.ZEN_MCP_SERVER,
                    ProjectType.ATOMS_MCP_OLD,
                    ProjectType.GLOBAL,
                },
            ),
        )

    def _register_atlas_commands(self) -> None:
        """
        Register Atlas commands.
        """
        from ..cli.commands.atlas import atlas_health, atlas_status

        # Atlas Health
        self.registry.register_command(
            CLICommand(
                name="atlas-health",
                description="Generate atlas health report",
                handler=atlas_health,
                category=CommandCategory.ATLAS,
                project_types={
                    ProjectType.PHENO_SDK,
                    ProjectType.ZEN_MCP_SERVER,
                    ProjectType.ATOMS_MCP_OLD,
                    ProjectType.GLOBAL,
                },
            ),
        )

        # Atlas Status
        self.registry.register_command(
            CLICommand(
                name="atlas-status",
                description="Show atlas status",
                handler=atlas_status,
                category=CommandCategory.ATLAS,
                project_types={
                    ProjectType.PHENO_SDK,
                    ProjectType.ZEN_MCP_SERVER,
                    ProjectType.ATOMS_MCP_OLD,
                    ProjectType.GLOBAL,
                },
            ),
        )

    def get_available_commands(self) -> list[CLICommand]:
        """
        Get all available commands for current context.
        """
        return self.registry.get_commands_for_project(self.project_type)
