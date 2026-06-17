"""
Base process wrapper class.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import subprocess


class BaseProcess(ABC):
    """Abstract base class for process wrappers.

    Provides process lifecycle management with health checking and auto-restart
    capabilities.
    """

    def __init__(
        self,
        name: str,
        command: str,
        *,
        port: int | None = None,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        auto_restart: bool = False,
        max_restarts: int = 3,
    ):
        """Initialize process wrapper.

        Args:
            name: Process name
            command: Command to execute
            port: Port number (optional)
            cwd: Working directory
            env: Environment variables
            auto_restart: Enable auto-restart on failure
            max_restarts: Maximum restart attempts
        """
        self.name = name
        self.command = command
        self.port = port
        self.cwd = cwd
        self.env = env
        self.auto_restart = auto_restart
        self.max_restarts = max_restarts
        self.restart_count = 0
        self.process: subprocess.Popen | None = None

    @abstractmethod
    def start(self):
        """Start the process.

        Implementation should:
        1. Start subprocess
        2. Store process handle
        3. Setup monitoring
        """

    @abstractmethod
    def stop(self):
        """Stop the process gracefully.

        Implementation should:
        1. Send SIGTERM
        2. Wait for graceful shutdown
        3. Force kill if necessary
        """

    @abstractmethod
    def restart(self):
        """Restart the process.

        Implementation should:
        1. Stop existing process
        2. Reset state
        3. Start new process
        """

    @abstractmethod
    def is_running(self) -> bool:
        """Check if process is running.

        Returns:
            True if process is alive
        """

    @abstractmethod
    def get_status(self) -> dict[str, Any]:
        """Get process status.

        Returns:
            Status dictionary with process information
        """

    def health_check(self) -> bool:
        """Check process health.

        Default implementation checks if process is running.
        Override for custom health checks.

        Returns:
            True if healthy
        """
        return self.is_running()

    def handle_failure(self):
        """Handle process failure.

        Implements auto-restart logic if enabled.
        """
        if self.auto_restart and self.restart_count < self.max_restarts:
            self.restart_count += 1
            print(
                f"♻️  Auto-restarting {self.name} (attempt {self.restart_count}/{self.max_restarts})",
            )
            self.restart()
        else:
            print(f"❌ {self.name} failed (max restarts reached)")
