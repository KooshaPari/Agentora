"""CLI Bridge for Pheno Control Center.

Provides integration between the TUI monitor and pheno-cli commands, enabling command
execution with real-time output streaming.
"""

import logging
import subprocess
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    """
    Result of a command execution.
    """

    command_id: str
    command: str
    project_name: str
    exit_code: int
    stdout: str
    stderr: str
    start_time: float
    end_time: float
    success: bool


class CLIBridge:
    """Bridge between TUI monitor and pheno-cli commands.

    Handles:
    - Command execution with real-time output
    - Output streaming to TUI components
    - Command history and result tracking
    - Project context detection
    """

    def __init__(self, pheno_cli_path: str | None = None):
        """
        Initialize CLI bridge.
        """
        self.pheno_cli_path = pheno_cli_path or "pheno"
        self.output_callbacks: list[Callable] = []
        self.command_results: dict[str, CommandResult] = {}
        self.running_commands: dict[str, subprocess.Popen] = {}
        self.command_counter = 0

        logger.info(f"CLI Bridge initialized with pheno-cli path: {self.pheno_cli_path}")

    def add_output_callback(self, callback: Callable[[str, str, str], None]) -> None:
        """
        Add callback for command output streaming.
        """
        self.output_callbacks.append(callback)
        logger.debug("Added output callback")

    def _emit_output(self, command_id: str, stream_type: str, line: str) -> None:
        """
        Emit output to all registered callbacks.
        """
        for callback in self.output_callbacks:
            try:
                callback(command_id, stream_type, line)
            except Exception as e:
                logger.exception(f"Output callback error: {e}")

    def execute_command(
        self,
        command: str,
        project_name: str | None = None,
        working_directory: str | None = None,
    ) -> str:
        """
        Execute a pheno-cli command and return command ID.
        """
        self.command_counter += 1
        command_id = f"cmd_{self.command_counter}"

        # Detect project context if not provided
        if not project_name:
            project_name = self._detect_project_context(command, working_directory)

        # Build full command
        full_command = self._build_command(command, project_name)

        logger.info(f"Executing command {command_id}: {full_command}")

        # Start command execution in thread
        thread = threading.Thread(
            target=self._execute_command_thread,
            args=(command_id, full_command, project_name, working_directory),
            daemon=True,
        )
        thread.start()

        return command_id

    def _detect_project_context(self, command: str, working_directory: str | None) -> str:
        """
        Detect project context from command or working directory.
        """
        # Check if command specifies a project
        if command.startswith("atoms"):
            return "atoms"
        if command.startswith("zen"):
            return "zen"
        if command.startswith("byteport"):
            return "byteport"

        # Check working directory for project indicators
        if working_directory:
            wd_path = Path(working_directory)
            if "atoms" in wd_path.name.lower():
                return "atoms"
            if "zen" in wd_path.name.lower():
                return "zen"
            if "byteport" in wd_path.name.lower():
                return "byteport"

        return "global"

    def _build_command(self, command: str, project_name: str) -> list[str]:
        """
        Build the full command with pheno-cli prefix.
        """
        # Split command into parts
        parts = command.split()

        # Add pheno-cli prefix if not already present
        if not parts[0].startswith("pheno"):
            parts.insert(0, self.pheno_cli_path)

        return parts

    def _execute_command_thread(
        self,
        command_id: str,
        command: list[str],
        project_name: str,
        working_directory: str | None,
    ) -> None:
        """
        Execute command in a separate thread.
        """
        import time

        start_time = time.time()

        try:
            # Start process
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=working_directory,
                bufsize=1,
                universal_newlines=True,
            )

            self.running_commands[command_id] = process

            # Stream output
            stdout_lines = []
            stderr_lines = []

            # Read stdout
            for line in iter(process.stdout.readline, ""):
                if line:
                    stdout_lines.append(line.rstrip())
                    self._emit_output(command_id, "stdout", line.rstrip())

            # Read stderr
            for line in iter(process.stderr.readline, ""):
                if line:
                    stderr_lines.append(line.rstrip())
                    self._emit_output(command_id, "stderr", line.rstrip())

            # Wait for completion
            exit_code = process.wait()
            end_time = time.time()

            # Create result
            result = CommandResult(
                command_id=command_id,
                command=" ".join(command),
                project_name=project_name,
                exit_code=exit_code,
                stdout="\n".join(stdout_lines),
                stderr="\n".join(stderr_lines),
                start_time=start_time,
                end_time=end_time,
                success=exit_code == 0,
            )

            self.command_results[command_id] = result
            self.running_commands.pop(command_id, None)

            # Emit completion event
            self._emit_output(
                command_id, "complete", f"Command completed with exit code {exit_code}",
            )

            logger.info(
                f"Command {command_id} completed: exit_code={exit_code}, success={result.success}",
            )

        except Exception as e:
            end_time = time.time()
            error_msg = f"Command execution failed: {e}"

            result = CommandResult(
                command_id=command_id,
                command=" ".join(command),
                project_name=project_name,
                exit_code=-1,
                stdout="",
                stderr=error_msg,
                start_time=start_time,
                end_time=end_time,
                success=False,
            )

            self.command_results[command_id] = result
            self.running_commands.pop(command_id, None)

            self._emit_output(command_id, "error", error_msg)
            logger.exception(f"Command {command_id} failed: {e}")

    def get_command_result(self, command_id: str) -> CommandResult | None:
        """
        Get result for a completed command.
        """
        return self.command_results.get(command_id)

    def get_running_commands(self) -> list[str]:
        """
        Get list of currently running command IDs.
        """
        return list(self.running_commands.keys())

    def cancel_command(self, command_id: str) -> bool:
        """
        Cancel a running command.
        """
        if command_id in self.running_commands:
            process = self.running_commands[command_id]
            try:
                process.terminate()
                self.running_commands.pop(command_id, None)
                logger.info(f"Cancelled command {command_id}")
                return True
            except Exception as e:
                logger.exception(f"Failed to cancel command {command_id}: {e}")
                return False
        return False

    def get_command_history(self, limit: int = 50) -> list[CommandResult]:
        """
        Get recent command history.
        """
        results = list(self.command_results.values())
        results.sort(key=lambda x: x.start_time, reverse=True)
        return results[:limit]


