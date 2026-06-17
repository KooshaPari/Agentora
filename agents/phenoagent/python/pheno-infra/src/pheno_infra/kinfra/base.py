"""
Base KInfra initialization and lifecycle helpers (split from kinfra/kinfra.py).
"""

from __future__ import annotations

import atexit
import logging
import os
import signal
from typing import TYPE_CHECKING, Self

from ..exceptions import TunnelError
from ..port_registry import PortRegistry
from ..smart_allocator import SmartPortAllocator
from ..tunnel_sync import TunnelManager
from ..utils.process import get_port_occupant, terminate_process

if TYPE_CHECKING:
    from collections.abc import Iterable

logger = logging.getLogger(__name__)


class BaseKInfra:
    """
    Core wiring and lifecycle primitives for KInfra.
    """

    def __init__(self, domain: str = "kooshapari.com", config_dir: str | None = None) -> None:
        self.domain = domain
        self.config_dir = config_dir

        # Initialize components
        self.registry = PortRegistry(config_dir=config_dir)
        self.allocator = SmartPortAllocator(registry=self.registry)
        self.tunnel_manager = TunnelManager(registry=self.registry, domain=domain)

        # Track managed services for cleanup
        self._managed_services: set[str] = set()
        self._cleanup_registered = False

        # Register cleanup handlers only if not already registered
        if not getattr(BaseKInfra, "_global_cleanup_registered", False):
            atexit.register(self._cleanup_on_exit)
            signal.signal(signal.SIGTERM, self._cleanup_on_signal)
            signal.signal(signal.SIGINT, self._cleanup_on_signal)
            BaseKInfra._global_cleanup_registered = True
            logger.debug("Registered KInfra cleanup handlers")

        # Clean up any stale processes from previous runs
        self._cleanup_stale_processes()

        logger.info(f"KInfra initialized for domain: {domain}")

    # ----- Lifecycle & cleanup -----

    def cleanup_all(self) -> None:
        """
        Clean up all managed services and resources.
        """
        logger.info("Cleaning up all KInfra resources")

        # Clean up managed services
        for service_name in list(self._managed_services):
            try:
                self.cleanup(service_name)
            except Exception as e:
                logger.exception("Error cleaning up service '%s': %s", service_name, e)

        # Clean up tunnel manager
        try:
            self.tunnel_manager.cleanup_all()
        except Exception as e:
            logger.exception("Error cleaning up tunnel manager: %s", e)

        self._managed_services.clear()
        logger.info("KInfra cleanup completed")

    def _cleanup_stale_processes(self) -> None:
        """
        Best‑effort cleanup of stale processes from previous runs on startup.
        """
        logger.info("Checking for stale processes from previous runs...")

        stale_count = 0
        domain_lower = (self.domain or "").lower()
        apply_domain_filter = bool(domain_lower)
        domain_tokens = {
            token
            for token in {
                domain_lower,
                domain_lower.replace(".", "-"),
                domain_lower.split(".")[0] if "." in domain_lower else domain_lower,
            }
            if token
        }

        def _matches_domain(hostname: str | None) -> bool:
            if not apply_domain_filter or not hostname:
                return False
            value = hostname.lower()
            return value == domain_lower or value.endswith(f".{domain_lower}")

        # Access private services map conservatively
        for service_name, service_info in list(self.registry._services.items()):  # type: ignore[attr-defined]
            port = service_info.assigned_port

            occupant = get_port_occupant(port)
            if not occupant:
                logger.debug(
                    "Port %s for '%s' has no detectable occupant; preserving registry entry",
                    port,
                    service_name,
                )
                continue

            pid = occupant.get("pid")
            cmdline = occupant.get("cmdline", "").lower()
            service_domain_match = not apply_domain_filter

            if apply_domain_filter:
                if _matches_domain(getattr(service_info, "tunnel_hostname", None)):
                    service_domain_match = True
                else:
                    config_path = (getattr(service_info, "config_path", None) or "").lower()
                    service_name_lower = service_name.lower()
                    for token in domain_tokens:
                        if token in config_path or token in service_name_lower or token in cmdline:
                            service_domain_match = True
                            break

            if not service_domain_match:
                logger.debug(
                    "Skipping cleanup for %s (domain mismatch for %s)",
                    service_name,
                    self.domain,
                )
                continue

            stale_indicators = {
                "mcp",
                "fastmcp",
                "server.py",
                "python -m server",
                service_name.lower(),
            }
            stale_indicators.update(domain_tokens)
            is_stale = any(ind and ind in cmdline for ind in stale_indicators)

            if is_stale and pid:
                logger.info(
                    "Found stale process %s on port %s for '%s', terminating...",
                    pid,
                    port,
                    service_name,
                )
                if terminate_process(pid):
                    import time as _t

                    _t.sleep(0.3)
                    stale_count += 1
                    logger.info("Successfully terminated stale process %s", pid)
                    self.registry.unregister_service(service_name)
                else:
                    logger.warning("Failed to terminate stale process %s", pid)

        if stale_count > 0:
            logger.info("Cleaned up %d stale process(es) from previous runs", stale_count)
        else:
            logger.debug("No stale processes found")

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
            # Imported at call time to avoid hard dependency when not installed
            from pheno.infra.tunneling import (
                cleanup_runtime_environment,  # type: ignore
            )

            stats = cleanup_runtime_environment(
                grace_period=grace_period,
                force_kill=force_kill,
                exclude_pids=exclude_pids,
            )
            logger.info("Cloudflared cleanup summary: %s", stats)
            return stats
        except ImportError as exc:  # pragma: no cover - optional path
            logger.warning("Runtime cleanup helpers unavailable: %s", exc)
            return {}
        except Exception as exc:
            logger.exception("Error during runtime environment cleanup: %s", exc)
            raise TunnelError(f"Runtime cleanup failed: {exc}")

    # ----- Process exit/signal hooks -----

    def _cleanup_on_exit(self) -> None:
        try:
            self.cleanup_all()
        except Exception as e:
            logger.exception("Error during exit cleanup: %s", e)

    def _cleanup_on_signal(self, signum, frame) -> None:  # pragma: no cover - signal path
        logger.info("Received signal %s, cleaning up...", signum)
        try:
            self.cleanup_all()
        except Exception as e:
            logger.exception("Error during signal cleanup: %s", e)
        signal.signal(signum, signal.SIG_DFL)
        os.kill(os.getpid(), signum)

    # ----- Context manager -----

    def __enter__(self) -> Self:  # pragma: no cover - convenience
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # pragma: no cover - convenience
        self.cleanup_all()
