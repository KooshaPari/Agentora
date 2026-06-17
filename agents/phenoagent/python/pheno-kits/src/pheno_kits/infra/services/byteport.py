"""BytePort Service Definitions for KInfra.

Pre-configured service definitions for BytePort infrastructure. Handles API backend (Go)
and Frontend (Next.js) with proper environment management.
"""

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from ..service_manager import ServiceConfig


@dataclass
class BytePortConfig:
    """
    Configuration for BytePort services.
    """

    root_dir: Path
    dev_mode: bool = False
    local_mode: bool = False
    api_preferred_port: int = 8000
    frontend_preferred_port: int = 8001


def _parse_env_file(path: Path) -> dict[str, str]:
    """
    Parse .env file into dict.
    """
    env_vars = {}
    if not path.exists():
        return env_vars

    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    # Remove quotes if present
                    value = value.strip().strip('"').strip("'")
                    env_vars[key.strip()] = value
    except Exception:
        pass

    return env_vars


def _load_env_cascade(root_dir: Path, service_env_file: Path | None = None) -> dict[str, str]:
    """
    Load environment variables with cascade:
    1. System environment
    2. BytePort root .env
    3. Service-specific .env
    """
    env = os.environ.copy()

    # Load root .env if exists
    root_env = root_dir / ".env"
    if root_env.exists():
        env.update(_parse_env_file(root_env))

    # Load service-specific .env
    if service_env_file and service_env_file.exists():
        env.update(_parse_env_file(service_env_file))

    return env


def _check_air_installed() -> bool:
    """
    Check if Air (Go live reload) is installed.
    """
    return shutil.which("air") is not None


def get_api_service(config: BytePortConfig) -> ServiceConfig:
    """
    Get API backend service configuration.
    """
    backend_dir = config.root_dir / "backend" / "byteport"
    env_file = config.root_dir / "backend" / ".env"

    # Base command
    command = ["go", "run", "*.go"]

    # Use air for dev mode if available
    if config.dev_mode and _check_air_installed():
        command = ["air"]

    # Load environment
    env = _load_env_cascade(config.root_dir, env_file)

    return ServiceConfig(
        name="api",
        command=command,
        cwd=backend_dir,
        env=env,
        preferred_port=config.api_preferred_port,
        enable_tunnel=True,
        tunnel_domain="byte.kooshapari.com",
        restart_on_failure=True,
        health_check_url=(
            f"http://localhost:{config.api_preferred_port}/health" if config.local_mode else None
        ),
        # Fallback configuration
        enable_fallback=True,
        fallback_page="loading",
        fallback_refresh_interval=3,
        fallback_message="API server is starting up..." if config.dev_mode else None,
        path_prefix="/api",
    )


def get_frontend_service(config: BytePortConfig) -> ServiceConfig:
    """
    Get frontend Next.js service configuration.
    """
    frontend_dir = Path("/Users/kooshapari/temp-PRODVERCEL/Rust/webApp/byte_port/frontend/web-next")
    env_file = frontend_dir / ".env.local"

    # Determine command based on mode
    if config.local_mode:
        command = ["npm", "run", "dev:local"]
    elif config.dev_mode:
        command = ["npm", "run", "dev"]
    else:
        command = ["npm", "run", "start"]

    # Load environment
    env = _load_env_cascade(config.root_dir, env_file)

    # Set local mode flag if needed
    if config.local_mode:
        env["NEXT_PUBLIC_USE_LOCAL"] = "true"

    return ServiceConfig(
        name="frontend",
        command=command,
        cwd=frontend_dir,
        env=env,
        preferred_port=config.frontend_preferred_port,
        enable_tunnel=True,
        tunnel_domain="byte.kooshapari.com",
        restart_on_failure=True,
        watch_paths=(
            [frontend_dir / "app", frontend_dir / "components", frontend_dir / "lib"]
            if config.dev_mode
            else None
        ),
        watch_patterns=["*.ts", "*.tsx", "*.js", "*.jsx"] if config.dev_mode else None,
        # Fallback configuration
        enable_fallback=True,
        fallback_page="loading",
        fallback_refresh_interval=5,
        fallback_message="Frontend is building..." if config.dev_mode else None,
        path_prefix="/",
    )


def get_byteport_services(
    root_dir: Path,
    dev_mode: bool = False,
    local_mode: bool = False,
    api_port: int = 8000,
    frontend_port: int = 8001,
) -> list[ServiceConfig]:
    """Get all BytePort service configurations.

    Args:
        root_dir: Root directory of BytePort project
        dev_mode: Enable development mode with live reload
        local_mode: Use localhost ports instead of production URLs
        api_port: Preferred port for API (default: 8000)
        frontend_port: Preferred port for frontend (default: 8001)

    Returns:
        List of ServiceConfig objects ready for KInfra ServiceManager
    """
    config = BytePortConfig(
        root_dir=root_dir,
        dev_mode=dev_mode,
        local_mode=local_mode,
        api_preferred_port=api_port,
        frontend_preferred_port=frontend_port,
    )

    services = []

    # Add API service
    api_service = get_api_service(config)
    services.append(api_service)

    # Add frontend service if directory exists
    frontend_dir = Path("/Users/kooshapari/temp-PRODVERCEL/Rust/webApp/byte_port/frontend/web-next")
    if frontend_dir.exists():
        frontend_service = get_frontend_service(config)
        services.append(frontend_service)

    return services
