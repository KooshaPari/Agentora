"""
Process Governance - Enhanced process management with metadata-based cleanup

Provides sophisticated process management with:
- Metadata-based process identification and cleanup
- Project and service-specific process tracking
- Configurable cleanup policies
- Process lifecycle management
- Integration with existing ProcessCleanupManager
"""

import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class CleanupPolicy(Enum):
    """
    Cleanup policy for process management.
    """

    CONSERVATIVE = "conservative"
    """
    Only clean up processes that are clearly related to the project/service.
    """

    MODERATE = "moderate"
    """
    Clean up related processes and shared resources.
    """

    AGGRESSIVE = "aggressive"
    """
    Clean up all potentially related processes and resources.
    """


@dataclass
class ProcessMetadata:
    """
    Metadata for process identification and management.
    """

    project: str | None = None
    """
    Project name associated with the process.
    """

    service: str | None = None
    """
    Service name associated with the process.
    """

    scope: str | None = None
    """
    Scope of the process (global, tenant, local).
    """

    resource_type: str | None = None
    """
    Type of resource (tunnel, dns, api, web, etc.).
    """

    tags: set[str] = field(default_factory=set)
    """
    Additional tags for process identification.
    """

    created_at: float = field(default_factory=time.time)
    """
    Timestamp when the process was created.
    """

    last_seen: float = field(default_factory=time.time)
    """
    Timestamp when the process was last seen.
    """

    pid: int | None = None
    """
    Process ID.
    """

    parent_pid: int | None = None
    """
    Parent process ID.
    """

    command_line: list[str] = field(default_factory=list)
    """
    Command line arguments.
    """

    environment: dict[str, str] = field(default_factory=dict)
    """
    Environment variables.
    """


@dataclass
class ProcessGovernanceConfig:
    """
    Configuration for process governance.
    """

    cleanup_policy: CleanupPolicy = CleanupPolicy.MODERATE
    """
    Cleanup policy to use.
    """

    grace_period: float = 5.0
    """
    Grace period for process termination in seconds.
    """

    force_kill: bool = True
    """
    Whether to force kill processes that don't terminate gracefully.
    """

    max_process_age: float = 3600.0
    """
    Maximum age for processes before they're considered stale (in seconds).
    """

    enable_metadata_tracking: bool = True
    """
    Whether to enable metadata-based process tracking.
    """

    project_isolation: bool = True
    """
    Whether to enforce project isolation in cleanup.
    """

    shared_resource_cleanup: bool = False
    """
    Whether to clean up shared resources.
    """


