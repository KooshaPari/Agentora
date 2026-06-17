"""Unified Monitor Engine for Pheno Control Center.

Core service manager abstraction that feeds both GUI and headless monitors with project-
specific process/resource registry and streaming log ingestion.
"""

import asyncio
import contextlib
import logging
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from pheno.domain.models.process import ProcessInfo
from pheno.domain.models.resource import ResourceInfo

logger = logging.getLogger(__name__)


class ServiceState(Enum):
    """
    Service lifecycle states.
    """

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    UNKNOWN = "unknown"


class ResourceState(Enum):
    """
    Resource availability states.
    """

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class LogEntry:
    """
    Log entry from a monitored process.
    """

    timestamp: datetime
    """
    Log timestamp.
    """

    project: str
    """
    Source project.
    """

    process: str
    """
    Source process/service name.
    """

    level: str
    """
    Log level (stdout, stderr, info, error, etc.)
    """

    message: str
    """
    Log message content.
    """

    metadata: dict[str, Any] = field(default_factory=dict)
    """
    Additional log metadata.
    """


class MonitorEngine:
    """
    Core monitoring engine that aggregates process and resource state from multiple
    projects and provides unified views for different UIs.
    """

    def __init__(self, max_log_entries: int = 10000, log_retention_hours: int = 24):
        """
        Initialize the monitor engine.
        """
        self.max_log_entries = max_log_entries
        self.log_retention_hours = log_retention_hours

        # Process and resource registries by project
        self.processes: dict[str, dict[str, ProcessInfo]] = defaultdict(dict)
        self.resources: dict[str, dict[str, ResourceInfo]] = defaultdict(dict)

        # Log storage
        self.logs: deque[LogEntry] = deque(maxlen=max_log_entries)
        self.logs_by_project: dict[str, deque[LogEntry]] = defaultdict(
            lambda: deque(maxlen=max_log_entries // 10),
        )

        # Event subscribers
        self.event_callbacks: list[Callable[[str, dict[str, Any]], None]] = []

        # Monitoring tasks
        self._monitor_task = None
        self._cleanup_task = None
        self._running = False

        logger.info("Unified Monitor Engine initialized")

    def subscribe_to_events(self, callback: Callable[[str, dict[str, Any]], None]) -> None:
        """Subscribe to monitoring events.

        Args:
            callback: Function called with (event_type, event_data)
                     Event types: 'process_state_changed', 'resource_state_changed',
                                 'log_entry', 'process_added', 'process_removed'
        """
        self.event_callbacks.append(callback)

    def _emit_event(self, event_type: str, event_data: dict[str, Any]) -> None:
        """
        Emit an event to all subscribers.
        """
        for callback in self.event_callbacks:
            try:
                callback(event_type, event_data)
            except Exception as e:
                logger.warning(f"Event callback error: {e}")

    def register_process(self, process_info: ProcessInfo) -> None:
        """
        Register a process for monitoring.
        """
        project_processes = self.processes[process_info.project]

        # Check if this is a state change
        existing = project_processes.get(process_info.name)
        is_new = existing is None
        state_changed = existing and existing.state != process_info.state

        # Update registry
        project_processes[process_info.name] = process_info

        # Emit events
        if is_new:
            self._emit_event(
                "process_added",
                {
                    "project": process_info.project,
                    "process": process_info.name,
                    "info": process_info,
                },
            )
            logger.info(f"Registered process {process_info.project}.{process_info.name}")

        if state_changed:
            self._emit_event(
                "process_state_changed",
                {
                    "project": process_info.project,
                    "process": process_info.name,
                    "old_state": existing.state.value if existing else None,
                    "new_state": process_info.state.value,
                    "info": process_info,
                },
            )
            logger.debug(
                f"Process state changed: {process_info.project}.{process_info.name} -> {process_info.state.value}",
            )

    def unregister_process(self, project: str, process_name: str) -> bool:
        """
        Unregister a process from monitoring.
        """
        project_processes = self.processes.get(project, {})
        if process_name in project_processes:
            process_info = project_processes.pop(process_name)

            self._emit_event(
                "process_removed",
                {"project": project, "process": process_name, "info": process_info},
            )
            logger.info(f"Unregistered process {project}.{process_name}")
            return True
        return False

    def register_resource(self, resource_info: ResourceInfo) -> None:
        """
        Register a resource for monitoring.
        """
        project_resources = self.resources[resource_info.project]

        # Check if this is a state change
        existing = project_resources.get(resource_info.name)
        is_new = existing is None
        state_changed = existing and existing.state != resource_info.state

        # Update registry
        project_resources[resource_info.name] = resource_info

        # Emit events
        if is_new:
            self._emit_event(
                "resource_added",
                {
                    "project": resource_info.project,
                    "resource": resource_info.name,
                    "info": resource_info,
                },
            )
            logger.info(f"Registered resource {resource_info.project}.{resource_info.name}")

        if state_changed:
            self._emit_event(
                "resource_state_changed",
                {
                    "project": resource_info.project,
                    "resource": resource_info.name,
                    "old_state": existing.state.value if existing else None,
                    "new_state": resource_info.state.value,
                    "info": resource_info,
                },
            )
            logger.debug(
                f"Resource state changed: {resource_info.project}.{resource_info.name} -> {resource_info.state.value}",
            )

    def get_process(self, project: str, process_name: str) -> ProcessInfo | None:
        """
        Get process information.
        """
        return self.processes.get(project, {}).get(process_name)

    def get_resource(self, project: str, resource_name: str) -> ResourceInfo | None:
        """
        Get resource information.
        """
        return self.resources.get(project, {}).get(resource_name)

    def get_project_processes(self, project: str) -> dict[str, ProcessInfo]:
        """
        Get all processes for a project.
        """
        return self.processes.get(project, {}).copy()

    def get_project_resources(self, project: str) -> dict[str, ResourceInfo]:
        """
        Get all resources for a project.
        """
        return self.resources.get(project, {}).copy()

    def get_all_projects(self) -> set[str]:
        """
        Get all monitored project names.
        """
        projects = set(self.processes.keys())
        projects.update(self.resources.keys())
        return projects

    def log_entry(self, entry: LogEntry) -> None:
        """
        Add a log entry to the monitoring system.
        """
        # Add to global logs
        self.logs.append(entry)

        # Add to project-specific logs
        self.logs_by_project[entry.project].append(entry)

        # Emit event
        self._emit_event(
            "log_entry", {"project": entry.project, "process": entry.process, "entry": entry},
        )

    def get_logs(
        self,
        project: str | None = None,
        process: str | None = None,
        level: str | None = None,
        limit: int | None = None,
    ) -> list[LogEntry]:
        """Get log entries with optional filtering.

        Args:
            project: Filter by project name
            process: Filter by process name
            level: Filter by log level
            limit: Maximum number of entries to return

        Returns:
            List of matching log entries
        """
        # Choose source logs
        logs = self.logs_by_project.get(project, deque()) if project else self.logs

        # Apply filters
        filtered = logs
        if process:
            filtered = [log for log in filtered if log.process == process]
        if level:
            filtered = [log for log in filtered if log.level == level]

        # Convert to list and apply limit
        result = list(filtered)
        if limit:
            result = result[-limit:]

        return result

    def get_project_status(self, project: str) -> dict[str, Any]:
        """
        Get comprehensive status for a project.
        """
        processes = self.get_project_processes(project)
        resources = self.get_project_resources(project)

        # Calculate overall health
        running_processes = sum(1 for p in processes.values() if p.state == ServiceState.RUNNING)
        total_processes = len(processes)

        available_resources = sum(
            1 for r in resources.values() if r.state == ResourceState.AVAILABLE
        )
        required_resources = sum(1 for r in resources.values() if r.required)

        # Determine overall state
        if total_processes == 0:
            overall_state = "no_processes"
        elif running_processes == total_processes and available_resources >= required_resources:
            overall_state = "healthy"
        elif running_processes > 0:
            overall_state = "degraded"
        else:
            overall_state = "down"

        return {
            "project": project,
            "overall_state": overall_state,
            "processes": {
                "running": running_processes,
                "total": total_processes,
                "details": {name: p.state.value for name, p in processes.items()},
            },
            "resources": {
                "available": available_resources,
                "required": required_resources,
                "total": len(resources),
                "details": {name: r.state.value for name, r in resources.items()},
            },
            "last_updated": datetime.now(),
        }

    def get_global_status(self) -> dict[str, Any]:
        """
        Get global status across all projects.
        """
        projects = self.get_all_projects()

        project_statuses = {}
        total_processes = 0
        running_processes = 0
        healthy_projects = 0

        for project in projects:
            status = self.get_project_status(project)
            project_statuses[project] = status

            total_processes += status["processes"]["total"]
            running_processes += status["processes"]["running"]

            if status["overall_state"] == "healthy":
                healthy_projects += 1

        return {
            "projects": project_statuses,
            "summary": {
                "total_projects": len(projects),
                "healthy_projects": healthy_projects,
                "total_processes": total_processes,
                "running_processes": running_processes,
            },
            "last_updated": datetime.now(),
        }

    async def start_monitoring(self, check_interval: float = 5.0) -> None:
        """
        Start background monitoring tasks.
        """
        if self._running:
            logger.warning("Monitor engine already running")
            return

        self._running = True

        # Start monitoring task
        self._monitor_task = asyncio.create_task(self._monitor_loop(check_interval))

        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        logger.info("Monitor engine background tasks started")

    async def stop_monitoring(self) -> None:
        """
        Stop background monitoring tasks.
        """
        if not self._running:
            return

        self._running = False

        # Cancel tasks
        if self._monitor_task:
            self._monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._monitor_task

        if self._cleanup_task:
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task

        logger.info("Monitor engine stopped")

    async def _monitor_loop(self, check_interval: float) -> None:
        """
        Background monitoring loop for health checks.
        """
        while self._running:
            try:
                # Health check all processes and resources
                await self._check_all_health()
                await asyncio.sleep(check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Monitor loop error: {e}")
                await asyncio.sleep(check_interval)

    async def _cleanup_loop(self) -> None:
        """
        Background cleanup loop for old logs and stale entries.
        """
        while self._running:
            try:
                # Clean up old logs
                self._cleanup_old_logs()

                # Clean up stale processes (could be enhanced)
                # self._cleanup_stale_processes()

                await asyncio.sleep(3600)  # Run cleanup every hour

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Cleanup loop error: {e}")
                await asyncio.sleep(3600)

    def _cleanup_old_logs(self) -> None:
        """
        Remove log entries older than retention period.
        """
        cutoff = datetime.now().timestamp() - (self.log_retention_hours * 3600)

        # Clean global logs
        while self.logs and self.logs[0].timestamp.timestamp() < cutoff:
            self.logs.popleft()

        # Clean project logs
        for project_logs in self.logs_by_project.values():
            while project_logs and project_logs[0].timestamp.timestamp() < cutoff:
                project_logs.popleft()

    async def _check_all_health(self) -> None:
        """
        Perform health checks on all registered processes and resources.
        """
        # This is a simplified version - could be enhanced with actual health checks

        for processes in self.processes.values():
            for process_info in processes.values():
                # Update last_seen
                process_info.last_seen = datetime.now()

                # Could add actual PID checks, port checks, etc.

        for resources in self.resources.values():
            for resource_info in resources.values():
                # Update last_checked
                resource_info.last_checked = datetime.now()

                # Could add actual connectivity checks


# Alias for backward compatibility
UnifiedMonitorEngine = MonitorEngine
