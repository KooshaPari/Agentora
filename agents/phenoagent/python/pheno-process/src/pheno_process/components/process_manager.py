"""
Process manager component.
"""

from __future__ import annotations

import subprocess
from typing import Any

from ..base.process_base import BaseProcess


class ManagedProcess(BaseProcess):
    """
    Concrete implementation of BaseProcess.
    """

    def start(self):
        """
        Start the process.
        """
        if self.process and self.is_running():
            print(f"⚠️  Process {self.name} is already running")
            return

        try:
            import shlex

            cmd_parts = shlex.split(self.command)

            self.process = subprocess.Popen(
                cmd_parts,
                cwd=self.cwd,
                env=self.env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            print(f"✅ Started {self.name} (PID: {self.process.pid})")

        except Exception as e:
            print(f"❌ Failed to start {self.name}: {e}")
            self.handle_failure()

    def stop(self):
        """
        Stop the process gracefully.
        """
        if not self.process:
            return

        try:
            # Send SIGTERM
            self.process.terminate()

            # Wait for graceful shutdown
            try:
                self.process.wait(timeout=10)
                print(f"✅ Stopped {self.name}")
            except subprocess.TimeoutExpired:
                # Force kill
                self.process.kill()
                print(f"⚠️  Force killed {self.name}")

        except Exception as e:
            print(f"❌ Error stopping {self.name}: {e}")

        finally:
            self.process = None

    def restart(self):
        """
        Restart the process.
        """
        print(f"♻️  Restarting {self.name}...")
        self.stop()
        self.start()

    def is_running(self) -> bool:
        """
        Check if process is running.
        """
        if not self.process:
            return False

        return self.process.poll() is None

    def get_status(self) -> dict[str, Any]:
        """
        Get process status.
        """
        return {
            "name": self.name,
            "running": self.is_running(),
            "pid": self.process.pid if self.process else None,
            "port": self.port,
            "restarts": self.restart_count,
            "command": self.command,
        }


class ProcessManager:
    """
    Manages multiple processes.
    """

    def __init__(self):
        """
        Initialize process manager.
        """
        self._processes: dict[str, ManagedProcess] = {}

    def start_process(self, name: str, command: str, **kwargs) -> ManagedProcess:
        """Start a new process.

        Args:
            name: Process name
            command: Command to execute
            **kwargs: Additional process options

        Returns:
            Process instance
        """
        if name in self._processes:
            raise ValueError(f"Process {name} already exists")

        process = ManagedProcess(name=name, command=command, **kwargs)
        self._processes[name] = process
        process.start()

        return process

    def stop_process(self, name: str) -> bool:
        """Stop a process.

        Args:
            name: Process name

        Returns:
            True if stopped
        """
        if name not in self._processes:
            return False

        self._processes[name].stop()
        return True

    def restart_process(self, name: str) -> bool:
        """Restart a process.

        Args:
            name: Process name

        Returns:
            True if restarted
        """
        if name not in self._processes:
            return False

        self._processes[name].restart()
        return True

    def stop_all(self):
        """
        Stop all processes.
        """
        for process in self._processes.values():
            process.stop()

    def get_process(self, name: str) -> ManagedProcess | None:
        """Get process by name.

        Args:
            name: Process name

        Returns:
            Process or None
        """
        return self._processes.get(name)

    def get_all_status(self) -> list[dict[str, Any]]:
        """Get status of all processes.

        Returns:
            List of process statuses
        """
        return [p.get_status() for p in self._processes.values()]

    def count_running(self) -> int:
        """Count running processes.

        Returns:
            Number of running processes
        """
        return sum(1 for p in self._processes.values() if p.is_running())