class CommandRouter:
    """Routes commands to appropriate handlers and manages command execution.

    Features:
    - Command parsing and validation
    - Project-specific command routing
    - Command aliases and shortcuts
    - Command completion suggestions
    """

    def __init__(self, cli_bridge: CLIBridge):
        """
        Initialize command router.
        """
        self.cli_bridge = cli_bridge
        self.command_aliases: dict[str, str] = {
            "start": "start",
            "stop": "stop",
            "restart": "restart",
            "status": "status",
            "logs": "logs",
            "dev": "dev",
            "build": "build",
            "deploy": "deploy",
        }

        # Project-specific commands
        self.project_commands = {
            "atoms": ["start", "stop", "restart", "status", "logs", "dev", "build", "deploy"],
            "zen": ["start", "stop", "restart", "status", "logs", "dev", "build", "deploy"],
            "byteport": ["start", "stop", "restart", "status", "logs", "dev", "build", "deploy"],
        }

        logger.info("Command router initialized")

    def route_command(self, command_text: str) -> str | None:
        """
        Route a command and return command ID if successful.
        """
        if not command_text.strip():
            return None

        # Parse command
        parts = command_text.strip().split()
        if not parts:
            return None

        # Handle special commands
        if parts[0].lower() in ["help", "h", "?"]:
            return self._handle_help_command()
        if parts[0].lower() in ["history", "hist"]:
            return self._handle_history_command()
        if parts[0].lower() in ["clear", "cls"]:
            return self._handle_clear_command()

        # Route to CLI bridge
        try:
            return self.cli_bridge.execute_command(command_text)
        except Exception as e:
            logger.exception(f"Failed to route command '{command_text}': {e}")
            return None

    def _handle_help_command(self) -> str:
        """
        Handle help command.
        """
        help_text = """
Pheno Control Center - Available Commands:

Project Commands:
  atoms <command>     - Execute atoms project command
  zen <command>       - Execute zen project command
  byteport <command>  - Execute byteport project command

General Commands:
  help, h, ?          - Show this help
  history, hist       - Show command history
  clear, cls          - Clear screen
  status              - Show global status
  quit, exit, q       - Exit application

Project-specific Commands:
  start               - Start the project
  stop                - Stop the project
  restart             - Restart the project
  status              - Show project status
  logs                - Show project logs
  dev                 - Start development mode
  build               - Build the project
  deploy              - Deploy the project

Examples:
  atoms start         - Start atoms project
  zen logs            - Show zen project logs
  status              - Show global status
        """

        # Emit help text as output
        for line in help_text.strip().split("\n"):
            self.cli_bridge._emit_output("help", "info", line)

        return "help"

    def _handle_history_command(self) -> str:
        """
        Handle history command.
        """
        history = self.cli_bridge.get_command_history(20)

        if not history:
            self.cli_bridge._emit_output("history", "info", "No command history available")
            return "history"

        self.cli_bridge._emit_output("history", "info", "Recent Commands:")
        for i, result in enumerate(history, 1):
            status = "✅" if result.success else "❌"
            duration = result.end_time - result.start_time
            self.cli_bridge._emit_output(
                "history", "info", f"  {i:2d}. {status} {result.command} ({duration:.1f}s)",
            )

        return "history"

    def _handle_clear_command(self) -> str:
        """
        Handle clear command.
        """
        # This would need to be handled by the TUI component
        self.cli_bridge._emit_output("clear", "info", "Screen cleared")
        return "clear"

    def get_command_suggestions(self, partial_command: str) -> list[str]:
        """
        Get command completion suggestions.
        """
        if not partial_command:
            return []

        suggestions = []
        parts = partial_command.split()

        if len(parts) == 1:
            # First part - suggest projects or general commands
            project_names = list(self.project_commands.keys())
            general_commands = ["help", "history", "clear", "status", "quit"]
            suggestions.extend(project_names + general_commands)
        elif len(parts) == 2:
            # Second part - suggest project-specific commands
            project = parts[0].lower()
            if project in self.project_commands:
                suggestions.extend(self.project_commands[project])

        # Filter suggestions based on partial input
        last_part = parts[-1].lower()
        suggestions = [s for s in suggestions if s.lower().startswith(last_part)]

        return suggestions[:10]  # Limit to 10 suggestions

    def validate_command(self, command_text: str) -> tuple[bool, str]:
        """
        Validate a command and return (is_valid, error_message).
        """
        if not command_text.strip():
            return False, "Empty command"

        parts = command_text.strip().split()
        if not parts:
            return False, "Invalid command format"

        # Check if it's a general command
        if parts[0].lower() in ["help", "history", "clear", "status", "quit", "exit"]:
            return True, ""

        # Check if it's a project command
        if len(parts) >= 2:
            project = parts[0].lower()
            command = parts[1].lower()

            if project in self.project_commands:
                if command in self.project_commands[project]:
                    return True, ""
                return False, f"Unknown command '{command}' for project '{project}'"
            return False, f"Unknown project '{project}'"

        return False, "Incomplete command"


