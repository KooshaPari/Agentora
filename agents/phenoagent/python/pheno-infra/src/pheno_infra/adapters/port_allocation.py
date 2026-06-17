"""
Unified port management utilities.

This module consolidates the persistent registry behavior from
``port_registry.py`` with the allocation and conflict resolution
capabilities previously spread across ``port_allocator.py`` and
``infra/networking/ports.py``.  The resulting ``PortManager`` exposes a
single surface for reserving, persisting, and releasing ports while
tracking rich service metadata.
"""

from __future__ import annotations

import fcntl
import json
import logging
import os
import socket
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from ..exceptions import ConfigurationError, PortAllocationError
from ..utils.process import get_port_occupant, is_port_free, terminate_process

logger = logging.getLogger(__name__)


@dataclass
class ServiceInfo:
    """
    Snapshot of a registered service and the port allocated to it.

    Attributes:
        service_name: Friendly identifier used when reserving the port.
        assigned_port: Port number currently mapped to the service.
        pid: Process identifier that owns the service, if known.
        last_seen: Timestamp of the last read/update of this record.
        tunnel_id: Optional identifier for a tunneling session.
        tunnel_hostname: Hostname provided by any active tunnel.
        config_path: Path to configuration material used by the service.
        created_at: Timestamp when the service was first registered.
        project: Optional project or tenancy partition for coordination.
        service: Optional service family/category metadata.
        scope: Optional scope tag (for example ``shared`` vs ``isolated``).
    """

    service_name: str
    assigned_port: int
    pid: int | None = None
    last_seen: float = 0.0
    tunnel_id: str | None = None
    tunnel_hostname: str | None = None
    config_path: str | None = None
    created_at: float = 0.0
    project: str | None = None
    service: str | None = None
    scope: str | None = None

    def __post_init__(self) -> None:
        """
        Stamp creation and access timestamps when a record is instantiated.
        """
        now = time.time()
        if self.last_seen == 0.0:
            self.last_seen = now
        if self.created_at == 0.0:
            self.created_at = now

    def is_stale(self, max_age_seconds: int = 3600) -> bool:
        """
        Determine whether the record has gone stale.

        Args:
            max_age_seconds: Time window that defines freshness.

        Returns:
            ``True`` if ``last_seen`` is older than ``max_age_seconds``.
        """
        return time.time() - self.last_seen > max_age_seconds

    def update_seen(self) -> None:
        """
        Refresh the ``last_seen`` timestamp to the current time.
        """
        self.last_seen = time.time()


