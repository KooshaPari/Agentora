"""
Port allocation and related helpers (split from kinfra/kinfra.py).
"""

from __future__ import annotations

import logging

from ..exceptions import PortAllocationError

logger = logging.getLogger(__name__)


class PortsMixin:
    def allocate_port(
        self,
        service_name: str,
        preferred_port: int | None = None,
        project: str | None = None,
        service_type: str | None = None,
        scope: str | None = None,
        **kwargs,
    ) -> int:
        """
        Allocate a port for a service with intelligent conflict resolution.

        Args:
            service_name: Name of the service
            preferred_port: Preferred port number (optional)
            project: Optional project identifier for multi-tenant coordination
            service_type: Optional service type/category for grouping related services
            scope: Optional scope identifier (e.g., 'shared', 'isolated', 'global')
            **kwargs: Additional arguments (for compatibility)
        """
        try:
            port = self.allocator.allocate_port(  # type: ignore[attr-defined]
                service_name,
                preferred_port,
                project=project,
                service=service_type,
                scope=scope,
            )
            self._managed_services.add(service_name)  # type: ignore[attr-defined]
            logger.info("Allocated port %s for service '%s'", port, service_name)
            return port
        except Exception as e:
            logger.exception("Failed to allocate port for '%s': %s", service_name, e)
            raise PortAllocationError(f"Port allocation failed for '{service_name}': {e}")

    # Aliases maintained in wrappers for API stability
