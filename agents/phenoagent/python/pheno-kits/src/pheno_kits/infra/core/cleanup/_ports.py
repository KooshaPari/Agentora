"""Port cleanup logic."""

from __future__ import annotations

import logging
from typing import Any

from pheno.kits.infra.core.cleanup._constants import PSUTIL_AVAILABLE, PROTECTED_PORTS
from pheno.kits.infra.core.cleanup._models import CleanupConfig

try:
    from shared.resources import get_shared_ports, is_shared_port
except ImportError:  # pragma: no cover - optional during packaging

    def get_shared_ports() -> list[int]:
        return []

    def is_shared_port(port: int) -> bool:
        return False


logger = logging.getLogger(__name__)


class PortCleanup:
    """Handles port scanning and process termination on specific ports."""

    def __init__(
        self,
        config: CleanupConfig,
        resource_registry: Any = None,
    ) -> None:
        self.config = config
        self._resource_registry = resource_registry
        self._protected_ports = set(config.protected_ports or set())
        self._protected_ports.update(PROTECTED_PORTS)
        shared_ports = set(get_shared_ports())
        self._protected_ports.update(shared_ports)

    def cleanup_ports(
        self,
        ports: list[int],
        force: bool = False,
    ) -> dict[str, Any]:
        """Terminate processes bound to the supplied ``ports``."""
        summary: dict[str, Any] = {
            "requested": len(ports),
            "terminated": 0,
            "skipped": 0,
            "errors": 0,
            "details": [],
        }

        if not PSUTIL_AVAILABLE:
            logger.warning("psutil not available, skipping port cleanup")
            summary["errors"] = len(ports)
            return summary

        for port in ports:
            detail: dict[str, Any] = {"port": port, "action": "skipped"}

            if port in self._protected_ports or is_shared_port(port):
                detail["reason"] = "protected port"
                summary["skipped"] += 1
                summary["details"].append(detail)
                continue

            if self._resource_registry and self._resource_registry.is_shared(port):
                detail["reason"] = "shared resource"
                summary["skipped"] += 1
                summary["details"].append(detail)
                continue

            try:
                terminated = self._kill_process_on_port(port, force=force)
                if terminated:
                    detail["action"] = "terminated"
                    summary["terminated"] += 1
                else:
                    detail["reason"] = "no owner found"
                    summary["skipped"] += 1
            except Exception as exc:  # pragma: no cover - defensive coding
                detail["reason"] = str(exc)
                summary["errors"] += 1
            summary["details"].append(detail)

        return summary

    def _kill_process_on_port(self, port: int, force: bool = False) -> bool:
        import psutil

        registry = self._resource_registry
        shared_resource = registry.get_by_port(port) if registry else None  # type: ignore[call-arg]

        for proc in psutil.process_iter(["pid", "name"]):
            try:
                connections = self._collect_connections(proc)
                for conn in connections:
                    local = getattr(conn, "laddr", None)
                    if not local or getattr(local, "port", None) != port:
                        continue

                    if shared_resource and not force:
                        logger.info(
                            "Leaving shared resource %s on port %s (PID %s)",
                            shared_resource.display_name,
                            port,
                            proc.pid,
                        )
                        return False

                    logger.info(
                        "Terminating process %s bound to port %s",
                        proc.pid,
                        port,
                    )
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                        return True
                    except psutil.TimeoutExpired:
                        logger.warning(
                            "Force killing process %s on port %s",
                            proc.pid,
                            port,
                        )
                        proc.kill()
                        proc.wait(timeout=5)
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    @staticmethod
    def _collect_connections(proc: Any) -> list[Any]:
        import psutil

        try:
            return list(proc.net_connections())  # type: ignore[attr-defined]
        except AttributeError:
            pass
        except psutil.AccessDenied:
            pass

        for attr in ("connections", "get_connections"):
            try:
                method = getattr(proc, attr)
                return list(method())
            except (AttributeError, psutil.AccessDenied):
                continue
        return []