class CommandExecutor:
    """High-level command executor that combines CLI bridge and router.

    Provides a simple interface for executing commands with automatic routing,
    validation, and result handling.
    """

    def __init__(self, cli_bridge: CLIBridge | None = None):
        """
        Initialize command executor.
        """
        self.cli_bridge = cli_bridge or CLIBridge()
        self.router = CommandRouter(self.cli_bridge)

        logger.info("Command executor initialized")

    def execute(self, command: str) -> str | None:
        """
        Execute a command and return command ID.
        """
        # Validate command first
        is_valid, error_msg = self.router.validate_command(command)
        if not is_valid:
            logger.warning(f"Invalid command '{command}': {error_msg}")
            # Still emit the error as output
            self.cli_bridge._emit_output("validation", "error", f"Error: {error_msg}")
            return None

        # Route and execute
        return self.router.route_command(command)

    def get_suggestions(self, partial_command: str) -> list[str]:
        """
        Get command completion suggestions.
        """
        return self.router.get_command_suggestions(partial_command)

    def get_result(self, command_id: str) -> CommandResult | None:
        """
        Get result for a command.
        """
        return self.cli_bridge.get_command_result(command_id)

    def cancel(self, command_id: str) -> bool:
        """
        Cancel a running command.
        """
        return self.cli_bridge.cancel_command(command_id)

    def get_history(self, limit: int = 50) -> list[CommandResult]:
        """
        Get command history.
        """
        return self.cli_bridge.get_command_history(limit)
