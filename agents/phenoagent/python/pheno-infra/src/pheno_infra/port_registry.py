"""Persistent port management with service lifecycle tracking.

The registry coordinates port reservations across multiple local processes, persisting
assignments to disk so subsequent invocations observe a consistent view. It implements
stale-entry cleanup, file-based locking for atomic writes, and convenience helpers for
tunnel metadata used by the TUI stack.
"""

import contextlib
import fcntl
import json
import logging
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from .exceptions import ConfigurationError

logger = logging.getLogger(__name__)


@dataclass
class ServiceInfo:
    """Typed container describing a service registered with the port registry.

    Attributes:
        service_name: Logical name of the service (used as the registry key).
        assigned_port: TCP port bound by the service.
        pid: Optional process identifier for the running service.
        last_seen: Timestamp of the most recent heartbeat/update.
        tunnel_id: Identifier for an active tunnel (if applicable).
        tunnel_hostname: Hostname exposed by the tunnel provider.
        config_path: Optional filesystem path to the service configuration file.
        created_at: Timestamp marking when the service first registered.
        project: Optional project identifier for multi-tenant coordination.
        service: Optional service type/category for grouping related services.
        scope: Optional scope identifier (e.g., 'shared', 'isolated', 'global').
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

    def __post_init__(self):
        if self.last_seen == 0.0:
            self.last_seen = time.time()
        if self.created_at == 0.0:
            self.created_at = time.time()

    def is_stale(self, max_age_seconds: int = 3600) -> bool:
        """Determine if the service record has expired based on ``last_seen``.

        Args:
            max_age_seconds: Maximum allowed inactivity window before the entry
                is considered stale.

        Returns:
            ``True`` when the record exceeds the inactivity window.
        """
        return time.time() - self.last_seen > max_age_seconds

    def update_seen(self):
        """Refresh the ``last_seen`` timestamp to the current time.

        Returns:
            Updated timestamp value, enabling fluent-style chaining when desired.
        """
        self.last_seen = time.time()
        return self.last_seen


class PortRegistry:
    """Persistent port registry with atomic updates and conflict resolution.

    Manages service-to-port mappings with:
    - JSON persistence with file locking
    - Automatic conflict detection
    - Stale entry cleanup
    - Port range management
    """

    def __init__(self, config_dir: Path | None = None):
        self.config_dir = config_dir or Path.home() / ".kinfra"
        self.config_dir.mkdir(exist_ok=True, parents=True)
        self.registry_file = self.config_dir / "port_registry.json"

        # Port allocation settings
        self.default_port_range = (8000, 65535)  # Allow full ephemeral port range
        self.reserved_ports = {22, 80, 443, 3306, 5432, 6379}  # Common system ports

        self._services: dict[str, ServiceInfo] = {}
        self._load_registry()

    def _load_registry(self):
        """Hydrate the in-memory registry state from the persisted JSON file.

        The method acquires a shared lock so concurrent readers avoid interfering with
        writers, and gracefully skips malformed entries to keep the registry usable even
        when partial corruption occurs.
        """
        if not self.registry_file.exists():
            self._services = {}
            return

        try:
            with open(self.registry_file) as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)  # Shared lock for reading
                data = json.load(f)

                self._services = {}
                for name, info_dict in data.get("services", {}).items():
                    try:
                        service_info = ServiceInfo(**info_dict)
                        self._services[name] = service_info
                    except (TypeError, ValueError) as e:
                        logger.warning(f"Skipping invalid service entry {name}: {e}")

        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to load port registry: {e}. Starting with empty registry.")
            self._services = {}

    def _save_registry(self):
        """Persist the registry to disk using an atomic rename strategy.

        Steps:
            1. Remove stale entries to avoid propagating dead registrations.
            2. Serialize the registry into a temporary file under an exclusive lock.
            3. Atomically replace the target file with the fresh snapshot.

        Raises:
            ConfigurationError: If writing to disk fails for any reason.
        """
        # Clean up stale entries before saving
        self._cleanup_stale_entries()

        data = {
            "version": "1.0",
            "timestamp": time.time(),
            "services": {name: asdict(info) for name, info in self._services.items()},
        }

        # Atomic write with temp file and rename
        temp_file = self.registry_file.with_suffix(".tmp")
        import os

        # Use a lock file to prevent concurrent writes
        lock_file = self.registry_file.with_suffix(".lock")

        # Retry mechanism for lock acquisition
        max_retries = 3
        retry_delay = 0.1

        for attempt in range(max_retries):
            try:
                # Create lock file and acquire exclusive lock
                with open(lock_file, "w") as lock_f:
                    fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

                    # Write to temp file
                    with open(temp_file, "w") as f:
                        json.dump(data, f, indent=2)
                        f.flush()
                        os.fsync(f.fileno())  # Ensure data is written to disk

                    # Atomic rename - this should be atomic on most filesystems
                    if temp_file.exists():
                        os.rename(str(temp_file), str(self.registry_file))
                        logger.debug(f"Registry saved with {len(self._services)} services")
                        return  # Success, exit the retry loop
                    raise OSError(f"Temp file {temp_file} was deleted before rename")

            except OSError as e:
                if "Resource temporarily unavailable" in str(e) and attempt < max_retries - 1:
                    # Lock is held by another process, wait and retry
                    logger.debug(f"Lock held by another process, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                # Clean up temp file if it exists
                if temp_file.exists():
                    with contextlib.suppress(OSError):
                        temp_file.unlink()
                logger.exception(f"Failed to save port registry: {e}")
                logger.exception(f"Temp file exists: {temp_file.exists()}")
                logger.exception(f"Target file exists: {self.registry_file.exists()}")
                raise ConfigurationError(f"Failed to save port registry: {e}")
            finally:
                # Clean up lock file
                if lock_file.exists():
                    with contextlib.suppress(OSError):
                        lock_file.unlink()

    def _cleanup_stale_entries(self, max_age_seconds: int = 86400):  # 24 hours
        """Expire services that have not updated their heartbeat within
        ``max_age_seconds``.

        Args:
            max_age_seconds: Threshold in seconds after which entries are removed.
        """
        stale_services = [
            name for name, info in self._services.items() if info.is_stale(max_age_seconds)
        ]

        for service_name in stale_services:
            logger.info(f"Removing stale registry entry: {service_name}")
            del self._services[service_name]

    def register_service(
        self,
        service_name: str,
        port: int,
        pid: int | None = None,
        project: str | None = None,
        service: str | None = None,
        scope: str | None = None,
    ) -> ServiceInfo:
        """Register a service/port pairing and persist the change.

        Args:
            service_name: Logical identifier for the service.
            port: TCP port reserved for the service.
            pid: Optional process identifier to aid cleanup heuristics.
            project: Optional project identifier for multi-tenant coordination.
            service: Optional service type/category for grouping related services.
            scope: Optional scope identifier (e.g., 'shared', 'isolated', 'global').

        Returns:
            Newly created :class:`ServiceInfo` entry.
        """
        service_info = ServiceInfo(
            service_name=service_name,
            assigned_port=port,
            pid=pid,
            project=project,
            service=service,
            scope=scope,
        )

        self._services[service_name] = service_info
        self._save_registry()

        logger.info(f"Registered service '{service_name}' on port {port}")
        return service_info

    def get_service(self, service_name: str) -> ServiceInfo | None:
        """Retrieve service metadata and refresh its heartbeat.

        Args:
            service_name: Registry key that identifies the service.

        Returns:
            Corresponding :class:`ServiceInfo` instance, or ``None`` when the
            service is unknown.
        """
        service_info = self._services.get(service_name)
        if service_info:
            service_info.update_seen()
            self._save_registry()
        return service_info

    def update_service(self, service_name: str, **kwargs) -> ServiceInfo | None:
        """Apply partial updates to a service and persist the mutation.

        Args:
            service_name: Registry key to update.
            **kwargs: Field/value pairs that should be applied to the existing record.

        Returns:
            Updated :class:`ServiceInfo` instance or ``None`` if the service is missing.
        """
        if service_name not in self._services:
            return None

        service_info = self._services[service_name]
        for key, value in kwargs.items():
            if hasattr(service_info, key):
                setattr(service_info, key, value)

        service_info.update_seen()
        self._save_registry()
        return service_info

    def unregister_service(self, service_name: str) -> bool:
        """Remove a service from the registry and persist the change.

        Args:
            service_name: Identifier of the service to delete.

        Returns:
            ``True`` when the service existed and was removed, otherwise ``False``.
        """
        if service_name in self._services:
            del self._services[service_name]
            self._save_registry()
            logger.info(f"Unregistered service '{service_name}'")
            return True
        return False

    def get_all_services(self) -> dict[str, ServiceInfo]:
        """Produce a shallow copy of all registered services.

        Returns:
            Mapping from service names to their :class:`ServiceInfo` entries.
        """
        return self._services.copy()

    def get_allocated_ports(self) -> set[int]:
        """Enumerate all ports currently tracked by the registry.

        Returns:
            Set of port numbers reserved by active services.
        """
        return {info.assigned_port for info in self._services.values()}

    def is_port_registered(self, port: int) -> str | None:
        """Determine whether a port belongs to a known service.

        Args:
            port: TCP port number to check.

        Returns:
            Service name when the port is assigned, otherwise ``None``.
        """
        for service_name, info in self._services.items():
            if info.assigned_port == port:
                return service_name
        return None

    def get_canonical_port(self, service_name: str) -> int | None:
        """Return the previously assigned port for a service.

        This helps services consistently reuse the same port across runs when possible.
        """
        service_info = self.get_service(service_name)
        return service_info.assigned_port if service_info else None

    def validate_port_range(self, port: int) -> bool:
        """Check whether a port falls inside the allowed allocation window.

        Args:
            port: TCP port number under consideration.

        Returns:
            ``True`` if the port is permitted, otherwise ``False``.
        """
        if port in self.reserved_ports:
            return False

        min_port, max_port = self.default_port_range
        return min_port <= port <= max_port
