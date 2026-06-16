"""
Factory for creating processes.
"""

from __future__ import annotations

from typing import Any

from ..components.process_manager import ManagedProcess


class ProcessFactory:
    """
    Factory for creating process instances.
    """

    @staticmethod
    def create(name: str, command: str, **kwargs) -> ManagedProcess:
        """Create a generic process.

        Args:
            name: Process name
            command: Command to execute
            **kwargs: Additional options (port, cwd, env, auto_restart, etc.)

        Returns:
            Process instance
        """
        return ManagedProcess(name=name, command=command, **kwargs)

    @staticmethod
    def create_server(
        name: str, command: str, port: int, health_endpoint: str = "/health", **kwargs,
    ) -> ManagedProcess:
        """Create a server process with health checking.

        Args:
            name: Process name
            command: Command to execute
            port: Server port
            health_endpoint: Health check endpoint
            **kwargs: Additional options

        Returns:
            Process instance with health checking enabled
        """
        process = ManagedProcess(name=name, command=command, port=port, **kwargs)

        # Attach health check metadata
        process.metadata["health_endpoint"] = health_endpoint
        process.metadata["is_server"] = True

        return process

    @staticmethod
    def create_worker(
        name: str, command: str, auto_restart: bool = True, max_restarts: int = 5, **kwargs,
    ) -> ManagedProcess:
        """Create a worker process with auto-restart.

        Args:
            name: Process name
            command: Command to execute
            auto_restart: Enable auto-restart on failure
            max_restarts: Maximum restart attempts
            **kwargs: Additional options

        Returns:
            Process instance with auto-restart enabled
        """
        return ManagedProcess(
            name=name,
            command=command,
            auto_restart=auto_restart,
            max_restarts=max_restarts,
            **kwargs,
        )

    @staticmethod
    def create_batch(configs: list[dict[str, Any]]) -> list[ManagedProcess]:
        """Create multiple processes from configs.

        Args:
            configs: List of process configurations

        Returns:
            List of process instances
        """
        processes = []

        for config in configs:
            name = config.pop("name")
            command = config.pop("command")
            process_type = config.pop("type", "generic")

            if process_type == "server":
                port = config.pop("port")
                process = ProcessFactory.create_server(name, command, port, **config)
            elif process_type == "worker":
                process = ProcessFactory.create_worker(name, command, **config)
            else:
                process = ProcessFactory.create(name, command, **config)

            processes.append(process)

        return processes
