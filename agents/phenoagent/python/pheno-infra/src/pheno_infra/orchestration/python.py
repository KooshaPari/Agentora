"""
Python service builder for KInfra orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pheno.infra.service_manager import ServiceConfig


@dataclass
class PythonServiceOptions:
    """
    Options for building a Python service configuration.
    """

    name: str
    """
    Service name (used for process tracking, port allocation)
    """

    module: str
    """
    Python module to run (e.g., 'server' for `python -m server`)
    """

    port: int
    """
    Port number for the service.
    """

    project_root: Path | None = None
    """
    Project root directory (defaults to current directory)
    """

    env_files: list[Path] = field(default_factory=list)
    """
    Environment files to load (.env files)
    """

    extra_env: dict[str, str] = field(default_factory=dict)
    """
    Additional environment variables.
    """

    health_check_url: str | None = None
    """Health check URL (e.g., 'http://localhost:8080/health')"""

    enable_tunnel: bool = True
    """
    Enable CloudFlare tunnel for this service.
    """

    tunnel_domain: str | None = None
    """
    CloudFlare tunnel domain (e.g., 'myapp.example.com')
    """

    python_path: str | None = None
    """
    Custom Python interpreter path (defaults to 'python3')
    """

    working_dir: Path | None = None
    """
    Working directory for the service (defaults to project_root)
    """


def build_python_service(options: PythonServiceOptions) -> ServiceConfig:
    """Build a ServiceConfig for a Python module service.

    Args:
        options: Python service configuration options

    Returns:
        ServiceConfig ready for KInfra orchestration

    Example:
        >>> options = PythonServiceOptions(
        ...     name="atoms-mcp",
        ...     module="server",
        ...     port=50002,
        ...     enable_tunnel=True,
        ...     tunnel_domain="atomcp.kooshapari.com",
        ... )
        >>> service = build_python_service(options)
    """
    from pheno.config import load_env_cascade

    # Determine working directory
    working_dir = options.working_dir or options.project_root or Path.cwd()

    # Build Python command
    python_exe = options.python_path or "python3"
    command = [python_exe, "-m", options.module]

    root_dir = options.project_root or working_dir
    env_files = [Path(env_file) for env_file in options.env_files]
    env_vars = load_env_cascade(
        root_dirs=[root_dir],
        env_files=env_files or None,
    )

    # Add service-specific vars
    env_vars["PORT"] = str(options.port)
    env_vars["PYTHON_SERVICE_NAME"] = options.name

    # Add extra environment variables
    env_vars.update(options.extra_env)

    # Build ServiceConfig
    return ServiceConfig(
        name=options.name,
        command=command,
        port=options.port,
        cwd=working_dir,
        env=env_vars,
        health_check_url=options.health_check_url,
        enable_tunnel=options.enable_tunnel,
        tunnel_domain=options.tunnel_domain if options.enable_tunnel else None,
    )


__all__ = ["PythonServiceOptions", "build_python_service"]
