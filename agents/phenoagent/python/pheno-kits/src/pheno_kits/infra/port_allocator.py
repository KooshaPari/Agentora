"""
Port Allocator - Intelligent port allocation with conflict resolution.

Provides semi-static port allocation with automatic conflict resolution,
process detection, and instance management.
"""

import logging
import os
import socket
import time
import warnings

from .exceptions import PortAllocationError
from .port_registry import PortRegistry
from .utils.process import get_port_occupant, is_port_free, terminate_process

logger = logging.getLogger(__name__)


class PortAllocator:
    """Port allocator with conflict resolution.

    Features:
    - Semi-static port allocation (consistent ports across runs)
    - Automatic conflict detection and resolution
    - Process detection and management
    - Stale instance cleanup
    - Port range management
    """

    def __init__(self, registry: PortRegistry | None = None):
        self.registry = registry or PortRegistry()
        self.default_port_range = (8000, 65535)  # Allow full ephemeral port range
        self.max_allocation_attempts = 50

    def allocate_port(
        self,
        service_name: str,
        preferred_port: int | None = None,
        project: str | None = None,
        service: str | None = None,
        scope: str | None = None,
    ) -> int:
        """Allocate a port for a service with smart conflict resolution.

        Resolution strategy:
        1. Try preferred port if specified (highest priority)
        2. Try canonical port (from registry) if available
        3. Check for conflicts and resolve them
        4. Fall back to dynamic allocation

        Args:
            service_name: Name of the service
            preferred_port: Preferred port number (optional)
            project: Optional project identifier for multi-tenant coordination
            service: Optional service type/category for grouping related services
            scope: Optional scope identifier (e.g., 'shared', 'isolated', 'global')

        Returns:
            Allocated port number

        Raises:
            PortAllocationError: If port allocation fails
        """
        # Store metadata for use in registration calls
        self._current_metadata = {
            "project": project,
            "service": service,
            "scope": scope,
        }
        logger.info(f"Allocating port for service '{service_name}'")

        # Step 1: Try preferred port if specified (highest priority)
        if preferred_port and self.registry.validate_port_range(preferred_port):
            logger.debug(f"Trying preferred port {preferred_port} for '{service_name}'")
            if self._try_allocate_specific_port(service_name, preferred_port):
                return preferred_port

        # Step 2: Check if service already has a canonical port
        canonical_port = self.registry.get_canonical_port(service_name)
        if canonical_port:
            logger.debug(f"Found canonical port {canonical_port} for '{service_name}'")
            if self._try_allocate_specific_port(service_name, canonical_port):
                return canonical_port

        # Step 3: Dynamic allocation within range
        logger.debug(f"Using dynamic allocation for '{service_name}'")
        return self._allocate_dynamic_port(service_name)

    def _try_allocate_specific_port(self, service_name: str, port: int) -> bool:
        """
        Try to allocate a specific port, handling conflicts.
        """
        metadata = getattr(self, "_current_metadata", {})

        if is_port_free(port):
            # Port is free, allocate it
            self.registry.register_service(
                service_name,
                port,
                os.getpid(),
                project=metadata.get("project"),
                service=metadata.get("service"),
                scope=metadata.get("scope"),
            )
            logger.info(f"Allocated free port {port} to '{service_name}'")
            return True

        # Port is occupied, check what's using it
        conflict_info = get_port_occupant(port)
        if not conflict_info:
            logger.warning(f"Port {port} appears occupied but no process found")
            return False

        logger.debug(
            f"Port {port} occupied by PID {conflict_info.get('pid')}: {conflict_info.get('cmdline', 'unknown')}",
        )

        # Check if it's our own service (stale instance)
        if self._is_our_service_instance(conflict_info, service_name):
            logger.info(f"Found stale instance of '{service_name}' on port {port}, terminating...")
            if terminate_process(conflict_info["pid"]):
                # Wait a bit for the port to be released
                time.sleep(0.5)
                if is_port_free(port):
                    self.registry.register_service(
                        service_name,
                        port,
                        os.getpid(),
                        project=metadata.get("project"),
                        service=metadata.get("service"),
                        scope=metadata.get("scope"),
                    )
                    logger.info(
                        f"Reclaimed port {port} for '{service_name}' after terminating stale instance",
                    )
                    return True

        # Port is occupied by another process/service
        logger.debug(f"Port {port} unavailable for '{service_name}', will try different port")
        return False

    def _allocate_dynamic_port(self, service_name: str) -> int:
        """
        Allocate a port dynamically within the allowed range.
        """
        metadata = getattr(self, "_current_metadata", {})
        allocated_ports = self.registry.get_allocated_ports()
        min_port, max_port = self.default_port_range

        for attempt in range(self.max_allocation_attempts):
            # Try OS-assigned port first
            if attempt == 0:
                port = self._get_os_assigned_port()
                if port and min_port <= port <= max_port and port not in allocated_ports:
                    if is_port_free(port):
                        self.registry.register_service(
                            service_name,
                            port,
                            os.getpid(),
                            project=metadata.get("project"),
                            service=metadata.get("service"),
                            scope=metadata.get("scope"),
                        )
                        logger.info(f"Allocated OS-assigned port {port} to '{service_name}'")
                        return port

            # Try sequential allocation within range
            for port in range(min_port, max_port + 1):
                if port in allocated_ports or port in self.registry.reserved_ports:
                    continue

                if is_port_free(port):
                    self.registry.register_service(
                        service_name,
                        port,
                        os.getpid(),
                        project=metadata.get("project"),
                        service=metadata.get("service"),
                        scope=metadata.get("scope"),
                    )
                    logger.info(f"Allocated sequential port {port} to '{service_name}'")
                    return port

        raise PortAllocationError(
            f"Failed to allocate port for '{service_name}' after {self.max_allocation_attempts} attempts",
        )

    def _get_os_assigned_port(self) -> int | None:
        """
        Get a port assigned by the OS.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(("127.0.0.1", 0))
                return sock.getsockname()[1]
        except OSError:
            return None

    def _is_our_service_instance(self, process_info: dict, service_name: str) -> bool:
        """
        Check if a process is a stale instance of our service.
        """
        cmdline = process_info.get("cmdline", "").lower()
        process_name = process_info.get("name", "").lower()

        # Check if the service is registered and the PID matches
        service_info = self.registry.get_service(service_name)
        if service_info and service_info.pid == process_info.get("pid"):
            return True

        # Heuristic checks based on command line and process name
        service_indicators = [service_name.lower(), "zen-mcp", "mcp-server", "fastmcp", "server.py"]

        return any(
            indicator in cmdline or indicator in process_name for indicator in service_indicators
        )

    def release_port(self, service_name: str) -> bool:
        """
        Release a port allocated to a service.
        """
        service_info = self.registry.get_service(service_name)
        if not service_info:
            return False

        logger.info(f"Releasing port {service_info.assigned_port} for service '{service_name}'")
        return self.registry.unregister_service(service_name)

    def get_service_port(self, service_name: str) -> int | None:
        """
        Get the currently allocated port for a service.
        """
        service_info = self.registry.get_service(service_name)
        return service_info.assigned_port if service_info else None

    def list_allocated_services(self) -> dict[str, int]:
        """
        Get all currently allocated services and their ports.
        """
        return {name: info.assigned_port for name, info in self.registry.get_all_services().items()}

    def _is_port_free(self, port: int) -> bool:
        """
        Check if a port is free (available for allocation).

        Args:
            port: Port number to check

        Returns:
            True if port is free, False if in use
        """
        return is_port_free(port)


class SmartPortAllocator(PortAllocator):
    """Deprecated: use PortAllocator instead."""

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "SmartPortAllocator is deprecated, use PortAllocator instead",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)