class PortManager:
    """
    High-level port manager with persistent registry and smart allocation.

    The manager provides:

    * JSON-backed persistence with atomic updates and file locking.
    * Rich ``ServiceInfo`` metadata, including project awareness.
    * Semi-static port allocation that favors preferred and canonical ports.
    * Conflict detection with optional stale process reclamation.
    * Utility helpers for observing and releasing port assignments.
    """

    def __init__(
        self,
        config_dir: Path | None = None,
        port_range: tuple[int, int] | None = None,
        reserved_ports: set[int] | None = None,
        max_allocation_attempts: int = 50,
        stale_record_ttl: int = 86400,
    ) -> None:
        """
        Initialize the manager and eagerly load any persisted registry state.

        Args:
            config_dir: Optional override of the configuration directory used
                to store the registry file. Defaults to ``~/.kinfra``.
            port_range: Inclusive ``(min_port, max_port)`` tuple describing the
                dynamic allocation range. Defaults to ``(8000, 65535)``.
            reserved_ports: Ports that must never be allocated dynamically.
            max_allocation_attempts: Number of attempts when searching for a
                free port before giving up.
            stale_record_ttl: Age threshold for pruning unused service records.
        """
        self.config_dir = config_dir or Path.home() / ".kinfra"
        self.config_dir.mkdir(exist_ok=True, parents=True)
        self.registry_file = self.config_dir / "port_registry.json"

        self.default_port_range = port_range or (8000, 65535)
        self.reserved_ports: set[int] = reserved_ports or {
            22,
            80,
            443,
            3306,
            5432,
            6379,
        }
        self.max_allocation_attempts = max_allocation_attempts
        self.stale_record_ttl = stale_record_ttl

        self._services: dict[str, ServiceInfo] = {}
        self._load_registry()

    # --------------------------------------------------------------------- #
    # Persistence helpers
    # --------------------------------------------------------------------- #

    def _load_registry(self) -> None:
        """
        Load the persisted registry data into memory with shared file locking.
        """
        if not self.registry_file.exists():
            self._services = {}
            return

        try:
            with open(self.registry_file) as registry_fp:
                fcntl.flock(registry_fp.fileno(), fcntl.LOCK_SH)
                data = json.load(registry_fp)

            services: dict[str, ServiceInfo] = {}
            for name, info_dict in data.get("services", {}).items():
                try:
                    valid_fields = {
                        key: value
                        for key, value in info_dict.items()
                        if key in ServiceInfo.__dataclass_fields__
                    }
                    services[name] = ServiceInfo(**valid_fields)
                except (TypeError, ValueError) as exc:
                    logger.warning("Skipping invalid service entry %s: %s", name, exc)

            self._services = services
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(
                "Failed to load port registry %s: %s. Resetting in-memory state.",
                self.registry_file,
                exc,
            )
            self._services = {}

    def _save_registry(self) -> None:
        """
        Persist the in-memory registry state to disk using an atomic rename.
        """
        self._cleanup_stale_entries(self.stale_record_ttl)

        payload = {
            "version": "1.0",
            "timestamp": time.time(),
            "services": {name: asdict(info) for name, info in self._services.items()},
        }

        temp_file = self.registry_file.with_suffix(".tmp")
        try:
            with open(temp_file, "w") as temp_fp:
                fcntl.flock(temp_fp.fileno(), fcntl.LOCK_EX)
                json.dump(payload, temp_fp, indent=2)
                temp_fp.flush()

            temp_file.replace(self.registry_file)
            logger.debug("Registry persisted with %s services", len(self._services))
        except OSError as exc:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    logger.debug("Failed to clean up temp registry file %s", temp_file)
            raise ConfigurationError(f"Failed to save port registry: {exc}") from exc

    def _cleanup_stale_entries(self, max_age_seconds: int) -> None:
        """
        Drop any service records that have not been observed recently.
        """
        stale_services = [
            name
            for name, info in self._services.items()
            if info.is_stale(max_age_seconds)
        ]

        for service_name in stale_services:
            logger.info("Removing stale registry entry for %s", service_name)
            del self._services[service_name]

    # --------------------------------------------------------------------- #
    # Registry interface
    # --------------------------------------------------------------------- #

    def register_service(
        self,
        service_name: str,
        port: int,
        pid: int | None = None,
        *,
        project: str | None = None,
        service: str | None = None,
        scope: str | None = None,
        tunnel_id: str | None = None,
        tunnel_hostname: str | None = None,
        config_path: str | None = None,
    ) -> ServiceInfo:
        """
        Insert or overwrite a service record and persist the registry.

        Args:
            service_name: Unique identifier for the service.
            port: Port number assigned to the service.
            pid: Process identifier currently using the port.
            project: Optional project partition for the service.
            service: Optional service family metadata.
            scope: Optional scope tag that influences tenancy.
            tunnel_id: Optional identifier returned by a tunneling service.
            tunnel_hostname: External hostname associated with the tunnel.
            config_path: Path to supporting configuration material.

        Returns:
            The ``ServiceInfo`` snapshot that was stored.
        """
        record = ServiceInfo(
            service_name=service_name,
            assigned_port=port,
            pid=pid,
            project=project,
            service=service,
            scope=scope,
            tunnel_id=tunnel_id,
            tunnel_hostname=tunnel_hostname,
            config_path=config_path,
        )
        self._services[service_name] = record
        self._save_registry()

        logger.info("Registered service %s on port %s", service_name, port)
        return record

    def get_service(self, service_name: str) -> ServiceInfo | None:
        """
        Retrieve a service record and update its ``last_seen`` timestamp.
        """
        record = self._services.get(service_name)
        if record:
            record.update_seen()
            self._save_registry()
        return record

    def update_service(self, service_name: str, **updates: object) -> ServiceInfo | None:
        """
        Apply an in-place update to a service record before persisting it.
        """
        record = self._services.get(service_name)
        if record is None:
            return None

        for key, value in updates.items():
            if hasattr(record, key):
                setattr(record, key, value)

        record.update_seen()
        self._save_registry()
        return record

    def unregister_service(self, service_name: str) -> bool:
        """
        Remove a service record from the registry.
        """
        if service_name in self._services:
            del self._services[service_name]
            self._save_registry()
            logger.info("Unregistered service %s", service_name)
            return True
        return False

    def get_all_services(self) -> dict[str, ServiceInfo]:
        """
        Return a shallow copy of the current service registry.
        """
        return self._services.copy()

    def get_allocated_ports(self) -> set[int]:
        """
        Return the set of all ports currently tracked in the registry.
        """
        return {info.assigned_port for info in self._services.values()}

    def is_port_registered(self, port: int) -> str | None:
        """
        Check whether a port is already mapped to a service.
        """
        for name, info in self._services.items():
            if info.assigned_port == port:
                return name
        return None

    def get_canonical_port(self, service_name: str) -> int | None:
        """
        Return the persisted port for ``service_name`` if one exists.
        """
        record = self._services.get(service_name)
        return record.assigned_port if record else None

    def validate_port_range(self, port: int) -> bool:
        """
        Confirm that a port number is eligible for allocation.
        """
        if port in self.reserved_ports:
            return False

        min_port, max_port = self.default_port_range
        return min_port <= port <= max_port

    # --------------------------------------------------------------------- #
    # Allocation helpers
    # --------------------------------------------------------------------- #

    def allocate_port(
        self,
        service_name: str,
        preferred_port: int | None = None,
        *,
        project: str | None = None,
        service: str | None = None,
        scope: str | None = None,
    ) -> int:
        """
        Allocate a port for ``service_name`` with smart conflict resolution.

        The allocator prefers the caller-specified ``preferred_port``.  If
        omitted or unavailable it falls back to the canonical port recorded in
        the registry.  Remaining conflicts are resolved by dynamic allocation.

        Args:
            service_name: Logical name of the service requesting a port.
            preferred_port: Optional high-priority port to attempt first.
            project: Project or tenancy metadata stored with the record.
            service: Service category metadata stored with the record.
            scope: Scope tag describing the isolation level.

        Returns:
            The allocated port number.

        Raises:
            PortAllocationError: If the allocator cannot find a free port.
        """
        metadata = {
            "project": project,
            "service": service,
            "scope": scope,
        }

        logger.info("Allocating port for service %s", service_name)

        if preferred_port and self.validate_port_range(preferred_port):
            logger.debug("Attempting preferred port %s for %s", preferred_port, service_name)
            if self._try_allocate_specific_port(service_name, preferred_port, metadata):
                return preferred_port

        canonical_port = self.get_canonical_port(service_name)
        if canonical_port and self.validate_port_range(canonical_port):
            logger.debug("Attempting canonical port %s for %s", canonical_port, service_name)
            if self._try_allocate_specific_port(service_name, canonical_port, metadata):
                return canonical_port

        logger.debug("Falling back to dynamic allocation for %s", service_name)
        return self._allocate_dynamic_port(service_name, metadata)

    def _try_allocate_specific_port(
        self,
        service_name: str,
        port: int,
        metadata: dict[str, str | None],
    ) -> bool:
        """
        Attempt to allocate a specific port, reclaiming stale processes when needed.
        """
        if not self.validate_port_range(port):
            return False

        if is_port_free(port):
            self.register_service(
                service_name,
                port,
                os.getpid(),
                project=metadata.get("project"),
                service=metadata.get("service"),
                scope=metadata.get("scope"),
            )
            logger.info("Allocated free port %s to %s", port, service_name)
            return True

        conflict_info = get_port_occupant(port)
        if not conflict_info:
            logger.warning("Port %s appears occupied but no process information was found", port)
            return False

        logger.debug(
            "Port %s occupied by PID %s (%s)",
            port,
            conflict_info.get("pid"),
            conflict_info.get("cmdline", "unknown"),
        )

        if self._is_our_service_instance(conflict_info, service_name):
            logger.info("Terminating stale instance of %s on port %s", service_name, port)
            if terminate_process(conflict_info["pid"]):
                time.sleep(0.5)
                if is_port_free(port):
                    self.register_service(
                        service_name,
                        port,
                        os.getpid(),
                        project=metadata.get("project"),
                        service=metadata.get("service"),
                        scope=metadata.get("scope"),
                    )
                    logger.info("Reclaimed port %s for %s", port, service_name)
                    return True

        return False

    def _allocate_dynamic_port(
        self,
        service_name: str,
        metadata: dict[str, str | None],
    ) -> int:
        """
        Scan for an available port within the configured allocation range.
        """
        allocated_ports = self.get_allocated_ports()
        min_port, max_port = self.default_port_range

        for attempt in range(self.max_allocation_attempts):
            if attempt == 0:
                os_port = self._get_os_assigned_port()
                if (
                    os_port
                    and min_port <= os_port <= max_port
                    and os_port not in allocated_ports
                    and os_port not in self.reserved_ports
                    and is_port_free(os_port)
                ):
                    self.register_service(
                        service_name,
                        os_port,
                        os.getpid(),
                        project=metadata.get("project"),
                        service=metadata.get("service"),
                        scope=metadata.get("scope"),
                    )
                    logger.info("Allocated OS-assigned port %s to %s", os_port, service_name)
                    return os_port

            for port in range(min_port, max_port + 1):
                if port in allocated_ports or port in self.reserved_ports:
                    continue

                if is_port_free(port):
                    self.register_service(
                        service_name,
                        port,
                        os.getpid(),
                        project=metadata.get("project"),
                        service=metadata.get("service"),
                        scope=metadata.get("scope"),
                    )
                    logger.info("Allocated sequential port %s to %s", port, service_name)
                    return port

        raise PortAllocationError(
            f"Failed to allocate port for {service_name!r} after {self.max_allocation_attempts} attempts",
        )

    def _get_os_assigned_port(self) -> int | None:
        """
        Ask the operating system to provide an unused port number.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(("127.0.0.1", 0))
                return sock.getsockname()[1]
        except OSError:
            return None

    def _is_our_service_instance(self, process_info: dict, service_name: str) -> bool:
        """
        Heuristically determine whether ``process_info`` represents a stale service instance.
        """
        cmdline = process_info.get("cmdline", "").lower()
        process_name = process_info.get("name", "").lower()

        record = self._services.get(service_name)
        if record and record.pid == process_info.get("pid"):
            return True

        indicators = [
            service_name.lower(),
            "zen-mcp",
            "atoms-mcp",
            "atoms",
            "mcp-server",
            "fastmcp",
            "server.py",
            "python -m server",
        ]

        return any(indicator in cmdline or indicator in process_name for indicator in indicators)

    # --------------------------------------------------------------------- #
    # Convenience helpers
    # --------------------------------------------------------------------- #

    def release_port(self, service_name: str) -> bool:
        """
        Free the port currently allocated to ``service_name``.
        """
        record = self.get_service(service_name)
        if record is None:
            return False

        logger.info("Releasing port %s for service %s", record.assigned_port, service_name)
        return self.unregister_service(service_name)

    def get_service_port(self, service_name: str) -> int | None:
        """
        Return the port assigned to ``service_name`` if the service exists.
        """
        record = self.get_service(service_name)
        return record.assigned_port if record else None

    def list_allocated_services(self) -> dict[str, int]:
        """
        Produce a map of service names to their allocated ports.
        """
        return {
            name: info.assigned_port
            for name, info in self.get_all_services().items()
        }

    @staticmethod
    def allocate_free_port(preferred: int | None = None, logger_obj: logging.Logger | None = None) -> int:
        """
        Allocate a free port with lightweight conflict handling.

        Args:
            preferred: Optional caller-specified port to attempt first.
            logger_obj: Optional logger used for informational messages.

        Returns:
            The port number that was successfully bound and released.

        Raises:
            RuntimeError: If no free port could be discovered.
        """
        log = logger_obj or logger

        def try_bind(port: int) -> int | None:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                bind_port = port if port and port > 0 else 0
                sock.bind(("", bind_port))
                actual = sock.getsockname()[1]
                sock.close()
                return actual
            except OSError:
                return None

        if preferred and preferred > 0:
            preferred_actual = try_bind(preferred)
            if preferred_actual:
                log.info("Port allocation: using preferred port %s", preferred_actual)
                return preferred_actual
            log.warning("Port allocation: preferred port %s unavailable, falling back", preferred)

        os_port = try_bind(0)
        if os_port:
            log.info("Port allocation: OS assigned port %s", os_port)
            return os_port

        raise RuntimeError("Failed to allocate a free port")
