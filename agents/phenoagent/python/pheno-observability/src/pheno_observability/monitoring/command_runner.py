"""Command Runner and Executor.

Unified command execution system that consolidates functionality from infra/monitoring,
MCP QA, and observability stacks.
"""

from __future__ import annotations

import asyncio
import shlex
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from ..logging import get_logger

logger = get_logger(__name__)


@dataclass
class CommandResult:
    """
    Result of a command execution.
    """

    command_id: str
    command: str
    return_code: int
    stdout: str = ""
    stderr: str = ""
    duration: float = 0.0
    started_at: float = field(default_factory=time.time)
    completed_at: float = field(default_factory=time.time)
    success: bool = True

    def __post_init__(self):
        """
        Set success based on return code.
        """
        self.success = self.return_code == 0


@dataclass
class CommandConfig:
    """
    Configuration for command execution.
    """

    timeout: float = 30.0
    cwd: str | None = None
    env: dict[str, str] | None = None
    shell: bool = False
    capture_output: bool = True
    check: bool = False  # Raise exception on non-zero return code


class CommandExecutor:
    """Executes commands and manages their lifecycle.

    Consolidates command execution from infra/monitoring, MCP QA, and observability
    stacks into a unified interface.
    """

    def __init__(self, max_concurrent: int = 10):
        """Initialize command executor.

        Args:
            max_concurrent: Maximum number of concurrent commands
        """
        self.max_concurrent = max_concurrent
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

        # Command tracking
        self._running_commands: dict[str, asyncio.Task] = {}
        self._command_history: list[CommandResult] = []
        self._max_history = 1000

        # State
        self._running = False
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def start(self) -> None:
        """
        Start command executor.
        """
        if self._running:
            self.logger.warning("Command executor already started")
            return

        self._running = True
        self.logger.info("Started command executor")

    async def stop(self) -> None:
        """
        Stop command executor and cancel running commands.
        """
        if not self._running:
            return

        self._running = False

        # Cancel all running commands
        for command_id, task in self._running_commands.items():
            task.cancel()
            self.logger.info(f"Cancelled command: {command_id}")

        # Wait for tasks to complete
        if self._running_commands:
            await asyncio.gather(*self._running_commands.values(), return_exceptions=True)

        self._running_commands.clear()
        self.logger.info("Stopped command executor")

    async def execute(
        self,
        command: str | list[str],
        config: CommandConfig | None = None,
        command_id: str | None = None,
    ) -> CommandResult:
        """Execute a command.

        Args:
            command: Command to execute (string or list)
            config: Command configuration
            command_id: Optional command ID

        Returns:
            Command execution result
        """
        if not self._running:
            raise RuntimeError("Command executor not started")

        command_id = command_id or str(uuid4())
        config = config or CommandConfig()

        # Convert command to list if it's a string
        if isinstance(command, str):
            cmd_list = command if config.shell else shlex.split(command)
        else:
            cmd_list = command

        self.logger.info(f"Executing command: {command_id}")

        # Acquire semaphore
        async with self._semaphore:
            return await self._execute_command(command_id, cmd_list, config)

    async def _execute_command(
        self,
        command_id: str,
        command: str | list[str],
        config: CommandConfig,
    ) -> CommandResult:
        """
        Execute a single command.
        """
        start_time = time.time()

        try:
            process = await self._create_subprocess(command, config)
            return_code = await self._wait_for_completion(process, command_id, config)
            stdout, stderr = await self._capture_output(process, config)
            result = self._create_command_result(
                command_id, command, return_code, stdout, stderr, start_time,
            )

            self._validate_result(result, config)
            self._finalize_command_execution(command_id, result)

            return result

        except Exception as e:
            return self._handle_command_error(command_id, command, e, start_time)

    async def _create_subprocess(
        self, command: str | list[str], config: CommandConfig,
    ) -> asyncio.subprocess.Process:
        """
        Create and start the subprocess.
        """
        kwargs = self._build_subprocess_kwargs(command, config)

        if config.shell:
            return await asyncio.create_subprocess_shell(command, **kwargs)
        return await asyncio.create_subprocess_exec(*command, **kwargs)

    def _build_subprocess_kwargs(
        self, command: str | list[str], config: CommandConfig,
    ) -> dict[str, Any]:
        """
        Build subprocess keyword arguments.
        """
        return {
            "cwd": config.cwd,
            "env": config.env,
            "capture_output": config.capture_output,
            "text": True,
        }

    async def _wait_for_completion(
        self, process: asyncio.subprocess.Process, command_id: str, config: CommandConfig,
    ) -> int:
        """
        Wait for process completion with timeout handling.
        """
        # Track running command
        self._running_commands[command_id] = asyncio.create_task(
            self._wait_for_process(process, command_id),
        )

        try:
            return await asyncio.wait_for(process.wait(), timeout=config.timeout)
        except TimeoutError:
            return await self._handle_timeout(process, command_id, config)

    async def _handle_timeout(
        self, process: asyncio.subprocess.Process, command_id: str, config: CommandConfig,
    ) -> int:
        """
        Handle command timeout.
        """
        process.kill()
        await process.wait()
        self.logger.warning(f"Command {command_id} timed out after {config.timeout}s")
        return -1

    async def _capture_output(
        self, process: asyncio.subprocess.Process, config: CommandConfig,
    ) -> tuple[str, str]:
        """
        Capture process output.
        """
        if not config.capture_output:
            return "", ""

        stdout = process.stdout.read() if process.stdout else ""
        stderr = process.stderr.read() if process.stderr else ""
        return stdout, stderr

    def _create_command_result(
        self,
        command_id: str,
        command: str | list[str],
        return_code: int,
        stdout: str,
        stderr: str,
        start_time: float,
    ) -> CommandResult:
        """
        Create a CommandResult object.
        """
        return CommandResult(
            command_id=command_id,
            command=str(command),
            return_code=return_code,
            stdout=stdout,
            stderr=stderr,
            duration=time.time() - start_time,
            started_at=start_time,
            completed_at=time.time(),
        )

    def _validate_result(self, result: CommandResult, config: CommandConfig) -> None:
        """
        Validate command result and raise exception if needed.
        """
        if config.check and not result.success:
            raise subprocess.CalledProcessError(
                result.return_code, result.command, result.stdout, result.stderr,
            )

    def _finalize_command_execution(self, command_id: str, result: CommandResult) -> None:
        """
        Finalize command execution by updating state.
        """
        self._add_to_history(result)
        self._running_commands.pop(command_id, None)
        self.logger.info(f"Command {command_id} completed with return code {result.return_code}")

    def _handle_command_error(
        self, command_id: str, command: str | list[str], error: Exception, start_time: float,
    ) -> CommandResult:
        """
        Handle command execution errors.
        """
        result = CommandResult(
            command_id=command_id,
            command=str(command),
            return_code=-1,
            stderr=str(error),
            duration=time.time() - start_time,
            started_at=start_time,
            completed_at=time.time(),
        )

        self._add_to_history(result)
        self._running_commands.pop(command_id, None)
        self.logger.error(f"Command {command_id} failed: {error}")
        return result

    async def _wait_for_process(self, process: asyncio.subprocess.Process, command_id: str) -> None:
        """
        Wait for a process to complete.
        """
        try:
            await process.wait()
        except asyncio.CancelledError:
            process.kill()
            await process.wait()
            self.logger.info(f"Command {command_id} was cancelled")

    def _add_to_history(self, result: CommandResult) -> None:
        """
        Add result to history, maintaining max size.
        """
        self._command_history.append(result)
        if len(self._command_history) > self._max_history:
            self._command_history = self._command_history[-self._max_history :]

    def get_running_commands(self) -> list[str]:
        """
        Get list of running command IDs.
        """
        return list(self._running_commands.keys())

    def get_command_result(self, command_id: str) -> CommandResult | None:
        """
        Get result for a specific command.
        """
        for result in self._command_history:
            if result.command_id == command_id:
                return result
        return None

    def get_command_history(self, limit: int | None = None) -> list[CommandResult]:
        """
        Get command execution history.
        """
        if limit:
            return self._command_history[-limit:]
        return self._command_history.copy()

    def get_successful_commands(self) -> list[CommandResult]:
        """
        Get successful command results.
        """
        return [result for result in self._command_history if result.success]

    def get_failed_commands(self) -> list[CommandResult]:
        """
        Get failed command results.
        """
        return [result for result in self._command_history if not result.success]

    def clear_history(self) -> None:
        """
        Clear command history.
        """
        self._command_history.clear()
        self.logger.info("Cleared command history")

    async def cancel_command(self, command_id: str) -> bool:
        """
        Cancel a running command.
        """
        task = self._running_commands.get(command_id)
        if task:
            task.cancel()
            self._running_commands.pop(command_id, None)
            self.logger.info(f"Cancelled command: {command_id}")
            return True
        return False

    async def health_check(self) -> dict[str, Any]:
        """
        Check command executor health.
        """
        return {
            "healthy": True,
            "running": self._running,
            "running_commands": len(self._running_commands),
            "total_history": len(self._command_history),
            "max_concurrent": self.max_concurrent,
            "available_slots": self._semaphore._value,
        }


