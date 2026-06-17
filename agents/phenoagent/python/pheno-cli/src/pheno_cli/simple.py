"""
Simple CLI Entry Point A lightweight CLI that doesn't depend on all pheno modules.
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import Any

# Version manager will be imported locally in the publish handler


class SimpleCLI:
    """
    Simple CLI implementation.
    """

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.project_type = self._detect_project_type()
        self.commands = self._load_commands()

    def _run_subprocess(self, cmd: list[str], env: dict[str, str] | None = None) -> int:
        """
        Run a subprocess relative to the project root.
        """
        return subprocess.run(cmd, check=False, cwd=self.project_path, env=env).returncode

    def _run_make(
        self,
        target: str,
        args: list[str] | None = None,
        fallback: list[str] | None = None,
    ) -> int:
        """
        Invoke make with a specific target if a Makefile exists; otherwise fallback to piping the command.
        """
        if args is None:
            args = []
        makefile = self.project_path / "Makefile"
        if makefile.exists():
            return self._run_subprocess(["make", target, *args])
        if fallback is not None:
            return self._run_subprocess(fallback + args)
        print("Makefile not found; unable to run make target.")
        return 1

    def _detect_project_type(self) -> str:
        """
        Detect project type from current path.
        """
        path_name = self.project_path.name

        # Check for specific project indicators
        if "pheno-sdk" in path_name or (self.project_path / "pheno").exists():
            return "pheno-sdk"
        if (self.project_path / "zen").exists() and (self.project_path / "zen").is_file():
            return "zen-mcp-server"
        if (self.project_path / "atoms").exists() and (self.project_path / "atoms").is_file():
            return "atoms_mcp-old"
        if "zen-mcp-server" in path_name:
            return "zen-mcp-server"
        if "atoms_mcp-old" in path_name:
            return "atoms_mcp-old"
        if "morph" in path_name:
            return "morph"
        if "router" in path_name:
            return "router"
        return "global"

    def _load_commands(self) -> dict[str, dict[str, Any]]:
        """
        Load available commands.
        """
        common_projects = [
            "pheno-sdk",
            "zen-mcp-server",
            "atoms_mcp-old",
            "router",
            "morph",
            "global",
        ]

        return {
            # Core commands
            "status": {
                "description": "Show project status",
                "handler": self._status_handler,
                "available": common_projects,
            },
            "help": {
                "description": "Show help information",
                "handler": self._help_handler,
                "available": common_projects,
                "aliases": ["-h", "--help"],
            },
            "version": {
                "description": "Show version information",
                "handler": self._version_handler,
                "available": common_projects,
                "aliases": ["-v", "--version"],
            },
            # Workspace-wide build/test flows
            "install": {
                "description": "Install project dependencies",
                "handler": self._install_handler,
                "available": common_projects,
            },
            "install-dev": {
                "description": "Install development dependencies",
                "handler": self._install_dev_handler,
                "available": common_projects,
            },
            "setup": {
                "description": "Run full development setup",
                "handler": self._setup_handler,
                "available": common_projects,
            },
            "clean": {
                "description": "Clean build artefacts",
                "handler": self._clean_handler,
                "available": common_projects,
            },
            "build": {
                "description": "Build the project",
                "handler": self._build_handler,
                "available": ["pheno-sdk", "router", "morph", "atoms_mcp-old"],
            },
            "test": {
                "description": "Run tests",
                "handler": self._test_handler,
                "available": common_projects,
            },
            "test-cov": {
                "description": "Run tests with coverage",
                "handler": self._test_cov_handler,
                "available": ["pheno-sdk", "router", "morph", "atoms_mcp-old"],
            },
            "quality": {
                "description": "Run quality checks",
                "handler": self._quality_handler,
                "available": ["pheno-sdk", "router", "morph", "atoms_mcp-old"],
            },
            "lint": {
                "description": "Run linting (ruff)",
                "handler": self._lint_handler,
                "available": common_projects,
            },
            "format": {
                "description": "Format code",
                "handler": self._format_handler,
                "available": common_projects,
            },
            "type-check": {
                "description": "Run type checker",
                "handler": self._type_check_handler,
                "available": common_projects,
            },
            "dev": {
                "description": "Run developer check suite",
                "handler": self._dev_handler,
                "available": ["pheno-sdk", "router", "morph", "atoms_mcp-old"],
            },
            "ci": {
                "description": "Run CI pipeline locally",
                "handler": self._ci_handler,
                "available": ["pheno-sdk", "router", "morph", "atoms_mcp-old"],
            },
            "serve": {
                "description": "Run the local service/server",
                "handler": self._serve_handler,
                "available": ["router", "morph", "zen-mcp-server"],
            },
            # Zen commands
            "start": {
                "description": "Start Zen MCP server",
                "handler": self._zen_start_handler,
                "available": ["zen-mcp-server"],
            },
            "stop": {
                "description": "Stop Zen MCP server",
                "handler": self._zen_stop_handler,
                "available": ["zen-mcp-server"],
            },
            # Atoms commands
            "check": {
                "description": "Run Atoms check",
                "handler": self._atoms_check_handler,
                "available": ["atoms_mcp-old"],
            },
            # CI/CD commands
            "cicd-generate": {
                "description": "Generate CI/CD pipeline",
                "handler": self._cicd_generate_handler,
                "available": ["pheno-sdk", "zen-mcp-server", "atoms_mcp-old", "global"],
            },
            "cicd-sync": {
                "description": "Synchronize CI/CD configuration",
                "handler": self._cicd_sync_handler,
                "available": ["pheno-sdk", "zen-mcp-server", "atoms_mcp-old", "global"],
            },
            "cicd-update": {
                "description": "Update soft dependencies",
                "handler": self._cicd_update_handler,
                "available": ["pheno-sdk", "zen-mcp-server", "atoms_mcp-old", "global"],
            },
            "cicd-status": {
                "description": "Show CI/CD status",
                "handler": self._cicd_status_handler,
                "available": ["pheno-sdk", "zen-mcp-server", "atoms_mcp-old", "global"],
            },
            "cicd-validate": {
                "description": "Validate CI/CD configuration",
                "handler": self._cicd_validate_handler,
                "available": ["pheno-sdk", "zen-mcp-server", "atoms_mcp-old", "global"],
            },
            "cicd-manage": {
                "description": "Manage CI/CD across all projects",
                "handler": self._cicd_manage_handler,
                "available": ["pheno-sdk", "zen-mcp-server", "atoms_mcp-old", "global"],
            },
            # Atlas commands
            "atlas-health": {
                "description": "Generate atlas health report",
                "handler": self._atlas_health_handler,
                "available": ["pheno-sdk", "zen-mcp-server", "atoms_mcp-old", "global"],
            },
            "atlas-status": {
                "description": "Show atlas status",
                "handler": self._atlas_status_handler,
                "available": ["pheno-sdk", "zen-mcp-server", "atoms_mcp-old", "global"],
            },
            # Quality commands
            "pattern-detection": {
                "description": "Run advanced pattern detection",
                "handler": self._pattern_detection_handler,
                "available": ["pheno-sdk", "zen-mcp-server", "atoms_mcp-old", "global"],
            },
            "architectural-validation": {
                "description": "Run architectural pattern validation",
                "handler": self._architectural_validation_handler,
                "available": ["pheno-sdk", "zen-mcp-server", "atoms_mcp-old", "global"],
            },
            # Publishing commands
            "publish": {
                "description": "Publish latest commit in main to a bumped version",
                "handler": self._publish_handler,
                "available": ["pheno-sdk"],
            },
        }


    def get_available_commands(self) -> list[str]:
        """
        Get available commands for current project type.
        """
        available = []
        for name, cmd in self.commands.items():
            if self.project_type in cmd.get("available", []):
                available.append(name)
        return available

    def run(self, args: list[str]) -> int:
        """
        Run CLI with arguments.
        """
        if not args:
            self._help_handler([])
            return 0

        command_name = args[0]
        command_args = args[1:]

        # Check aliases
        for name, cmd in self.commands.items():
            if command_name in cmd.get("aliases", []):
                command_name = name
                break

        if command_name not in self.commands:
            print(f"Unknown command: {command_name}")
            self._help_handler([])
            return 1

        command = self.commands[command_name]

        if self.project_type not in command.get("available", []):
            print(f"Command '{command_name}' not available for project type '{self.project_type}'")
            return 1

        try:
            return command["handler"](command_args)
        except Exception as e:
            print(f"Error executing {command_name}: {e}")
            return 1

    def _help_handler(self, args: list[str]) -> int:
        """
        Show help information.
        """
        print(f"{self.project_type.title()} CLI")
        print("Available commands:")

        available_commands = self.get_available_commands()
        for name in available_commands:
            cmd = self.commands[name]
            print(f"  {name}: {cmd['description']}")

        print(f"\nUsage: {self.project_type} <command> [options]")
        print("Examples:")
        print(f"  {self.project_type} status")
        print(f"  {self.project_type} help")
        return 0

    def _version_handler(self, args: list[str]) -> int:
        """
        Show version information.
        """
        print(f"{self.project_type.title()} CLI v1.0.0")
        return 0

    def _status_handler(self, args: list[str]) -> int:
        """
        Show project status.
        """
        print(f"📊 {self.project_type.title()} Status")
        print(f"Project Type: {self.project_type}")
        print(f"Project Path: {self.project_path}")

        # Check if it's a git repository
        if (self.project_path / ".git").exists():
            print("Git: ✅ Repository")
        else:
            print("Git: ❌ Not a repository")

        # Check for common files
        common_files = ["README.md", "requirements.txt", "pyproject.toml", "Makefile"]
        for file in common_files:
            if (self.project_path / file).exists():
                print(f"{file}: ✅ Found")
            else:
                print(f"{file}: ❌ Not found")

        return 0

    def _install_handler(self, args: list[str]) -> int:
        """
        Install project dependencies.
        """
        print("📦 Installing project dependencies...")
        fallback = ["pip", "install", "-e", "."]
        return self._run_make("install", args, fallback=fallback)

    def _install_dev_handler(self, args: list[str]) -> int:
        """
        Install development dependencies.
        """
        print("🛠️ Installing development dependencies...")
        fallback = ["pip", "install", "-e", ".[dev]"]
        return self._run_make("install-dev", args, fallback=fallback)

    def _setup_handler(self, args: list[str]) -> int:
        """
        Run project setup workflow.
        """
        print("🧰 Setting up development environment...")
        return self._run_make("setup", args, fallback=["pip", "install", "-e", ".[dev]"])

    def _clean_handler(self, args: list[str]) -> int:
        """
        Clean generated artefacts.
        """
        print("🧹 Cleaning project artefacts...")
        return self._run_make("clean", args)

    def _build_handler(self, args: list[str]) -> int:
        """
        Build the project.
        """
        print("🔨 Building project...")
        return self._run_make("build", args, fallback=["python", "-m", "build"])

    def _test_handler(self, args: list[str]) -> int:
        """
        Run tests.
        """
        print("🧪 Running tests...")
        if args:
            return self._run_subprocess(["pytest", *args])
        return self._run_make("test", [])

    def _test_cov_handler(self, args: list[str]) -> int:
        """
        Run tests with coverage reporting.
        """
        print("🧪 Running tests with coverage...")
        if args:
            return self._run_subprocess(["pytest", "--cov", *args])
        return self._run_make("test-cov", [])

    def _quality_handler(self, args: list[str]) -> int:
        """
        Run quality checks.
        """
        print("🔍 Running quality checks...")
        return self._run_make("quality", args)

    def _lint_handler(self, args: list[str]) -> int:
        """
        Run linting for the project.
        """
        print("🧹 Running lint checks...")
        if args:
            return self._run_subprocess(["ruff", "check", *args])
        return self._run_make("lint", [])

    def _format_handler(self, args: list[str]) -> int:
        """
        Format project sources.
        """
        print("🪄 Formatting sources...")
        if args:
            return self._run_subprocess(["ruff", "format", *args])
        return self._run_make("format", [])

    def _type_check_handler(self, args: list[str]) -> int:
        """
        Run static type checking.
        """
        print("🔎 Running type checks...")
        if args:
            return self._run_subprocess(["mypy", *args])
        return self._run_make("type-check", [])

    def _dev_handler(self, args: list[str]) -> int:
        """
        Run the developer quality suite.
        """
        print("🧪 Running developer checks...")
        return self._run_make("dev", args)

    def _ci_handler(self, args: list[str]) -> int:
        """
        Execute the CI pipeline locally.
        """
        print("🧬 Running CI pipeline...")
        return self._run_make("ci", args)

    def _serve_handler(self, args: list[str]) -> int:
        """
        Run the local service/server.
        """
        if self.project_type == "router":
            print("🚀 Starting KRouter API server...")
            cmd = ["python", "-m", "router.main", *args]
            return self._run_subprocess(cmd)
        if self.project_type == "morph":
            print("🚀 Starting Morph MCP server...")
            cmd = ["python", "server.py", *args]
            return self._run_subprocess(cmd)
        if self.project_type == "zen-mcp-server":
            print("🚀 Starting Zen MCP server...")
            return self._zen_start_handler(args)
        print(f"Serve command not supported for project type '{self.project_type}'.")
        return 1

    def _zen_start_handler(self, args: list[str]) -> int:
        """
        Start Zen MCP server.
        """
        print("🚀 Starting Zen MCP Server...")
        return self._run_subprocess(["python", "-m", "zen_mcp_server.server", *args])

    def _zen_stop_handler(self, args: list[str]) -> int:
        """
        Stop Zen MCP server.
        """
        print("🛑 Stopping Zen MCP Server...")
        # Implementation would stop the server
        return 0

    def _atoms_check_handler(self, args: list[str]) -> int:
        """
        Run Atoms check.
        """
        print("🔍 Running Atoms check...")
        return self._run_subprocess(["./atoms", "check", *args])

    def _cicd_generate_handler(self, args: list[str]) -> int:
        """
        Generate CI/CD pipeline.
        """
        print("🔧 Generating CI/CD pipeline...")
        return self._run_subprocess(["python3", "-m", "src.pheno.cicd.cli", "generate", *args])

    def _cicd_sync_handler(self, args: list[str]) -> int:
        """
        Synchronize CI/CD configuration.
        """
        print("🔄 Synchronizing CI/CD configuration...")
        return self._run_subprocess(["python3", "-m", "src.pheno.cicd.cli", "sync", *args])

    def _cicd_update_handler(self, args: list[str]) -> int:
        """
        Update soft dependencies.
        """
        print("📦 Updating soft dependencies...")
        return self._run_subprocess(["python3", "-m", "src.pheno.cicd.cli", "update", *args])

    def _cicd_status_handler(self, args: list[str]) -> int:
        """
        Show CI/CD status.
        """
        print("📊 Showing CI/CD status...")
        return self._run_subprocess(["python3", "-m", "src.pheno.cicd.cli", "status", *args])

    def _cicd_validate_handler(self, args: list[str]) -> int:
        """
        Validate CI/CD configuration.
        """
        print("✅ Validating CI/CD configuration...")
        return self._run_subprocess(["python3", "-m", "src.pheno.cicd.cli", "validate", *args])

    def _cicd_manage_handler(self, args: list[str]) -> int:
        """
        Manage CI/CD across all projects.
        """
        print("🎛️ Managing CI/CD across all projects...")
        return self._run_subprocess(["python3", "-m", "src.pheno.cicd.manager", *args])

    def _atlas_health_handler(self, args: list[str]) -> int:
        """
        Generate atlas health report.
        """
        print("🏥 Generating atlas health report...")
        cmd = ["python3", "scripts/atlas_health.py"]
        if not any(arg == "--json" or arg.startswith("--json=") for arg in args):
            cmd.append("--json")
        cmd.extend(args)
        return self._run_subprocess(cmd)

    def _atlas_status_handler(self, args: list[str]) -> int:
        """
        Show atlas status.
        """
        print("📊 Showing atlas status...")
        cmd = ["python3", "scripts/atlas_health.py"]
        cmd.extend(args)
        return self._run_subprocess(cmd)

    def _pattern_detection_handler(self, args: list[str]) -> int:
        """
        Run advanced pattern detection.
        """
        print("🔍 Running advanced pattern detection...")
        return self._run_subprocess(
            ["python3", "scripts/advanced_pattern_detector.py", ".", "--json"],
        )

    def _architectural_validation_handler(self, args: list[str]) -> int:
        """
        Run architectural pattern validation.
        """
        print("🏗️ Running architectural pattern validation...")
        return self._run_subprocess(
            ["python3", "scripts/architectural_pattern_validator.py", ".", "--json"],
        )

    def _publish_handler(self, args: list[str]) -> int:
        """
        Publish latest commit in main to a bumped version.
        """
        # Handle help
        if "--help" in args or "-h" in args:
            print("📦 Publish Command")
            print("Publish latest commit in main to a bumped version")
            print("\nUsage:")
            print("  pheno publish [bump_type|custom_version]")
            print("\nArguments:")
            print("  bump_type      Type of version bump: patch, minor, major (default: patch)")
            print("  custom_version Custom version in format X.Y.Z")
            print("\nExamples:")
            print("  pheno publish              # Bump patch version (0.1.2 -> 0.1.3)")
            print("  pheno publish minor        # Bump minor version (0.1.2 -> 0.2.0)")
            print("  pheno publish major        # Bump major version (0.1.2 -> 1.0.0)")
            print("  pheno publish 2.0.0        # Set custom version")
            return 0

        # Import standalone version manager
        try:
            import sys
            sys.path.insert(0, str(self.project_path))
            from version_manager import VersionManager
        except ImportError as e:
            print(f"❌ Version manager not available: {e}")
            print("Please ensure version_manager.py is in the project root")
            return 1

        try:
            version_manager = VersionManager(self.project_path)

            # Check if we're in a git repo
            if not version_manager.is_git_repo():
                print("❌ Not a git repository")
                return 1

            # Check if we're on main branch
            if not version_manager.is_on_main_branch():
                print("❌ Must be on main branch to publish")
                return 1

            # Check if working tree is clean
            if not version_manager.is_clean_working_tree():
                print("❌ Working tree is not clean. Please commit or stash changes first.")
                return 1

            # Get current version
            current_version = version_manager.get_current_version()
            print(f"📦 Current version: {current_version}")

            # Determine bump type or custom version
            if args and args[0] != "patch":
                if args[0] in ["major", "minor", "patch"]:
                    bump_type = args[0]
                    new_version = version_manager.bump_version(current_version, bump_type)
                else:
                    # Custom version provided
                    new_version = args[0]
                    # Validate custom version format
                    if not re.match(r"^\d+\.\d+\.\d+$", new_version):
                        print(f"❌ Invalid version format: {new_version}. Use format: X.Y.Z")
                        return 1
            else:
                # Default to patch bump
                bump_type = "patch"
                new_version = version_manager.bump_version(current_version, bump_type)

            print(f"🚀 Bumping version to: {new_version}")

            # Update pyproject.toml
            version_manager.update_pyproject_version(new_version)
            print("✅ Updated pyproject.toml")

            # Commit changes
            version_manager.commit_changes(new_version)
            print("✅ Committed version changes")

            # Create tag
            version_manager.create_tag(new_version)
            print(f"✅ Created tag v{new_version}")

            # Build package
            print("🔨 Building package...")
            version_manager.build_package()
            print("✅ Package built successfully")

            # Ask for confirmation before publishing
            print(f"\n📤 Ready to publish version {new_version}")
            print("This will:")
            print("  - Push commits to main branch")
            print(f"  - Push tag v{new_version}")
            print("  - Upload package to PyPI")

            confirm = input("\nProceed with publishing? (y/N): ").strip().lower()
            if confirm not in ["y", "yes"]:
                print("❌ Publishing cancelled")
                return 1

            # Push changes
            print("📤 Pushing changes...")
            version_manager.push_changes(include_tags=True)
            print("✅ Changes pushed to remote")

            # Publish package
            print("📦 Publishing to PyPI...")
            version_manager.publish_package()
            print("✅ Package published successfully")

            # Cleanup
            print("🧹 Cleaning up build artifacts...")
            version_manager.cleanup_build_artifacts()
            print("✅ Cleanup completed")

            print(f"\n🎉 Successfully published version {new_version}!")
            print(f"📦 Package available at: https://pypi.org/project/pheno-sdk/{new_version}/")

            return 0

        except Exception as e:
            print(f"❌ Error during publishing: {e}")
            return 1


def create_simple_cli(project_path: Path | None = None) -> int:
    """
    Create and run simple CLI.
    """
    if project_path is None:
        project_path = Path.cwd()

    cli = SimpleCLI(project_path)
    return cli.run(sys.argv[1:])


def main():
    """
    Main entry point.
    """
    return create_simple_cli()


if __name__ == "__main__":
    sys.exit(main())
