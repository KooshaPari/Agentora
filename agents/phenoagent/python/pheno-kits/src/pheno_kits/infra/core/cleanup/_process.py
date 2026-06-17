"""Process discovery and cleanup logic."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Sequence

from pheno.kits.infra.core.cleanup._constants import (
    DNS_PATTERNS,
    PSUTIL_AVAILABLE,
    RELATED_SERVICE_PATTERNS,
    TUNNEL_PATTERNS,
)
from pheno.kits.infra.core.cleanup._models import (
    CleanupConfig,
    CleanupStats,
    ProcessDiscoveryRecord,
)

logger = logging.getLogger(__name__)


class _FallbackProcessMetadata:
    """Fallback metadata container used when the governance package is missing."""

    project: str | None = None
    service: str | None = None
    scope: str | None = None
    resource_type: str | None = None
    tags: set[str]
    created_at: float
    last_seen: float
    pid: int | None = None
    parent_pid: int | None = None
    command_line: list[str]
    environment: dict[str, str]

    def __init__(
        self,
        project: str | None = None,
        service: str | None = None,
        scope: str | None = None,
        resource_type: str | None = None,
        tags: set[str] | None = None,
        created_at: float | None = None,
        last_seen: float | None = None,
        pid: int | None = None,
        parent_pid: int | None = None,
        command_line: list[str] | None = None,
        environment: dict[str, str] | None = None,
    ) -> None:
        import time

        self.project = project
        self.service = service
        self.scope = scope
        self.resource_type = resource_type
        self.tags = tags or set()
        self.created_at = created_at or time.time()
        self.last_seen = last_seen or time.time()
        self.pid = pid
        self.parent_pid = parent_pid
        self.command_line = command_line or []
        self.environment = environment or {}


try:
    from pheno.infra.cleanup_policies import CleanupPolicyManager, ResourceType
except ImportError:  # pragma: no cover - optional runtime dependency
    CleanupPolicyManager = None  # type: ignore
    ResourceType = None  # type: ignore

try:
    from pheno.infra.process_governance import (
        ProcessGovernanceConfig,
        ProcessGovernanceManager,
        ProcessMetadata,
    )
except ImportError:  # pragma: no cover - optional runtime dependency
    ProcessGovernanceConfig = None  # type: ignore
    ProcessGovernanceManager = None  # type: ignore
    ProcessMetadata = _FallbackProcessMetadata  # type: ignore


class ProcessCleanup:
    """Handles process discovery, filtering, and termination."""

    def __init__(
        self,
        config: CleanupConfig,
        policy_manager: Any,
        governance_manager: Any,
    ) -> None:
        self.config = config
        self._policy_manager = policy_manager
        self._governance_manager = governance_manager
        self._current_pid = os.getpid()

    def cleanup_processes(self, service_name: str) -> CleanupStats:
        """Run all configured process cleanup stages."""
        stats = CleanupStats()

        if not PSUTIL_AVAILABLE:
            logger.warning("psutil not available, skipping process cleanup")
            return stats

        if self.config.cleanup_tunnels:
            stats.merge(
                self._cleanup_by_patterns(TUNNEL_PATTERNS, "tunnel", use_sigkill=True),
            )

        if self.config.cleanup_dns_processes:
            stats.merge(self._cleanup_by_patterns(DNS_PATTERNS, "dns server"))

        if self.config.cleanup_related_services:
            stats.merge(
                self._cleanup_by_patterns(RELATED_SERVICE_PATTERNS, "related service"),
            )

        if self.config.cleanup_shared_resources:
            stats.merge(self._cleanup_shared_resources())

        policy_patterns = self._policy_patterns_for(service_name)
        if policy_patterns:
            stats.merge(self._cleanup_by_patterns(policy_patterns, "policy process"))

        return stats

    def _cleanup_shared_resources(self) -> CleanupStats:
        stats = CleanupStats()
        temp_dirs = [
            Path("/tmp"),
            Path.home() / ".cache",
            Path.home() / ".kinfra",
        ]

        for temp_dir in temp_dirs:
            if not temp_dir.exists():
                continue
            for pattern in ("kinfra_*", "atoms_*", "mcp_*", "pheno_*"):
                for file_path in temp_dir.glob(pattern):
                    try:
                        if file_path.is_file():
                            file_path.unlink()
                    except Exception:
                        stats.errors += 1

        return stats

    def _policy_patterns_for(self, service_name: str) -> list[str]:
        if not self._policy_manager or ResourceType is None:
            return []

        patterns: list[str] = []
        project_name = self.config.project or service_name

        try:
            process_enum = getattr(ResourceType, "PROCESS", None)
            tunnel_enum = getattr(ResourceType, "TUNNEL", None)
            if process_enum:
                patterns.extend(
                    self._policy_manager.get_cleanup_patterns(
                        project_name,
                        process_enum,
                    ),
                )
            if tunnel_enum and self.config.cleanup_tunnels:
                patterns.extend(
                    self._policy_manager.get_cleanup_patterns(
                        project_name,
                        tunnel_enum,
                    ),
                )
        except Exception as exc:  # pragma: no cover - defensive coding
            logger.debug("Failed to load policy patterns: %s", exc)

        return [pattern for pattern in patterns if pattern]

    def cleanup_governed_processes(
        self,
        project: str | None = None,
        service: str | None = None,
        scope: str | None = None,
        cleanup_stale: bool = False,
    ) -> dict[str, Any]:
        """Invoke metadata-aware cleanup through the governance manager."""
        if not self._governance_manager:
            return {}

        results: dict[str, Any] = {}

        if project:
            results["project"] = self._governance_manager.cleanup_project_processes(
                project,
            )

        if service:
            results["service"] = self._governance_manager.cleanup_service_processes(
                service,
            )

        if cleanup_stale:
            results["stale"] = self._governance_manager.cleanup_stale_processes()

        return results

    def discover_processes(
        self,
        patterns: Sequence[str] | None = None,
        include_ports: bool = True,
    ) -> list[ProcessDiscoveryRecord]:
        """Return processes whose names or command lines match ``patterns``."""
        import psutil

        if not PSUTIL_AVAILABLE:
            logger.warning("psutil not available - process discovery skipped")
            return []

        patterns_lower = [p.lower() for p in patterns or []]
        discoveries: list[ProcessDiscoveryRecord] = []

        for proc in psutil.process_iter(
            ["pid", "name", "cmdline", "status", "username"],
        ):
            try:
                pid = proc.info.get("pid")
                if pid is None:
                    continue
                name = (proc.info.get("name") or "").lower()
                cmdline = [str(part) for part in proc.info.get("cmdline") or []]
                cmdline_str = " ".join(cmdline).lower()

                if patterns_lower:
                    if not any(
                        pattern in name or pattern in cmdline_str
                        for pattern in patterns_lower
                    ):
                        continue

                ports: list[int] = []
                if include_ports:
                    ports = self._collect_ports(proc)

                record = ProcessDiscoveryRecord(
                    pid=pid,
                    name=proc.info.get("name") or "",
                    cmdline=cmdline,
                    ports=ports,
                    status=proc.info.get("status") or "",
                    username=proc.info.get("username"),
                    create_time=self._safe_call(proc, "create_time"),
                )
                discoveries.append(record)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception as exc:  # pragma: no cover - defensive coding
                logger.debug("Process discovery error: %s", exc)
                continue

        return discoveries

    def register_process_metadata(self, pid: int, metadata: Any) -> None:
        """Register metadata with the governance manager when available."""
        if not self._governance_manager:
            return
        try:
            self._governance_manager.register_process(pid, metadata)
        except Exception as exc:  # pragma: no cover - defensive coding
            logger.debug("Failed to register metadata for PID %s: %s", pid, exc)

    def unregister_process_metadata(self, pid: int) -> None:
        """Remove metadata tracking for a PID when governance is enabled."""
        if not self._governance_manager:
            return
        try:
            self._governance_manager.unregister_process(pid)
        except Exception as exc:  # pragma: no cover - defensive coding
            logger.debug("Failed to unregister metadata for PID %s: %s", pid, exc)

    def _cleanup_by_patterns(
        self,
        patterns: Sequence[str],
        process_type: str,
        use_sigkill: bool = False,
        exclude_patterns: Sequence[str] | None = None,
    ) -> CleanupStats:
        import psutil

        stats = CleanupStats()
        if not patterns:
            return stats

        patterns_lower = [pattern.lower() for pattern in patterns]
        exclude_lower = [pattern.lower() for pattern in (exclude_patterns or [])]
        matched_processes: list[psutil.Process] = []

        for proc in psutil.process_iter(["pid", "name", "cmdline", "ppid"]):
            stats.inspected += 1
            try:
                pid = proc.info.get("pid")
                if pid is None or pid == self._current_pid:
                    stats.skipped += 1
                    continue

                if proc.info.get("ppid") == self._current_pid:
                    stats.skipped += 1
                    continue

                name = (proc.info.get("name") or "").lower()
                cmdline = " ".join(
                    str(arg) for arg in proc.info.get("cmdline") or []
                ).lower()

                if any(
                    exclude in name or exclude in cmdline for exclude in exclude_lower
                ):
                    stats.skipped += 1
                    continue

                if any(
                    pattern in name or pattern in cmdline for pattern in patterns_lower
                ):
                    matched_processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                stats.skipped += 1
            except Exception as exc:  # pragma: no cover - defensive coding
                logger.debug("Error while scanning process: %s", exc)
                stats.errors += 1

        if matched_processes:
            self._terminate_processes(
                matched_processes,
                process_type,
                stats,
                use_sigkill,
            )

        return stats

    def _terminate_processes(
        self,
        processes: Any,
        process_type: str,
        stats: CleanupStats,
        use_sigkill: bool = False,
    ) -> None:
        import psutil

        for proc in processes:
            try:
                if use_sigkill:
                    proc.kill()
                else:
                    proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                stats.skipped += 1
            except Exception as exc:
                logger.warning(
                    "Failed to terminate %s %s: %s",
                    process_type,
                    proc.pid,
                    exc,
                )
                stats.errors += 1

        try:
            timeout = 2.0 if use_sigkill else self.config.grace_period
            gone, alive = psutil.wait_procs(list(processes), timeout=timeout)
            stats.terminated += len(gone)

            if alive and self.config.force_kill and not use_sigkill:
                for proc in alive:
                    try:
                        proc.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                    except Exception as exc:
                        logger.warning(
                            "Failed to force kill %s %s: %s",
                            process_type,
                            proc.pid,
                            exc,
                        )
                        stats.errors += 1

                gone_after_kill, still_alive = psutil.wait_procs(alive, timeout=2.0)
                stats.force_killed += len(gone_after_kill)
                for proc in still_alive:
                    logger.error(
                        "%s %s survived termination attempts",
                        process_type,
                        proc.pid,
                    )
                    stats.errors += 1
        except Exception as exc:  # pragma: no cover - defensive coding
            logger.error(
                "Error while waiting for %s termination: %s",
                process_type,
                exc,
            )
            stats.errors += 1

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

    @staticmethod
    def _collect_ports(proc: Any) -> list[int]:
        import psutil

        ports: set[int] = set()
        for conn in ProcessCleanup._collect_connections(proc):
            local = getattr(conn, "laddr", None)
            port = getattr(local, "port", None) if local else None
            if port:
                ports.add(port)
        return sorted(ports)

    @staticmethod
    def _safe_call(proc: Any, attribute: str) -> float | None:
        import psutil

        try:
            method = getattr(proc, attribute)
            return float(method())  # type: ignore[call-arg]
        except (AttributeError, psutil.AccessDenied, psutil.NoSuchProcess):
            return None
        except Exception:  # pragma: no cover - defensive coding
            return None