class CommandRunner:
    """High-level command runner with monitoring and scheduling.

    Provides a higher-level interface for command execution with monitoring, scheduling,
    and result tracking.
    """

    def __init__(self, executor: CommandExecutor | None = None):
        """Initialize command runner.

        Args:
            executor: Command executor instance
        """
        self.executor = executor or CommandExecutor()
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

        # Scheduled commands
        self._scheduled_commands: dict[str, asyncio.Task] = {}
        self._running = False

    async def start(self) -> None:
        """
        Start command runner.
        """
        if self._running:
            self.logger.warning("Command runner already started")
            return

        await self.executor.start()
        self._running = True
        self.logger.info("Started command runner")

    async def stop(self) -> None:
        """
        Stop command runner.
        """
        if not self._running:
            return

        # Cancel scheduled commands
        for command_id, task in self._scheduled_commands.items():
            task.cancel()
            self.logger.info(f"Cancelled scheduled command: {command_id}")

        if self._scheduled_commands:
            await asyncio.gather(*self._scheduled_commands.values(), return_exceptions=True)

        await self.executor.stop()
        self._running = False
        self.logger.info("Stopped command runner")

    async def run(
        self,
        command: str | list[str],
        config: CommandConfig | None = None,
        command_id: str | None = None,
    ) -> CommandResult:
        """
        Run a command immediately.
        """
        return await self.executor.execute(command, config, command_id)

    async def schedule(
        self,
        command: str | list[str],
        delay: float,
        config: CommandConfig | None = None,
        command_id: str | None = None,
    ) -> str:
        """Schedule a command to run after a delay.

        Args:
            command: Command to execute
            delay: Delay in seconds
            config: Command configuration
            command_id: Optional command ID

        Returns:
            Command ID
        """
        command_id = command_id or str(uuid4())

        async def _delayed_execution():
            await asyncio.sleep(delay)
            await self.executor.execute(command, config, command_id)
            self._scheduled_commands.pop(command_id, None)

        task = asyncio.create_task(_delayed_execution())
        self._scheduled_commands[command_id] = task

        self.logger.info(f"Scheduled command {command_id} to run in {delay}s")
        return command_id

    async def cancel_scheduled(self, command_id: str) -> bool:
        """
        Cancel a scheduled command.
        """
        task = self._scheduled_commands.get(command_id)
        if task:
            task.cancel()
            self._scheduled_commands.pop(command_id, None)
            self.logger.info(f"Cancelled scheduled command: {command_id}")
            return True
        return False

    def get_scheduled_commands(self) -> list[str]:
        """
        Get list of scheduled command IDs.
        """
        return list(self._scheduled_commands.keys())

    async def health_check(self) -> dict[str, Any]:
        """
        Check command runner health.
        """
        executor_health = await self.executor.health_check()

        return {
            "healthy": True,
            "running": self._running,
            "scheduled_commands": len(self._scheduled_commands),
            "executor": executor_health,
        }
