"""
Service Templates - Common service patterns for KInfra.

Provides pre-configured templates for common service types:
- Python ASGI (FastAPI, FastMCP, Litestar, Starlette)
- Go HTTP servers
- Next.js applications
- Static sites

Usage:
    from pheno.infra.templates import PythonASGIService
    from pheno.infra.service_manager import ServiceManager

    service = PythonASGIService(
        name="my-api",
        app_path="server:app",
        port=8000
    ).to_service_config()

    manager = ServiceManager(kinfra)
    manager.register_service(service)
"""

from dataclasses import dataclass, field
from pathlib import Path

from .service_manager import ServiceConfig


@dataclass
class ServiceTemplate:
    """
    Base template for service types.
    """

    name: str
    port: int
    enable_tunnel: bool = True
    tunnel_domain: str | None = None
    env: dict[str, str] | None = field(default_factory=dict)

    def to_service_config(self) -> ServiceConfig:
        """
        Convert template to ServiceConfig.
        """
        raise NotImplementedError("Subclasses must implement to_service_config()")


@dataclass
class PythonASGIService(ServiceTemplate):
    """Template for Python ASGI applications.

    Supports: FastAPI, FastMCP, Litestar, Starlette, Quart, etc.

    Usage:
        service = PythonASGIService(
            name="zen-mcp-server",
            app_path="server:app",
            port=50002,
            workers=1,
            reload=False
        ).to_service_config()

        # Override environment variables
        service.env["MCP_BASE_PATH"] = "/mcp"
        service.tunnel_health_endpoint = "/mcp/healthz"
    """

    # All fields with defaults to avoid inheritance issues
    app_path: str = ""  # "module:app" - REQUIRED, set in __post_init__
    workers: int = 1
    reload: bool = False
    uvicorn_host: str = "0.0.0.0"
    uvicorn_log_level: str = "info"
    health_endpoint: str = "/healthz"
    cwd: Path | None = None

    def __post_init__(self):
        """
        Validate required fields.
        """
        if not self.app_path:
            raise ValueError("app_path is required for PythonASGIService")

    def to_service_config(self) -> ServiceConfig:
        """
        Generate ServiceConfig for Python ASGI service.
        """
        command = [
            "uvicorn",
            self.app_path,
            "--host",
            self.uvicorn_host,
            "--port",
            str(self.port),
            "--workers",
            str(self.workers),
            "--log-level",
            self.uvicorn_log_level,
        ]

        if self.reload:
            command.append("--reload")

        return ServiceConfig(
            name=self.name,
            command=command,
            cwd=self.cwd,
            env=self.env or {},
            preferred_port=self.port,
            enable_tunnel=self.enable_tunnel,
            tunnel_domain=self.tunnel_domain,
            health_check_url=f"http://localhost:{self.port}{self.health_endpoint}",
            tunnel_health_endpoint=self.health_endpoint,
            tunnel_ready_timeout=45,
            restart_on_failure=True,
            path_prefix="/",
        )


@dataclass
class GoHTTPService(ServiceTemplate):
    """Template for Go HTTP servers.

    Usage:
        service = GoHTTPService(
            name="api",
            module_dir=Path("backend/api"),
            port=8080,
            path_prefix="/api/v1"
        ).to_service_config()
    """

    module_dir: Path | None = None  # REQUIRED, validated in __post_init__
    build_command: list[str] | None = None
    path_prefix: str = "/"
    go_cache_dir: Path | None = None
    go_mod_cache_dir: Path | None = None
    set_go_defaults: bool = True

    def __post_init__(self):
        """
        Validate required fields.
        """
        if not self.module_dir:
            raise ValueError("module_dir is required for GoHTTPService")

    def to_service_config(self) -> ServiceConfig:
        """
        Generate ServiceConfig for Go HTTP service.
        """
        # Default to "go run ."
        command = self.build_command or ["go", "run", "."]

        # Setup Go cache directories
        env = self.env or {}
        if self.go_cache_dir:
            env["GOCACHE"] = str(self.go_cache_dir)
        if self.go_mod_cache_dir:
            env["GOMODCACHE"] = str(self.go_mod_cache_dir)

        if self.set_go_defaults:
            env.setdefault("GOPROXY", "off")
            env.setdefault("GONOSUMDB", "*")

        health_url = f"http://localhost:{self.port}"
        if self.path_prefix and self.path_prefix != "/":
            health_url += f"{self.path_prefix.rstrip('/')}/health"
        else:
            health_url += "/health"

        return ServiceConfig(
            name=self.name,
            command=command,
            cwd=self.module_dir,
            env=env,
            preferred_port=self.port,
            enable_tunnel=self.enable_tunnel,
            tunnel_domain=self.tunnel_domain,
            health_check_url=health_url,
            tunnel_health_endpoint=(
                f"{self.path_prefix.rstrip('/')}/health" if self.path_prefix != "/" else "/health"
            ),
            tunnel_ready_timeout=45,
            restart_on_failure=True,
            path_prefix=self.path_prefix,
        )


