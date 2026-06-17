"""Command execution and process management for Pheno Control Center.

Provides CLIBridge for executing CLI commands with streaming output capture and process
lifecycle management.
"""

import logging
import os
import shlex
import subprocess
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    """
    Result of command execution.
    """

    command: list[str]
    """
    The executed command.
    """

    exit_code: int | None = None
    """
    Process exit code (None if still running)
    """

    stdout_lines: list[str] = field(default_factory=list)
    """
    Captured stdout lines.
    """

    stderr_lines: list[str] = field(default_factory=list)
    """
    Captured stderr lines.
    """

    start_time: float = field(default_factory=time.time)
    """
    Command start timestamp.
    """

    end_time: float | None = None
    """
    Command end timestamp.
    """

    project_name: str | None = None
    """
    Associated project name.
    """

    @property
    def duration(self) -> float | None:
        """
        Command duration in seconds.
        """
        if self.end_time:
            return self.end_time - self.start_time
        return None

    @property
    def is_running(self) -> bool:
        """
        Whether command is still running.
        """
        return self.exit_code is None and self.end_time is None

    @property
    def success(self) -> bool:
        """
        Whether command completed successfully.
        """
        return self.exit_code == 0


class CLIBridge:
    """Bridge for executing CLI commands with streaming output capture.

    Provides:
    - Real-time output streaming
    - Environment context switching
    - Command history and autocomplete data
    - Process lifecycle management
    """

    def __init__(self, max_history: int = 1000, max_output_lines: int = 10000):
        """
        Initialize CLI bridge.
        """
        self.max_history = max_history
        self.max_output_lines = max_output_lines

        # Command history
        self.command_history: deque = deque(maxlen=max_history)

        # Active processes by command ID
        self.active_processes: dict[str, subprocess.Popen] = {}

        # Output streaming callbacks
        self.output_callbacks: list[Callable[[str, str, str], None]] = []

        # Command results cache
        self.results: dict[str, CommandResult] = {}

        # Background thread for process monitoring
        self._monitor_thread = None
        self._shutdown = False

        logger.info("CLI Bridge initialized")

    def add_output_callback(self, callback: Callable[[str, str, str], None]) -> None:
        """Add callback for streaming output.

        Args:
            callback: Function called with (command_id, stream_type, line)
                     where stream_type is 'stdout' or 'stderr'
        """
        self.output_callbacks.append(callback)

    def execute_command(
        self,
        command: str | list[str],
        project_name: str | None = None,
        working_dir: Path | None = None,
        env_vars: dict[str, str] | None = None,
        stream_output: bool = True,
        timeout: float | None = None,
    ) -> str:
        """Execute a command and return command ID for tracking.

        Args:
            command: Command to execute (string or list)
            project_name: Associated project name
            working_dir: Working directory for command
            env_vars: Additional environment variables
            stream_output: Whether to stream output in real-time
            timeout: Command timeout in seconds

        Returns:
            Command ID for tracking execution
        """
        # Parse command
        cmd_parts = shlex.split(command) if isinstance(command, str) else command

        # Generate command ID
        command_id = f"{project_name or 'global'}_{int(time.time() * 1000)}"

        # Prepare environment
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)

        # Create result object
        result = CommandResult(
            command=cmd_parts,
            project_name=project_name,
        )
        self.results[command_id] = result

        try:
            # Start process
            process = subprocess.Popen(
                cmd_parts,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=working_dir,
                env=env,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            self.active_processes[command_id] = process

            # Add to history
            self.command_history.append(
                {
                    "command": cmd_parts,
                    "project": project_name,
                    "timestamp": time.time(),
                    "command_id": command_id,
                },
            )

            if stream_output:
                # Start streaming threads
                stdout_thread = threading.Thread(
                    target=self._stream_output,
                    args=(command_id, process.stdout, "stdout"),
                    daemon=True,
                )
                stderr_thread = threading.Thread(
                    target=self._stream_output,
                    args=(command_id, process.stderr, "stderr"),
                    daemon=True,
                )

                stdout_thread.start()
                stderr_thread.start()

            # Start monitoring thread if not already running
            if self._monitor_thread is None or not self._monitor_thread.is_alive():
                self._monitor_thread = threading.Thread(target=self._monitor_processes, daemon=True)
                self._monitor_thread.start()

            logger.info(f"Started command {command_id}: {' '.join(cmd_parts)}")
            return command_id

        except Exception as e:
            logger.exception(f"Failed to start command {command_id}: {e}")
            result.exit_code = -1
            result.end_time = time.time()
            raise

    def _stream_output(self, command_id: str, stream, stream_type: str) -> None:
        """
        Stream output from a process in a background thread.
        """
        result = self.results.get(command_id)
        if not result:
            return

        try:
            self._process_stream_lines(command_id, stream, stream_type, result)
        except Exception as e:
            logger.warning(f"Output streaming error for {command_id}: {e}")
        finally:
            stream.close()

    def _process_stream_lines(self, command_id: str, stream, stream_type: str, result) -> None:
        """
        Process lines from the stream.
        """
        for line in iter(stream.readline, ""):
            if not line:
                break

            line = line.rstrip("\n")
            self._store_output_line(result, stream_type, line)
            self._notify_output_callbacks(command_id, stream_type, line)

    def _store_output_line(self, result, stream_type: str, line: str) -> None:
        """
        Store output line in the result with size management.
        """
        if stream_type == "stdout":
            result.stdout_lines.append(line)
            if len(result.stdout_lines) > self.max_output_lines:
                result.stdout_lines.pop(0)
        else:
            result.stderr_lines.append(line)
            if len(result.stderr_lines) > self.max_output_lines:
                result.stderr_lines.pop(0)

    def _notify_output_callbacks(self, command_id: str, stream_type: str, line: str) -> None:
        """
        Notify all output callbacks about the new line.
        """
        for callback in self.output_callbacks:
            try:
                callback(command_id, stream_type, line)
            except Exception as e:
                logger.warning(f"Output callback error: {e}")

    def _monitor_processes(self) -> None:
        """
        Monitor active processes for completion.
        """
        while not self._shutdown:
            completed = []

            for command_id, process in self.active_processes.items():
                if process.poll() is not None:
                    # Process completed
                    result = self.results.get(command_id)
                    if result:
                        result.exit_code = process.returncode
                        result.end_time = time.time()

                    completed.append(command_id)
                    logger.info(
                        f"Command {command_id} completed with exit code {process.returncode}",
                    )

            # Clean up completed processes
            for command_id in completed:
                self.active_processes.pop(command_id, None)

            time.sleep(0.5)

    def get_command_result(self, command_id: str) -> CommandResult | None:
        """
        Get result for a command.
        """
        return self.results.get(command_id)

    def is_command_running(self, command_id: str) -> bool:
        """
        Check if a command is still running.
        """
        return command_id in self.active_processes

    def terminate_command(self, command_id: str, timeout: float = 5.0) -> bool:
        """Terminate a running command.

        Args:
            command_id: Command to terminate
            timeout: Grace period before killing

        Returns:
            True if successfully terminated
        """
        process = self.active_processes.get(command_id)
        if not process:
            return False

        try:
            # Try graceful termination first
            process.terminate()

            # Wait for graceful exit
            try:
                process.wait(timeout=timeout)
                return True
            except subprocess.TimeoutExpired:
                # Force kill
                process.kill()
                process.wait()
                return True

        except Exception as e:
            logger.exception(f"Failed to terminate command {command_id}: {e}")
            return False
        finally:
            self.active_processes.pop(command_id, None)

            # Update result
            result = self.results.get(command_id)
            if result and result.end_time is None:
                result.exit_code = -1  # Terminated
                result.end_time = time.time()

    def get_command_history(self, project_name: str | None = None) -> list[dict[str, Any]]:
        """Get command history, optionally filtered by project.

        Args:
            project_name: Filter by project name (None for all)

        Returns:
            List of command history entries
        """
        history = list(self.command_history)

        if project_name:
            history = [h for h in history if h.get("project") == project_name]

        return history

    def get_active_commands(self) -> dict[str, dict[str, Any]]:
        """
        Get information about active commands.
        """
        active = {}

        for command_id, process in self.active_processes.items():
            result = self.results.get(command_id)
            active[command_id] = {
                "command": result.command if result else [],
                "project": result.project_name if result else None,
                "pid": process.pid,
                "start_time": result.start_time if result else None,
                "duration": time.time() - result.start_time if result else None,
            }

        return active

    def shutdown(self) -> None:
        """
        Shutdown CLI bridge and terminate all processes.
        """
        logger.info("Shutting down CLI bridge...")
        self._shutdown = True

        # Terminate all active processes
        for command_id in list(self.active_processes.keys()):
            self.terminate_command(command_id, timeout=2.0)

        # Wait for monitor thread
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5.0)


__all__ = [
    "CLIBridge",
    "CommandResult",
]
