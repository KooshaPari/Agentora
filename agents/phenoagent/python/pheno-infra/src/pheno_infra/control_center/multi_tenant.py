"""Multi-Tenant Management for Pheno Control Center.

Manages tunnels, fallback services, and proxy routing with per-project isolation to
avoid port conflicts and enable shared infrastructure.
"""

import contextlib
import logging
import socket
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from ..fallback_site import FallbackServer
from ..proxy_gateway import ProxyServer, UpstreamConfig
from ..tunnel_sync import TunnelInfo, TunnelManager
from .config import ProjectConfig

logger = logging.getLogger(__name__)


@dataclass
class ProjectTunnelInfo:
    """
    Tunnel information specific to a project.
    """

    project: str
    """
    Project name.
    """

    service_name: str
    """
    Service name within the project.
    """

    local_port: int
    """
    Local port being tunneled.
    """

    tunnel_info: TunnelInfo
    """
    Actual tunnel information.
    """

    metadata: dict[str, Any] = field(default_factory=dict)
    """
    Additional tunnel metadata.
    """


@dataclass
class ProjectFallbackInfo:
    """
    Fallback configuration for a project.
    """

    project: str
    """
    Project name.
    """

    port: int
    """
    Fallback port for this project.
    """

    active: bool = False
    """
    Whether fallback is currently active.
    """

    upstream_services: dict[str, str] = field(default_factory=dict)
    """
    Map of service names to upstream URLs.
    """


@dataclass
class ProjectProxyInfo:
    """
    Proxy configuration for a project.
    """

    project: str
    """
    Project name.
    """

    port: int
    """
    Proxy port for this project.
    """

    active: bool = False
    """
    Whether proxy is currently active.
    """

    upstreams: list[UpstreamConfig] = field(default_factory=list)
    """
    Upstream configurations for this project.
    """


