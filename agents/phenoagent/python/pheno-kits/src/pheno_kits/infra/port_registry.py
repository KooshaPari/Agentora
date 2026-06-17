"""
Port Registry - Persistent port management with service tracking.

Provides centralized port allocation and service lifecycle management
with JSON-based persistence and atomic updates.
"""

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
    """
    Information about a registered service.
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
        """
        Check if service info is stale based on last_seen timestamp.
        """
        return time.time() - self.last_seen > max_age_seconds

    def update_seen(self):
        """
        Update the last_seen timestamp.
        """
        self.last_seen = time.time()


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
        """
        Load registry from disk with file locking.
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
                        # Filter out unknown fields to handle schema evolution
                        valid_fields = {
                            k: v for k, v in info_dict.items()
                            if k in ServiceInfo.__dataclass_fields__
                        }
                        service_info = ServiceInfo(**valid_fields)
                        self._services[name] = service_info
                    except (TypeError, ValueError) as e:
                        logger.warning(f"Skipping invalid service entry {name}: {e}")

        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to load port registry: {e}. Starting with empty registry.")
            self._services = {}

    def _save_registry(self):
        """
        Save registry to disk with atomic write and file locking.
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
        try:
            with open(temp_file, "w") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive lock for writing
                json.dump(data, f, indent=2)
                f.flush()

            # Atomic rename
            temp_file.replace(self.registry_file)
            logger.debug(f"Registry saved with {len(self._services)} services")

        except OSError as e:
            if temp_file.exists():
                temp_file.unlink()
            raise ConfigurationError(f"Failed to save port registry: {e}")

    def _cleanup_stale_entries(self, max_age_seconds: int = 86400):  # 24 hours
        """
        Remove stale service entries.
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
        """
        Register a service with the registry.
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
        """
        Get service information by name.
        """
        service_info = self._services.get(service_name)
        if service_info:
            service_info.update_seen()
            self._save_registry()
        return service_info

    def update_service(self, service_name: str, **kwargs) -> ServiceInfo | None:
        """
        Update service information.
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
        """
        Unregister a service from the registry.
        """
        if service_name in self._services:
            del self._services[service_name]
            self._save_registry()
            logger.info(f"Unregistered service '{service_name}'")
            return True
        return False

    def get_all_services(self) -> dict[str, ServiceInfo]:
        """
        Get all registered services.
        """
        return self._services.copy()

    def get_allocated_ports(self) -> set[int]:
        """
        Get all currently allocated ports.
        """
        return {info.assigned_port for info in self._services.values()}

    def is_port_registered(self, port: int) -> str | None:
        """
        Check if a port is registered to a service.
        """
        for service_name, info in self._services.items():
            if info.assigned_port == port:
                return service_name
        return None

    def get_canonical_port(self, service_name: str) -> int | None:
        """
        Get the canonical port for a service (preferred port for future runs).
        """
        service_info = self.get_service(service_name)
        return service_info.assigned_port if service_info else None

    def validate_port_range(self, port: int) -> bool:
        """
        Validate if port is in acceptable range.
        """
        if port in self.reserved_ports:
            return False

        min_port, max_port = self.default_port_range
        return min_port <= port <= max_port
