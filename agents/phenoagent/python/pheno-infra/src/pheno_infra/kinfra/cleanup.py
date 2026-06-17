"""
Per-service cleanup and environment wrappers (split from kinfra/kinfra.py).
"""

from __future__ import annotations

import logging
import time

from ..utils.process import get_port_occupant, terminate_process

logger = logging.getLogger(__name__)


class CleanupMixin:
    def cleanup(self, service_name: str) -> bool:
        """
        Clean up resources for a specific service.
        """
        logger.info("Cleaning up service '%s'", service_name)
        success = True

        service_info = self.allocator.registry.get_service(service_name)  # type: ignore[attr-defined]
        port = service_info.assigned_port if service_info else None

        try:
            if not self.tunnel_manager.stop_tunnel(service_name):  # type: ignore[attr-defined]
                logger.warning("Failed to stop tunnel for '%s'", service_name)
                success = False
        except Exception as e:
            logger.exception("Error stopping tunnel for '%s': %s", service_name, e)
            success = False

        if port:
            try:
                occupant = get_port_occupant(port)
                if occupant and occupant.get("pid"):
                    pid = occupant["pid"]
                    logger.info(
                        "Terminating process %s using port %s for '%s'", pid, port, service_name,
                    )
                    if terminate_process(pid):
                        time.sleep(0.5)
                        logger.info("Successfully terminated process %s", pid)
                    else:
                        logger.warning("Failed to terminate process %s", pid)
                        success = False
            except Exception as e:
                logger.exception("Error terminating process for '%s': %s", service_name, e)
                success = False

        try:
            if not self.allocator.release_port(service_name):  # type: ignore[attr-defined]
                logger.warning("Failed to release port for '%s'", service_name)
                success = False
        except Exception as e:
            logger.exception("Error releasing port for '%s': %s", service_name, e)
            success = False

        self._managed_services.discard(service_name)  # type: ignore[attr-defined]

        if success:
            logger.info("Successfully cleaned up service '%s'", service_name)
        return success

    # allocate_and_tunnel wrapper kept in wrappers mixin