@dataclass
class NextJSService(ServiceTemplate):
    """Template for Next.js applications.

    Usage:
        service = NextJSService(
            name="frontend",
            app_dir=Path("frontend/web-next"),
            port=3000,
            dev_mode=True
        ).to_service_config()
    """

    app_dir: Path | None = None  # REQUIRED, validated in __post_init__
    dev_mode: bool = False
    local_mode: bool = False
    command_start: list[str] | None = None
    command_dev: list[str] | None = None
    command_local: list[str] | None = None
    watch_paths: list[Path] | None = None
    watch_patterns: list[str] | None = None

    def __post_init__(self):
        """
        Validate required fields.
        """
        if not self.app_dir:
            raise ValueError("app_dir is required for NextJSService")

    def to_service_config(self) -> ServiceConfig:
        """
        Generate ServiceConfig for Next.js service.
        """
        # Determine command based on mode
        if self.local_mode:
            command = self.command_local or ["pnpm", "dev:local"]
        elif self.dev_mode:
            command = self.command_dev or ["pnpm", "dev"]
        else:
            command = self.command_start or ["pnpm", "start"]

        # Setup environment
        env = self.env or {}
        if self.local_mode:
            env.setdefault("NEXT_PUBLIC_USE_LOCAL", "true")

        # Setup file watching in dev mode
        watch_paths = self.watch_paths
        watch_patterns = self.watch_patterns
        if (self.dev_mode or self.local_mode) and not watch_paths:
            watch_paths = [self.app_dir / "app", self.app_dir / "components", self.app_dir / "lib"]
        if (self.dev_mode or self.local_mode) and not watch_patterns:
            watch_patterns = ["*.ts", "*.tsx", "*.js", "*.jsx"]

        return ServiceConfig(
            name=self.name,
            command=command,
            cwd=self.app_dir,
            env=env,
            preferred_port=self.port,
            enable_tunnel=self.enable_tunnel,
            tunnel_domain=self.tunnel_domain,
            health_check_url=f"http://localhost:{self.port}/",
            tunnel_health_endpoint="/",
            tunnel_ready_timeout=45,
            restart_on_failure=True,
            watch_paths=watch_paths,
            watch_patterns=watch_patterns,
            path_prefix="/",
        )


@dataclass
class StaticSiteService(ServiceTemplate):
    """Template for static site servers.

    Usage:
        service = StaticSiteService(
            name="docs",
            root_dir=Path("dist"),
            port=8080
        ).to_service_config()
    """

    root_dir: Path | None = None  # REQUIRED, validated in __post_init__
    index_file: str = "index.html"
    server_command: list[str] | None = None

    def __post_init__(self):
        """
        Validate required fields.
        """
        if not self.root_dir:
            raise ValueError("root_dir is required for StaticSiteService")

    def to_service_config(self) -> ServiceConfig:
        """
        Generate ServiceConfig for static site.
        """
        # Default to Python's http.server
        command = self.server_command or [
            "python",
            "-m",
            "http.server",
            str(self.port),
            "--directory",
            str(self.root_dir),
        ]

        return ServiceConfig(
            name=self.name,
            command=command,
            cwd=None,  # Command specifies directory
            env=self.env or {},
            preferred_port=self.port,
            enable_tunnel=self.enable_tunnel,
            tunnel_domain=self.tunnel_domain,
            health_check_url=f"http://localhost:{self.port}/",
            tunnel_health_endpoint="/",
            tunnel_ready_timeout=45,
            restart_on_failure=True,
            path_prefix="/",
        )


# Convenience function for common patterns
def python_asgi_service(name: str, app_path: str, port: int = 8000, **kwargs) -> ServiceConfig:
    """Shorthand for creating Python ASGI service config.

    Args:
        name: Service name
        app_path: ASGI application path ("module:app")
        port: Port number
        **kwargs: Additional ServiceTemplate fields

    Returns:
        ServiceConfig ready to use
    """
    return PythonASGIService(name=name, app_path=app_path, port=port, **kwargs).to_service_config()


def go_http_service(name: str, module_dir: Path, port: int = 8080, **kwargs) -> ServiceConfig:
    """Shorthand for creating Go HTTP service config.

    Args:
        name: Service name
        module_dir: Go module directory
        port: Port number
        **kwargs: Additional ServiceTemplate fields

    Returns:
        ServiceConfig ready to use
    """
    return GoHTTPService(name=name, module_dir=module_dir, port=port, **kwargs).to_service_config()


def nextjs_service(name: str, app_dir: Path, port: int = 3000, **kwargs) -> ServiceConfig:
    """Shorthand for creating Next.js service config.

    Args:
        name: Service name
        app_dir: Next.js app directory
        port: Port number
        **kwargs: Additional ServiceTemplate fields

    Returns:
        ServiceConfig ready to use
    """
    return NextJSService(name=name, app_dir=app_dir, port=port, **kwargs).to_service_config()