class ProcessGovernanceManager:
    """
    Enhanced process governance with metadata-based management.

    Features:
    - Metadata-based process identification
    - Project and service-specific cleanup
    - Configurable cleanup policies
    - Process lifecycle tracking
    - Integration with existing cleanup systems
    """

    def __init__(self, config: ProcessGovernanceConfig | None = None):
        """Initialize process governance manager.

        Args:
            config: Process governance configuration
        """
        self.config = config or ProcessGovernanceConfig()
        self.current_pid = os.getpid()
        self._process_metadata: dict[int, ProcessMetadata] = {}
        self._project_processes: dict[str, set[int]] = {}
        self._service_processes: dict[str, set[int]] = {}
        self._cleanup_stats = {
            "inspected": 0,
            "terminated": 0,
            "force_killed": 0,
            "skipped": 0,
            "errors": 0,
            "by_project": {},
            "by_service": {},
        }

        logger.info(
            f"ProcessGovernanceManager initialized (policy: {self.config.cleanup_policy.value})",
        )

    def register_process(
        self,
        pid: int,
        metadata: ProcessMetadata,
    ) -> None:
        """
        Register a process with metadata.

        Args:
            pid: Process ID
            metadata: Process metadata
        """
        metadata.pid = pid
        self._process_metadata[pid] = metadata

        # Track by project
        if metadata.project:
            if metadata.project not in self._project_processes:
                self._project_processes[metadata.project] = set()
            self._project_processes[metadata.project].add(pid)

        # Track by service
        if metadata.service:
            if metadata.service not in self._service_processes:
                self._service_processes[metadata.service] = set()
            self._service_processes[metadata.service].add(pid)

        logger.debug(
            f"Registered process {pid} with metadata: project={metadata.project}, service={metadata.service}",
        )

    def unregister_process(
        self,
        pid: int,
    ) -> None:
        """
        Unregister a process.

        Args:
            pid: Process ID
        """
        if pid in self._process_metadata:
            metadata = self._process_metadata[pid]

            # Remove from project tracking
            if metadata.project and metadata.project in self._project_processes:
                self._project_processes[metadata.project].discard(pid)
                if not self._project_processes[metadata.project]:
                    del self._project_processes[metadata.project]

            # Remove from service tracking
            if metadata.service and metadata.service in self._service_processes:
                self._service_processes[metadata.service].discard(pid)
                if not self._service_processes[metadata.service]:
                    del self._service_processes[metadata.service]

            del self._process_metadata[pid]
            logger.debug(f"Unregistered process {pid}")

    def cleanup_project_processes(
        self,
        project_name: str,
        force: bool = False,
    ) -> dict[str, int]:
        """
        Clean up all processes for a specific project.

        Args:
            project_name: Name of the project
            force: Whether to force cleanup even if conservative policy

        Returns:
            Cleanup statistics
        """
        logger.info(f"Cleaning up processes for project '{project_name}'")

        # Reset stats
        self._cleanup_stats = {
            "inspected": 0,
            "terminated": 0,
            "force_killed": 0,
            "skipped": 0,
            "errors": 0,
            "by_project": {project_name: 0},
            "by_service": {},
        }

        if not PSUTIL_AVAILABLE:
            logger.warning("psutil not available, skipping process cleanup")
            return self._cleanup_stats

        # Get processes for this project
        project_pids = self._project_processes.get(project_name, set()).copy()

        if not project_pids:
            logger.info(f"No processes found for project '{project_name}'")
            return self._cleanup_stats

        # Clean up processes
        processes_to_terminate = []

        for pid in project_pids:
            try:
                if pid == self.current_pid:
                    self._cleanup_stats["skipped"] += 1
                    continue

                proc = psutil.Process(pid)
                self._cleanup_stats["inspected"] += 1

                # Check if process is still running
                if not proc.is_running():
                    self.unregister_process(pid)
                    self._cleanup_stats["skipped"] += 1
                    continue

                processes_to_terminate.append(proc)

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                self.unregister_process(pid)
                self._cleanup_stats["skipped"] += 1
                continue
            except Exception as e:
                logger.exception(f"Error inspecting process {pid}: {e}")
                self._cleanup_stats["errors"] += 1
                continue

        # Terminate processes
        if processes_to_terminate:
            self._terminate_processes(processes_to_terminate, f"project '{project_name}'")
            self._cleanup_stats["by_project"][project_name] = len(processes_to_terminate)

        logger.info(f"Project cleanup completed: {self._cleanup_stats}")
        return self._cleanup_stats

    def cleanup_service_processes(
        self,
        service_name: str,
        force: bool = False,
    ) -> dict[str, int]:
        """
        Clean up all processes for a specific service.

        Args:
            service_name: Name of the service
            force: Whether to force cleanup even if conservative policy

        Returns:
            Cleanup statistics
        """
        logger.info(f"Cleaning up processes for service '{service_name}'")

        # Reset stats
        self._cleanup_stats = {
            "inspected": 0,
            "terminated": 0,
            "force_killed": 0,
            "skipped": 0,
            "errors": 0,
            "by_project": {},
            "by_service": {service_name: 0},
        }

        if not PSUTIL_AVAILABLE:
            logger.warning("psutil not available, skipping process cleanup")
            return self._cleanup_stats

        # Get processes for this service
        service_pids = self._service_processes.get(service_name, set()).copy()

        if not service_pids:
            logger.info(f"No processes found for service '{service_name}'")
            return self._cleanup_stats

        # Clean up processes
        processes_to_terminate = []

        for pid in service_pids:
            try:
                if pid == self.current_pid:
                    self._cleanup_stats["skipped"] += 1
                    continue

                proc = psutil.Process(pid)
                self._cleanup_stats["inspected"] += 1

                # Check if process is still running
                if not proc.is_running():
                    self.unregister_process(pid)
                    self._cleanup_stats["skipped"] += 1
                    continue

                processes_to_terminate.append(proc)

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                self.unregister_process(pid)
                self._cleanup_stats["skipped"] += 1
                continue
            except Exception as e:
                logger.exception(f"Error inspecting process {pid}: {e}")
                self._cleanup_stats["errors"] += 1
                continue

        # Terminate processes
        if processes_to_terminate:
            self._terminate_processes(processes_to_terminate, f"service '{service_name}'")
            self._cleanup_stats["by_service"][service_name] = len(processes_to_terminate)

        logger.info(f"Service cleanup completed: {self._cleanup_stats}")
        return self._cleanup_stats

    def cleanup_stale_processes(
        self,
        max_age: float | None = None,
    ) -> dict[str, int]:
        """
        Clean up stale processes based on age.

        Args:
            max_age: Maximum age for processes (uses config default if None)

        Returns:
            Cleanup statistics
        """
        max_age = max_age or self.config.max_process_age
        logger.info(f"Cleaning up stale processes (max_age: {max_age}s)")

        # Reset stats
        self._cleanup_stats = {
            "inspected": 0,
            "terminated": 0,
            "force_killed": 0,
            "skipped": 0,
            "errors": 0,
            "by_project": {},
            "by_service": {},
        }

        if not PSUTIL_AVAILABLE:
            logger.warning("psutil not available, skipping process cleanup")
            return self._cleanup_stats

        # Find stale processes
        stale_pids = []
        current_time = time.time()

        for pid, metadata in self._process_metadata.items():
            if pid == self.current_pid:
                continue

            # Check if process is stale
            if current_time - metadata.last_seen > max_age:
                stale_pids.append(pid)

        if not stale_pids:
            logger.info("No stale processes found")
            return self._cleanup_stats

        # Clean up stale processes
        processes_to_terminate = []

        for pid in stale_pids:
            try:
                proc = psutil.Process(pid)
                self._cleanup_stats["inspected"] += 1

                # Check if process is still running
                if not proc.is_running():
                    self.unregister_process(pid)
                    self._cleanup_stats["skipped"] += 1
                    continue

                processes_to_terminate.append(proc)

                # Track by project and service
                metadata = self._process_metadata.get(pid)
                if metadata:
                    if metadata.project:
                        if metadata.project not in self._cleanup_stats["by_project"]:
                            self._cleanup_stats["by_project"][metadata.project] = 0
                        self._cleanup_stats["by_project"][metadata.project] += 1

                    if metadata.service:
                        if metadata.service not in self._cleanup_stats["by_service"]:
                            self._cleanup_stats["by_service"][metadata.service] = 0
                        self._cleanup_stats["by_service"][metadata.service] += 1

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                self.unregister_process(pid)
                self._cleanup_stats["skipped"] += 1
                continue
            except Exception as e:
                logger.exception(f"Error inspecting stale process {pid}: {e}")
                self._cleanup_stats["errors"] += 1
                continue

        # Terminate processes
        if processes_to_terminate:
            self._terminate_processes(processes_to_terminate, "stale processes")

        logger.info(f"Stale process cleanup completed: {self._cleanup_stats}")
        return self._cleanup_stats

    def get_project_processes(
        self,
        project_name: str,
    ) -> list[ProcessMetadata]:
        """
        Get all processes for a project.

        Args:
            project_name: Name of the project

        Returns:
            List of process metadata
        """
        project_pids = self._project_processes.get(project_name, set())
        return [
            self._process_metadata[pid] for pid in project_pids if pid in self._process_metadata
        ]

    def get_service_processes(
        self,
        service_name: str,
    ) -> list[ProcessMetadata]:
        """
        Get all processes for a service.

        Args:
            service_name: Name of the service

        Returns:
            List of process metadata
        """
        service_pids = self._service_processes.get(service_name, set())
        return [
            self._process_metadata[pid] for pid in service_pids if pid in self._process_metadata
        ]

    def get_process_metadata(
        self,
        pid: int,
    ) -> ProcessMetadata | None:
        """
        Get metadata for a specific process.

        Args:
            pid: Process ID

        Returns:
            Process metadata or None
        """
        return self._process_metadata.get(pid)

    def list_all_processes(self) -> list[ProcessMetadata]:
        """
        List all registered processes.

        Returns:
            List of all process metadata
        """
        return list(self._process_metadata.values())

    def get_cleanup_stats(self) -> dict[str, Any]:
        """
        Get current cleanup statistics.

        Returns:
            Cleanup statistics
        """
        return self._cleanup_stats.copy()

    def reset_stats(self) -> None:
        """
        Reset cleanup statistics.
        """
        self._cleanup_stats = {
            "inspected": 0,
            "terminated": 0,
            "force_killed": 0,
            "skipped": 0,
            "errors": 0,
            "by_project": {},
            "by_service": {},
        }

    # ========== Private helper methods ==========

    def _terminate_processes(
        self,
        processes: list[psutil.Process],
        process_type: str,
    ) -> None:
        """
        Terminate a list of processes.

        Args:
            processes: List of processes to terminate
            process_type: Human-readable description of the process type
        """
        logger.info(f"Terminating {len(processes)} {process_type}...")

        # Send SIGTERM to all processes
        for proc in processes:
            try:
                proc.terminate()
                logger.debug(f"Sent SIGTERM to {process_type} {proc.pid}")
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                logger.debug(f"Could not terminate {process_type} {proc.pid}: {e}")
                continue
            except Exception as e:
                logger.warning(f"Error terminating {process_type} {proc.pid}: {e}")
                self._cleanup_stats["errors"] += 1
                continue

        # Wait for graceful termination
        if processes:
            try:
                gone, alive = psutil.wait_procs(processes, timeout=self.config.grace_period)
                self._cleanup_stats["terminated"] += len(gone)

                # Force kill remaining processes if enabled
                if alive and self.config.force_kill:
                    logger.warning(f"Force killing {len(alive)} stubborn {process_type}...")
                    for proc in alive:
                        try:
                            proc.kill()
                            logger.debug(f"Force killed {process_type} {proc.pid}")
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                        except Exception as e:
                            logger.warning(f"Error force killing {process_type} {proc.pid}: {e}")
                            self._cleanup_stats["errors"] += 1
                            continue

                    # Wait for force killed processes
                    gone_after_kill, still_alive = psutil.wait_procs(alive, timeout=2.0)
                    self._cleanup_stats["force_killed"] += len(gone_after_kill)

                    # Log any processes that still won't die
                    for proc in still_alive:
                        logger.error(f"{process_type} {proc.pid} survived all termination attempts")
                        self._cleanup_stats["errors"] += 1

            except Exception as e:
                logger.exception(f"Error during process termination: {e}")
                self._cleanup_stats["errors"] += 1
