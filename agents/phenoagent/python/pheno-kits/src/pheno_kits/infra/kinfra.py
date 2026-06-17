"""
KInfra - Main unified API for infrastructure management.

Provides a simple, unified interface for port allocation, tunnel management,
and service lifecycle management with automatic conflict resolution.
"""

import atexit
import logging
import os
import signal
from collections.abc import Iterable
from typing import Any

from .exceptions import PortAllocationError, TunnelError
from .port_allocator import PortAllocator
from .port_registry import PortRegistry, ServiceInfo
from .tunnel_sync import TunnelInfo, TunnelManager

logger = logging.getLogger(__name__)


class KInfra:
    """Unified KInfra interface for seamless infrastructure management.

    Provides high-level API for:
    - Port allocation with conflict resolution
    - Tunnel management with automatic updates
    - Service lifecycle management
    - Cleanup and resource management

    Usage:
        kinfra = KInfra()
        port = kinfra.allocate_port("my-service")
        tunnel_info = kinfra.start_tunnel("my-service", port)
        print(f"Service available at: {tunnel_info.hostname}")
    """

    def __init__(self, domain: str = "kooshapari.com", config_dir: str | None = None):
        """Initialize KInfra.

        Args:
            domain: Base domain for tunnels (default: kooshapari.com)
            config_dir: Configuration directory (default: ~/.kinfra)
        """
        self.domain = domain
        self.config_dir = config_dir

        # Initialize components
        self.registry = PortRegistry(config_dir=config_dir)
        self.allocator = PortAllocator(registry=self.registry)
        self.tunnel_manager = TunnelManager(registry=self.registry, domain=domain)

        # Track managed services for cleanup
        self._managed_services = set()
        self._cleanup_registered = False

        # Register cleanup handlers only if not already registered
        if not getattr(KInfra, "_global_cleanup_registered", False):
            atexit.register(self._cleanup_on_exit)
            signal.signal(signal.SIGTERM, self._cleanup_on_signal)
            signal.signal(signal.SIGINT, self._cleanup_on_signal)
            KInfra._global_cleanup_registered = True
            logger.debug("Registered KInfra cleanup handlers")

        logger.info(f"KInfra initialized for domain: {domain}")

    def allocate_port(self, service_name: str, preferred_port: int | None = None) -> int:
        """Allocate a port for a service with intelligent conflict resolution.

        Features:
        - Semi-static allocation (same port across runs when possible)
        - Automatic conflict detection and resolution
        - Process detection and cleanup
        - Port range validation

        Args:
            service_name: Name of the service
            preferred_port: Preferred port number (optional)

        Returns:
            Allocated port number

        Raises:
            PortAllocationError: If port allocation fails

        Example:
            kinfra = KInfra()
            port = kinfra.allocate_port("zen-mcp-server", preferred_port=8080)
            # Start your service on the allocated port
        """
        try:
            port = self.allocator.allocate_port(service_name, preferred_port)
            self._managed_services.add(service_name)
            logger.info(f"Allocated port {port} for service '{service_name}'")
            return port
        except Exception as e:
            logger.exception(f"Failed to allocate port for '{service_name}': {e}")
            raise PortAllocationError(f"Port allocation failed for '{service_name}': {e}")

    def start_tunnel(
        self, service_name: str, port: int, domain: str | None = None,
    ) -> TunnelInfo:
        """Start a tunnel for a service with automatic configuration.

        Features:
        - Automatic cloudflared tunnel creation
        - DNS routing setup
        - Configuration generation and updates
        - Port change detection and tunnel restart

        Args:
            service_name: Name of the service
            port: Local port to tunnel to
            domain: Override default domain (optional)

        Returns:
            TunnelInfo object with tunnel details

        Raises:
            TunnelError: If tunnel creation/update fails

        Example:
            kinfra = KInfra()
            tunnel_info = kinfra.start_tunnel("zen-mcp-server", 8080)
            print(f"Tunnel available at: https://{tunnel_info.hostname}")
        """
        try:
            if domain:
                # Create temporary tunnel manager with different domain
                tunnel_manager = TunnelManager(registry=self.registry, domain=domain)
                tunnel_info = tunnel_manager.start_tunnel(service_name, port)
            else:
                tunnel_info = self.tunnel_manager.start_tunnel(service_name, port)

            self._managed_services.add(service_name)
            logger.info(f"Started tunnel for '{service_name}': https://{tunnel_info.hostname}")
            return tunnel_info

        except Exception as e:
            logger.exception(f"Failed to start tunnel for '{service_name}': {e}")
            raise TunnelError(f"Tunnel creation failed for '{service_name}': {e}")

    def allocate_and_tunnel(
        self, service_name: str, preferred_port: int | None = None, domain: str | None = None,
    ) -> dict[str, Any]:
        """Convenience method to allocate port and start tunnel in one call.

        Args:
            service_name: Name of the service
            preferred_port: Preferred port number (optional)
            domain: Override default domain (optional)

        Returns:
            Dictionary with port, tunnel_info, and url

        Example:
            kinfra = KInfra()
            result = kinfra.allocate_and_tunnel("zen-mcp-server")

            # Start your service on result['port']
            # Access via result['url']
        """
        # Allocate port
        port = self.allocate_port(service_name, preferred_port)

        # Start tunnel
        tunnel_info = self.start_tunnel(service_name, port, domain)

        return {
            "service_name": service_name,
            "port": port,
            "tunnel_info": tunnel_info,
            "url": f"https://{tunnel_info.hostname}",
            "hostname": tunnel_info.hostname,
        }

    def get_service_url(self, service_name: str) -> str | None:
        """Get the public URL for a service.

        Args:
            service_name: Name of the service

        Returns:
            Public HTTPS URL or None if not found
        """
        return self.tunnel_manager.get_service_url(service_name)

    def get_service_port(self, service_name: str) -> int | None:
        """Get the allocated port for a service.

        Args:
            service_name: Name of the service

        Returns:
            Allocated port or None if not found
        """
        return self.allocator.get_service_port(service_name)

    def get_service_info(self, service_name: str) -> ServiceInfo | None:
        """Get complete service information.

        Args:
            service_name: Name of the service

        Returns:
            ServiceInfo object or None if not found
        """
        return self.registry.get_service(service_name)

    def get_tunnel_status(self, service_name: str) -> dict[str, Any]:
        """Get detailed tunnel status for a service.

        Args:
            service_name: Name of the service

        Returns:
            Dictionary with tunnel status information
        """
        return self.tunnel_manager.get_tunnel_status(service_name)

    def list_services(self) -> dict[str, dict[str, Any]]:
        """List all managed services with their details.

        Returns:
            Dictionary mapping service names to their details
        """
        services = {}
        for name, info in self.registry.get_all_services().items():
            services[name] = {
                "port": info.assigned_port,
                "pid": info.pid,
                "tunnel_id": info.tunnel_id,
                "hostname": info.tunnel_hostname,
                "url": f"https://{info.tunnel_hostname}" if info.tunnel_hostname else None,
                "last_seen": info.last_seen,
                "created_at": info.created_at,
            }
        return services

    def cleanup(self, service_name: str) -> bool:
        """Clean up resources for a specific service.

        Args:
            service_name: Name of the service to clean up

        Returns:
            True if cleanup was successful
        """
        logger.info(f"Cleaning up service '{service_name}'")

        success = True

        # Stop tunnel
        try:
            if not self.tunnel_manager.stop_tunnel(service_name):
                logger.warning(f"Failed to stop tunnel for '{service_name}'")
                success = False
        except Exception as e:
            logger.exception(f"Error stopping tunnel for '{service_name}': {e}")
            success = False

        # Release port
        try:
            if not self.allocator.release_port(service_name):
                logger.warning(f"Failed to release port for '{service_name}'")
                success = False
        except Exception as e:
            logger.exception(f"Error releasing port for '{service_name}': {e}")
            success = False

        # Remove from managed services
        self._managed_services.discard(service_name)

        if success:
            logger.info(f"Successfully cleaned up service '{service_name}'")

        return success

    def cleanup_all(self):
        """
        Clean up all managed services and resources.
        """
        logger.info("Cleaning up all KInfra resources")

        # Clean up managed services
        for service_name in list(self._managed_services):
            try:
                self.cleanup(service_name)
            except Exception as e:
                logger.exception(f"Error cleaning up service '{service_name}': {e}")

        # Clean up tunnel manager
        try:
            self.tunnel_manager.cleanup_all()
        except Exception as e:
            logger.exception(f"Error cleaning up tunnel manager: {e}")

        self._managed_services.clear()
        logger.info("KInfra cleanup completed")

    def cleanup_environment(
        self,
        grace_period: float = 3.0,
        force_kill: bool = True,
        exclude_pids: Iterable[int] | None = None,
    ) -> dict[str, int]:
        """
        Run comprehensive runtime cleanup, including stray cloudflared processes.
        """

        logger.info("Running KInfra runtime environment cleanup")

        # Perform standard cleanup first to stop managed resources
        self.cleanup_all()

        try:
            from tunnel_manager import cleanup_runtime_environment

            stats = cleanup_runtime_environment(
                grace_period=grace_period,
                force_kill=force_kill,
                exclude_pids=exclude_pids,
            )
            logger.info("Cloudflared cleanup summary: %s", stats)
            return stats
        except ImportError as exc:
            logger.warning("Runtime cleanup helpers unavailable: %s", exc)
            return {}
        except Exception as exc:
            logger.exception("Error during runtime environment cleanup: %s", exc)
            raise TunnelError(f"Runtime cleanup failed: {exc}")

    def health_check(self, service_name: str) -> dict[str, Any]:
        """Perform a health check on a service.

        Args:
            service_name: Name of the service

        Returns:
            Dictionary with health check results
        """
        service_info = self.registry.get_service(service_name)
        if not service_info:
            return {
                "service_name": service_name,
                "status": "not_found",
                "healthy": False,
                "message": f"Service '{service_name}' not found",
            }

        health = {
            "service_name": service_name,
            "port": service_info.assigned_port,
            "status": "unknown",
            "healthy": False,
            "checks": {},
        }

        # Check if port is still free (bad sign)
        port_free = self.allocator._is_port_free(service_info.assigned_port)
        health["checks"]["port_bound"] = not port_free

        # Check tunnel status
        tunnel_status = self.tunnel_manager.get_tunnel_status(service_name)
        health["checks"]["tunnel"] = tunnel_status

        # Overall health assessment
        if health["checks"]["port_bound"] and tunnel_status.get("tunnel_running"):
            health["status"] = "healthy"
            health["healthy"] = True
            health["message"] = "Service is running and tunnel is active"
        elif health["checks"]["port_bound"]:
            health["status"] = "degraded"
            health["healthy"] = False
            health["message"] = "Service is running but tunnel may be down"
        else:
            health["status"] = "unhealthy"
            health["healthy"] = False
            health["message"] = "Service does not appear to be running"

        return health

    def _cleanup_on_exit(self):
        """
        Clean up resources on program exit.
        """
        try:
            self.cleanup_all()
        except Exception as e:
            logger.exception(f"Error during exit cleanup: {e}")

    def _cleanup_on_signal(self, signum, frame):
        """
        Clean up resources on signal.
        """
        logger.info(f"Received signal {signum}, cleaning up...")
        try:
            self.cleanup_all()
        except Exception as e:
            logger.exception(f"Error during signal cleanup: {e}")

        # Re-raise the signal for default handling
        signal.signal(signum, signal.SIG_DFL)
        os.kill(os.getpid(), signum)

    def __enter__(self):
        """
        Context manager entry.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit with cleanup.
        """
        self.cleanup_all()
