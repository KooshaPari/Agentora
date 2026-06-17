"""
Tunnel management methods (refactored from kinfra/tunnels.py).
"""

from __future__ import annotations

import logging
import warnings
from typing import Any

from ..exceptions import TunnelError
from ..tunnel_sync import TunnelInfo, TunnelManager

logger = logging.getLogger(__name__)

LEGACY_TUNNEL_REMOVAL_DATE = "2025-03-31"


class TunnelsMixin:
    def create_tunnel(
        self,
        service_name: str,
        port: int,
        domain: str | None = None,
        path: str = "/",
    ) -> TunnelInfo:
        """
        Create a tunnel for a service with automatic configuration (canonical).
        """
        try:
            if domain:
                tunnel_manager = TunnelManager(registry=self.registry, domain=domain)  # type: ignore[attr-defined]
                tunnel_info = tunnel_manager.start_tunnel(service_name, port, path=path)
            else:
                tunnel_manager = self.tunnel_manager  # type: ignore[attr-defined]
                tunnel_info = tunnel_manager.start_tunnel(service_name, port, path=path)
            self._managed_services.add(service_name)  # type: ignore[attr-defined]
            if tunnel_manager and hasattr(tunnel_manager, "_log_tunnel"):
                tunnel_manager._log_tunnel(
                    "Started tunnel for '%s': https://%s",
                    service_name,
                    tunnel_info.hostname,
                    verbose=True,
                )
            else:
                logger.info(
                    "Started tunnel for '%s': https://%s", service_name, tunnel_info.hostname,
                )
            return tunnel_info
        except Exception as e:
            logger.exception("Failed to start tunnel for '%s': %s", service_name, e)
            raise TunnelError(f"Tunnel creation failed for '{service_name}': {e}")

    def start_tunnel(
        self,
        service_name: str,
        port: int,
        domain: str | None = None,
        path: str = "/",
    ) -> TunnelInfo:
        """
        Legacy alias for create_tunnel (deprecated).
        """
        logger.warning(
            "start_tunnel is deprecated; switch to create_tunnel() by %s to avoid breakage",
            LEGACY_TUNNEL_REMOVAL_DATE,
        )
        warnings.warn(
            f"start_tunnel() is deprecated and will be removed after {LEGACY_TUNNEL_REMOVAL_DATE}; use create_tunnel() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.create_tunnel(service_name, port, domain=domain, path=path)

    def create_quick_tunnel(
        self, service_name: str, port: int, protocol: str = "http",
    ) -> TunnelInfo:
        try:
            if not self.registry.get_service(service_name):  # type: ignore[attr-defined]
                self.registry.register_service(service_name, port)  # type: ignore[attr-defined]
            manager = self.tunnel_manager  # type: ignore[attr-defined]
            info = manager.create_quick_tunnel(service_name, port, protocol=protocol)  # type: ignore[attr-defined]
            self._managed_services.add(service_name)  # type: ignore[attr-defined]
            if hasattr(manager, "_log_tunnel"):
                manager._log_tunnel(
                    "Quick tunnel for '%s': https://%s", service_name, info.hostname, verbose=True,
                )
            else:
                logger.info("Quick tunnel for '%s': https://%s", service_name, info.hostname)
            return info
        except Exception as e:
            logger.exception("Failed to create quick tunnel for '%s': %s", service_name, e)
            raise TunnelError(f"Quick tunnel creation failed for '{service_name}': {e}")

    def create_persistent_tunnel(
        self, service_name: str, port: int, domain: str | None = None, path: str = "/",
    ) -> TunnelInfo:
        return self.create_tunnel(service_name, port, domain=domain, path=path)

    def get_public_url(self, service_name: str) -> str | None:
        return self.tunnel_manager.get_service_url(service_name)  # type: ignore[attr-defined]

    # ---- Utilities ----

    def get_service_url(self, service_name: str) -> str | None:
        logger.warning(
            "get_service_url is deprecated; migrate to get_public_url() by %s",
            LEGACY_TUNNEL_REMOVAL_DATE,
        )
        warnings.warn(
            f"get_service_url() is deprecated and will be removed after {LEGACY_TUNNEL_REMOVAL_DATE}; use get_public_url() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.get_public_url(service_name)

    def get_tunnel_status(self, service_name: str) -> dict[str, Any]:
        return self.tunnel_manager.get_tunnel_status(service_name)  # type: ignore[attr-defined]

    def stop_tunnel(self, service_name: str) -> bool:
        try:
            return self.tunnel_manager.stop_tunnel(service_name)  # type: ignore[attr-defined]
        except Exception:
            logger.warning("Failed to stop tunnel for '%s'", service_name)
            return False

    def stop_all_tunnels(self) -> None:
        self.tunnel_manager.cleanup_all()  # type: ignore[attr-defined]