class TenantManager:
    """Manages multi-tenant tunnels, fallback services, and proxy routing.

    Provides:
    - Per-project port allocation for fallback/proxy services
    - Shared tunnel management with project isolation
    - Clean separation of project resources
    - Coordinated cleanup to avoid affecting other projects
    """

    def __init__(
        self,
        base_fallback_port: int = 9000,
        base_proxy_port: int = 9100,
        tunnel_domain: str = "kooshapari.com",
    ):
        """
        Initialize multi-tenant manager.
        """
        self.base_fallback_port = base_fallback_port
        self.base_proxy_port = base_proxy_port
        self.tunnel_domain = tunnel_domain

        # Project resource tracking
        self.project_tunnels: dict[str, dict[str, ProjectTunnelInfo]] = defaultdict(dict)
        self.project_fallbacks: dict[str, ProjectFallbackInfo] = {}
        self.project_proxies: dict[str, ProjectProxyInfo] = {}

        # Shared infrastructure
        self.tunnel_manager = TunnelManager(domain=tunnel_domain)
        self.fallback_servers: dict[int, FallbackServer] = {}
        self.proxy_servers: dict[int, ProxyServer] = {}

        # Port allocation tracking
        self.allocated_fallback_ports: set[int] = set()
        self.allocated_proxy_ports: set[int] = set()

        logger.info("Multi-tenant manager initialized")

    def register_project(self, project_config: ProjectConfig) -> None:
        """
        Register a project for multi-tenant management.
        """
        project_name = project_config.name

        # Calculate ports
        fallback_port = project_config.get_fallback_port(self.base_fallback_port)
        proxy_port = project_config.get_proxy_port(self.base_proxy_port)

        # Ensure ports are available
        fallback_port = self._ensure_port_available(fallback_port, self.allocated_fallback_ports)
        proxy_port = self._ensure_port_available(proxy_port, self.allocated_proxy_ports)

        # Register fallback configuration
        self.project_fallbacks[project_name] = ProjectFallbackInfo(
            project=project_name, port=fallback_port,
        )
        self.allocated_fallback_ports.add(fallback_port)

        # Register proxy configuration
        self.project_proxies[project_name] = ProjectProxyInfo(project=project_name, port=proxy_port)
        self.allocated_proxy_ports.add(proxy_port)

        logger.info(
            f"Registered project {project_name}: fallback={fallback_port}, proxy={proxy_port}",
        )

    def _ensure_port_available(self, preferred_port: int, allocated_ports: set[int]) -> int:
        """
        Ensure a port is available, incrementing if necessary.
        """
        port = preferred_port
        while port in allocated_ports or self._is_port_in_use(port):
            port += 1
        return port

    def _is_port_in_use(self, port: int) -> bool:
        """
        Check if a port is currently in use.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.1)
                result = sock.connect_ex(("localhost", port))
                return result == 0
        except Exception:
            return False

    async def create_tunnel(
        self,
        project: str,
        service_name: str,
        local_port: int,
        domain: str | None = None,
        path: str = "/",
    ) -> ProjectTunnelInfo | None:
        """Create a tunnel for a project service.

        Args:
            project: Project name
            service_name: Service name within project
            local_port: Local port to tunnel
            domain: Override tunnel domain
            path: Path prefix for the tunnel

        Returns:
            Project tunnel info if successful
        """
        try:
            # Use project-specific subdomain
            tunnel_domain = domain or self.tunnel_domain
            subdomain = f"{service_name}.{project}" if project != service_name else service_name

            # Create tunnel through tunnel manager
            tunnel_info = self.tunnel_manager.create_tunnel(
                name=f"{project}-{service_name}",
                port=local_port,
                domain=tunnel_domain,
                subdomain=subdomain,
                path=path,
            )

            # Create project tunnel info
            project_tunnel = ProjectTunnelInfo(
                project=project,
                service_name=service_name,
                local_port=local_port,
                tunnel_info=tunnel_info,
            )

            # Store in registry
            self.project_tunnels[project][service_name] = project_tunnel

            logger.info(
                f"Created tunnel for {project}.{service_name}: "
                f"{tunnel_info.hostname} -> localhost:{local_port}",
            )
            return project_tunnel

        except Exception as e:
            logger.exception(f"Failed to create tunnel for {project}.{service_name}: {e}")
            return None

    async def stop_tunnel(self, project: str, service_name: str) -> bool:
        """
        Stop a tunnel for a project service.
        """
        project_tunnels = self.project_tunnels.get(project, {})
        project_tunnel = project_tunnels.get(service_name)

        if not project_tunnel:
            logger.warning(f"No tunnel found for {project}.{service_name}")
            return False

        try:
            # Stop tunnel
            success = self.tunnel_manager.stop_tunnel(f"{project}-{service_name}")

            if success:
                # Remove from registry
                del project_tunnels[service_name]
                logger.info(f"Stopped tunnel for {project}.{service_name}")

            return success

        except Exception as e:
            logger.exception(f"Failed to stop tunnel for {project}.{service_name}: {e}")
            return False

    async def start_project_fallback(self, project: str) -> bool:
        """
        Start fallback server for a project.
        """
        fallback_info = self.project_fallbacks.get(project)
        if not fallback_info:
            logger.error(f"No fallback configuration for project: {project}")
            return False

        if fallback_info.active:
            logger.debug(f"Fallback already active for project: {project}")
            return True

        try:
            # Check if fallback server already exists for this port
            if fallback_info.port not in self.fallback_servers:
                # Create new fallback server
                fallback_server = FallbackServer(port=fallback_info.port, project_name=project)
                await fallback_server.start()
                self.fallback_servers[fallback_info.port] = fallback_server
                logger.info(f"Started fallback server for {project} on port {fallback_info.port}")

            fallback_info.active = True
            return True

        except Exception as e:
            logger.exception(f"Failed to start fallback for {project}: {e}")
            return False

    async def stop_project_fallback(self, project: str) -> bool:
        """
        Stop fallback server for a project.
        """
        fallback_info = self.project_fallbacks.get(project)
        if not fallback_info:
            return False

        if not fallback_info.active:
            return True

        try:
            # Check if other projects are using the same fallback port
            other_projects_using_port = any(
                fb.port == fallback_info.port and fb.active and fb.project != project
                for fb in self.project_fallbacks.values()
            )

            if not other_projects_using_port:
                # Safe to stop the fallback server
                fallback_server = self.fallback_servers.get(fallback_info.port)
                if fallback_server:
                    await fallback_server.stop()
                    del self.fallback_servers[fallback_info.port]
                    logger.info(f"Stopped fallback server on port {fallback_info.port}")

            fallback_info.active = False
            fallback_info.upstream_services.clear()
            return True

        except Exception as e:
            logger.exception(f"Failed to stop fallback for {project}: {e}")
            return False

    async def start_project_proxy(self, project: str, upstreams: list[UpstreamConfig]) -> bool:
        """
        Start proxy server for a project with specified upstreams.
        """
        proxy_info = self.project_proxies.get(project)
        if not proxy_info:
            logger.error(f"No proxy configuration for project: {project}")
            return False

        try:
            # Ensure proxy server exists for this port, else start it
            if proxy_info.port not in self.proxy_servers:
                proxy_server = ProxyServer(proxy_port=proxy_info.port)
                await proxy_server.start()
                self.proxy_servers[proxy_info.port] = proxy_server
                logger.info(f"Started proxy server for {project} on port {proxy_info.port}")

            # Register upstreams via admin client (tenant-aware)
            from ..proxy_server.admin_client import ProxyAdminClient

            client = ProxyAdminClient(port=proxy_info.port)
            for upstream in upstreams:
                client.add_upstream(
                    path_prefix=upstream.path_prefix or "/",
                    port=upstream.port,
                    host=upstream.host,
                    service_name=getattr(upstream, "name", None),
                    tenant=project,
                )

            proxy_info.active = True
            proxy_info.upstreams = upstreams
            return True

        except Exception as e:
            logger.exception(f"Failed to start proxy for {project}: {e}")
            return False

    async def stop_project_proxy(self, project: str) -> bool:
        """
        Stop proxy server for a project.
        """
        proxy_info = self.project_proxies.get(project)
        if not proxy_info:
            return False

        if not proxy_info.active:
            return True

        try:
            proxy_server = self.proxy_servers.get(proxy_info.port)
            # Deregister upstreams via admin client
            try:
                from ..proxy_server.admin_client import ProxyAdminClient

                client = ProxyAdminClient(port=proxy_info.port)
                client.deregister_tenant(tenant=project)
            except Exception:
                logger.debug(
                    "Admin deregister_tenant failed; attempting local removal", exc_info=True,
                )
                if proxy_server:
                    for upstream in proxy_info.upstreams:
                        with contextlib.suppress(Exception):
                            proxy_server.remove_upstream(upstream.path_prefix)

            # Check if other projects are using this proxy
            other_projects_using_port = any(
                px.port == proxy_info.port and px.active and px.project != project
                for px in self.project_proxies.values()
            )

            if not other_projects_using_port and proxy_server:
                # Safe to stop the entire proxy server
                await proxy_server.stop()
                del self.proxy_servers[proxy_info.port]
                logger.info(f"Stopped proxy server on port {proxy_info.port}")

            proxy_info.active = False
            proxy_info.upstreams.clear()
            return True

        except Exception as e:
            logger.exception(f"Failed to stop proxy for {project}: {e}")
            return False

    async def cleanup_project(self, project: str) -> None:
        """
        Clean up all resources for a project.
        """
        logger.info(f"Cleaning up resources for project: {project}")

        # Stop all tunnels
        project_tunnels = self.project_tunnels.get(project, {}).copy()
        for service_name in project_tunnels:
            await self.stop_tunnel(project, service_name)

        # Stop fallback
        await self.stop_project_fallback(project)

        # Stop proxy
        await self.stop_project_proxy(project)

        # Clean up tunnel registry
        self.project_tunnels.pop(project, None)

        logger.info(f"Cleanup completed for project: {project}")

    def get_project_tunnels(self, project: str) -> dict[str, ProjectTunnelInfo]:
        """
        Get all tunnels for a project.
        """
        return self.project_tunnels.get(project, {}).copy()

    def get_project_fallback_port(self, project: str) -> int | None:
        """
        Get fallback port for a project.
        """
        fallback_info = self.project_fallbacks.get(project)
        return fallback_info.port if fallback_info else None

    def get_project_proxy_port(self, project: str) -> int | None:
        """
        Get proxy port for a project.
        """
        proxy_info = self.project_proxies.get(project)
        return proxy_info.port if proxy_info else None

    def get_tunnel_status(self, project: str, service_name: str) -> dict[str, Any] | None:
        """
        Get tunnel status for a specific service.
        """
        project_tunnel = self.project_tunnels.get(project, {}).get(service_name)
        if not project_tunnel:
            return None

        tunnel_info = project_tunnel.tunnel_info
        return {
            "project": project,
            "service": service_name,
            "local_port": project_tunnel.local_port,
            "hostname": tunnel_info.hostname,
            "public_url": f"https://{tunnel_info.hostname}",
            "tunnel_id": tunnel_info.tunnel_id,
            "active": True,  # If it exists in registry, it should be active
            "metadata": project_tunnel.metadata,
        }

    def get_global_status(self) -> dict[str, Any]:
        """
        Get status of all multi-tenant resources.
        """
        return {
            "tunnels": {
                project: {
                    service: {
                        "hostname": tunnel.tunnel_info.hostname,
                        "local_port": tunnel.local_port,
                        "public_url": f"https://{tunnel.tunnel_info.hostname}",
                    }
                    for service, tunnel in tunnels.items()
                }
                for project, tunnels in self.project_tunnels.items()
            },
            "fallbacks": {
                project: {
                    "port": info.port,
                    "active": info.active,
                    "services": list(info.upstream_services.keys()),
                }
                for project, info in self.project_fallbacks.items()
            },
            "proxies": {
                project: {
                    "port": info.port,
                    "active": info.active,
                    "upstreams": len(info.upstreams),
                }
                for project, info in self.project_proxies.items()
            },
            "infrastructure": {
                "active_fallback_servers": len(self.fallback_servers),
                "active_proxy_servers": len(self.proxy_servers),
                "total_tunnels": sum(len(tunnels) for tunnels in self.project_tunnels.values()),
            },
        }

    async def shutdown(self) -> None:
        """
        Shutdown all multi-tenant resources.
        """
        logger.info("Shutting down multi-tenant manager...")

        # Stop all project resources
        for project in list(self.project_tunnels.keys()):
            await self.cleanup_project(project)

        # Stop remaining fallback servers
        for fallback_server in list(self.fallback_servers.values()):
            try:
                await fallback_server.stop()
            except Exception as e:
                logger.warning(f"Error stopping fallback server: {e}")
        self.fallback_servers.clear()

        # Stop remaining proxy servers
        for proxy_server in list(self.proxy_servers.values()):
            try:
                await proxy_server.stop()
            except Exception as e:
                logger.warning(f"Error stopping proxy server: {e}")
        self.proxy_servers.clear()

        logger.info("Multi-tenant manager shutdown complete")


# Alias for backward compatibility
MultiTenantManager = TenantManager
