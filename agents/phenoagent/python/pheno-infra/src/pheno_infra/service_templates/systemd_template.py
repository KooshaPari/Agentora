"""
SystemD Service Template Generator - Auto-generate systemd unit files.

Generates systemd service files for managing deployments with:
- Environment variable support
- Health check configuration
- Restart policies
- Resource limits
- Logging configuration
"""

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SystemDTemplateGenerator:
    """
    Generate systemd service unit files for deployment.
    """

    @staticmethod
    def generate_service_file(
        service_name: str,
        description: str,
        exec_start: str,
        user: str = "root",
        group: str = "root",
        working_directory: str | None = None,
        environment: dict[str, str] | None = None,
        restart_policy: str = "always",
        restart_sec: int = 5,
        timeout_stop_sec: int = 30,
        type_: str = "simple",
        memory_limit: str | None = None,
        cpu_limit: str | None = None,
        dependencies: list[str] | None = None,
        wants: list[str] | None = None,
        after: list[str] | None = None,
        health_check: dict[str, Any] | None = None,
    ) -> str:
        """Generate systemd service file content.

        Args:
            service_name: Name of the service (without .service extension)
            description: Human-readable service description
            exec_start: Command to start the service
            user: User to run service as
            group: Group to run service as
            working_directory: Working directory for the service
            environment: Environment variables as dict
            restart_policy: Restart policy (no, always, on-failure, etc.)
            restart_sec: Seconds between restarts
            timeout_stop_sec: Timeout for stop operation
            type_: Service type (simple, forking, oneshot, notify, idle)
            memory_limit: Memory limit (e.g., "512M", "1G")
            cpu_limit: CPU limit (e.g., "50%", "1.5")
            dependencies: Services this depends on
            wants: Services to start together
            after: Services to start after
            health_check: Health check configuration

        Returns:
            Systemd unit file content as string
        """
        lines = [
            "[Unit]",
            f"Description={description}",
        ]

        # Add dependencies
        if after:
            lines.append(f"After={' '.join(after)}")
        if dependencies:
            lines.extend([f"Requires={dep}" for dep in dependencies])
        if wants:
            lines.extend([f"Wants={want}" for want in wants])

        # Service section
        lines.extend(
            [
                "",
                "[Service]",
                f"Type={type_}",
                f"User={user}",
                f"Group={group}",
            ],
        )

        if working_directory:
            lines.append(f"WorkingDirectory={working_directory}")

        # Environment variables
        if environment:
            for key, value in environment.items():
                # Escape special characters in environment values
                safe_value = value.replace('"', '\\"').replace("\n", "\\n")
                lines.append(f'Environment="{key}={safe_value}"')

        lines.extend(
            [
                f"ExecStart={exec_start}",
                f"Restart={restart_policy}",
                f"RestartSec={restart_sec}",
                f"TimeoutStopSec={timeout_stop_sec}",
            ],
        )

        # Resource limits
        if memory_limit:
            lines.append(f"MemoryLimit={memory_limit}")
        if cpu_limit:
            lines.append(f"CPUQuota={cpu_limit}")

        # Security hardening options (optional)
        lines.extend(
            [
                "StandardOutput=journal",
                "StandardError=journal",
                "SyslogIdentifier=" + service_name,
            ],
        )

        # Health check (if configured)
        if health_check:
            health_type = health_check.get("type", "exec")
            if health_type == "exec":
                health_cmd = health_check.get("command")
                if health_cmd:
                    lines.append(f"ExecHealthCheck={health_cmd}")

        # Install section
        lines.extend(
            [
                "",
                "[Install]",
                "WantedBy=multi-user.target",
            ],
        )

        return "\n".join(lines) + "\n"

    @staticmethod
    def generate_socket_file(
        service_name: str,
        socket_port: int,
        listen_address: str = "127.0.0.1",
        protocol: str = "tcp",
    ) -> str:
        """Generate systemd socket unit file for socket-activated services.

        Args:
            service_name: Name of the service
            socket_port: Port to listen on
            listen_address: Address to bind to
            protocol: Protocol (tcp or udp)

        Returns:
            Systemd socket unit file content
        """
        protocol.upper()

        lines = [
            "[Unit]",
            f"Description={service_name} socket",
            f"Before={service_name}.service",
            "",
            "[Socket]",
            f"ListenStream={listen_address}:{socket_port}",
            "Accept=no",
            "",
            "[Install]",
            "WantedBy=sockets.target",
        ]

        return "\n".join(lines) + "\n"

    @staticmethod
    def generate_timer_file(
        service_name: str,
        schedule: str,
        persistent: bool = True,
    ) -> str:
        """Generate systemd timer unit file for scheduled execution.

        Args:
            service_name: Name of the service
            schedule: Timer schedule (e.g., "*-*-* 02:00:00" for daily at 2am)
            persistent: Whether to run missed timers on startup

        Returns:
            Systemd timer unit file content
        """
        lines = [
            "[Unit]",
            f"Description={service_name} timer",
            f"Requires={service_name}.service",
            "",
            "[Timer]",
            f"OnCalendar={schedule}",
            f"Persistent={'yes' if persistent else 'no'}",
            "Unit=" + service_name + ".service",
            "",
            "[Install]",
            "WantedBy=timers.target",
        ]

        return "\n".join(lines) + "\n"

    @staticmethod
    def save_service_file(
        service_name: str,
        content: str,
        output_dir: str = "/etc/systemd/system",
    ) -> Path | None:
        """Save service file to systemd directory.

        Args:
            service_name: Service name
            content: File content
            output_dir: Directory to save to (default: /etc/systemd/system)

        Returns:
            Path to saved file, or None if error
        """
        try:
            output_path = Path(output_dir) / f"{service_name}.service"

            # Write file
            output_path.write_text(content)
            logger.info(f"✓ Service file saved: {output_path}")

            return output_path

        except Exception as e:
            logger.exception(f"Failed to save service file: {e}")
            return None


# Example usage functions
def example_python_service() -> str:
    """Example: Python application service."""
    return SystemDTemplateGenerator.generate_service_file(
        service_name="my-app",
        description="My Python Application",
        exec_start="/usr/bin/python3 /opt/my-app/main.py",
        user="www-data",
        group="www-data",
        working_directory="/opt/my-app",
        environment={
            "PYTHONUNBUFFERED": "1",
            "LOG_LEVEL": "INFO",
        },
        restart_policy="on-failure",
        restart_sec=10,
        memory_limit="512M",
    )


def example_docker_service() -> str:
    """Example: Docker container service."""
    return SystemDTemplateGenerator.generate_service_file(
        service_name="my-container",
        description="My Docker Container",
        exec_start="/usr/bin/docker run --rm --name my-container my-image:latest",
        user="docker",
        restart_policy="always",
        restart_sec=5,
        after=["docker.service"],
        dependencies=["docker.service"],
    )


def example_web_service() -> str:
    """Example: Web service with health checks."""
    return SystemDTemplateGenerator.generate_service_file(
        service_name="web-app",
        description="Web Application Server",
        exec_start="/usr/bin/gunicorn app:app",
        user="www-data",
        working_directory="/opt/web-app",
        environment={
            "FLASK_ENV": "production",
            "WORKERS": "4",
        },
        restart_policy="on-failure",
        timeout_stop_sec=30,
        memory_limit="1G",
        cpu_limit="50%",
        health_check={
            "type": "exec",
            "command": "/usr/bin/curl -f http://localhost:8000/health",
        },
    )
