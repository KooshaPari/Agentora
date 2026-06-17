"""
Monitoring engine abstraction.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from typing import TYPE_CHECKING, Any

from pheno.domain.models.project import ProjectRegistry

if TYPE_CHECKING:
    from collections.abc import Callable

    from pheno.domain.models.log import LogEntry
    from pheno.domain.models.process import ProcessInfo
    from pheno.domain.models.resource import ResourceInfo

logger = logging.getLogger(__name__)


class MonitorEngine:
    """
    Monitoring engine for multiple projects.
    """

    def __init__(self):
        self.project_registry = ProjectRegistry()
        self.log_entries: deque[LogEntry] = deque(maxlen=1000)
        self.event_callbacks: list[Callable[[str, dict[str, Any]], None]] = []
        self.start_time = time.time()

    def subscribe_to_events(self, callback: Callable[[str, dict[str, Any]], None]) -> None:
        """
        Subscribe to monitor events.
        """
        self.event_callbacks.append(callback)

    def _emit_event(self, event_type: str, event_data: dict[str, Any]) -> None:
        """
        Emit an event to all subscribers.
        """
        for callback in self.event_callbacks:
            try:
                callback(event_type, event_data)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.exception("Event callback error: %s", exc)

    def log_entry(self, entry: LogEntry) -> None:
        """
        Add a log entry.
        """
        self.log_entries.append(entry)
        self._emit_event("log_entry", {"entry": entry})

    def add_process(self, project: str, process_info: ProcessInfo) -> None:
        """
        Add a process to monitoring.
        """
        self.project_registry.add_process(project, process_info)
        self._emit_event("process_added", {"project": project, "process": process_info})

    def remove_process(self, project: str, process_name: str) -> None:
        """
        Remove a process from monitoring.
        """
        self.project_registry.remove_process(project, process_name)
        self._emit_event("process_removed", {"project": project, "process_name": process_name})

    def update_process_state(self, project: str, process_name: str, state: str) -> None:
        """
        Update process state.
        """
        project_data = self.project_registry.get_project(project)
        if project_data and process_name in project_data["processes"]:
            project_data["processes"][process_name].state = state
            self._emit_event(
                "process_state_changed",
                {"project": project, "process_name": process_name, "state": state},
            )

    def add_resource(self, project: str, resource_info: ResourceInfo) -> None:
        """
        Add a resource to monitoring.
        """
        self.project_registry.add_resource(project, resource_info)
        self._emit_event("resource_added", {"project": project, "resource": resource_info})

    def update_resource_state(self, project: str, resource_name: str, state: str) -> None:
        """
        Update resource state.
        """
        project_data = self.project_registry.get_project(project)
        if project_data and resource_name in project_data["resources"]:
            project_data["resources"][resource_name].state = state
            self._emit_event(
                "resource_state_changed",
                {"project": project, "resource_name": resource_name, "state": state},
            )

    def get_global_status(self) -> dict[str, Any]:
        """
        Get global status across all projects.
        """
        projects = self.project_registry.list_projects()
        total_projects = len(projects)
        healthy_projects = 0
        total_processes = 0
        running_processes = 0
        project_statuses: dict[str, Any] = {}

        for project_name in projects:
            project_data = self.project_registry.get_project(project_name)
            if not project_data:
                continue

            processes = project_data["processes"]
            resources = project_data["resources"]

            project_total_processes = len(processes)
            project_running_processes = sum(
                1 for process in processes.values() if process.state == "running"
            )

            total_processes += project_total_processes
            running_processes += project_running_processes

            if project_total_processes == 0:
                overall_state = "no_processes"
            elif project_running_processes == project_total_processes:
                overall_state = "healthy"
                healthy_projects += 1
            elif project_running_processes > 0:
                overall_state = "degraded"
            else:
                overall_state = "down"

            total_resources = len(resources)
            available_resources = sum(
                1 for resource in resources.values() if resource.state == "available"
            )

            project_statuses[project_name] = {
                "overall_state": overall_state,
                "processes": {
                    "total": project_total_processes,
                    "running": project_running_processes,
                    "details": {name: proc.state for name, proc in processes.items()},
                },
                "resources": {
                    "total": total_resources,
                    "available": available_resources,
                    "details": {name: res.state for name, res in resources.items()},
                },
            }

        return {
            "summary": {
                "total_projects": total_projects,
                "healthy_projects": healthy_projects,
                "total_processes": total_processes,
                "running_processes": running_processes,
            },
            "projects": project_statuses,
        }

    def get_project_status(self, project_name: str) -> dict[str, Any]:
        """
        Get status for a specific project.
        """
        project_data = self.project_registry.get_project(project_name)
        if not project_data:
            return {
                "overall_state": "not_found",
                "processes": {"total": 0, "running": 0, "details": {}},
                "resources": {"total": 0, "available": 0, "details": {}},
            }

        processes = project_data["processes"]
        resources = project_data["resources"]

        project_total_processes = len(processes)
        project_running_processes = sum(
            1 for process in processes.values() if process.state == "running"
        )

        total_resources = len(resources)
        available_resources = sum(
            1 for resource in resources.values() if resource.state == "available"
        )

        if project_total_processes == 0:
            overall_state = "no_processes"
        elif project_running_processes == project_total_processes:
            overall_state = "healthy"
        elif project_running_processes > 0:
            overall_state = "degraded"
        else:
            overall_state = "down"

        return {
            "overall_state": overall_state,
            "processes": {
                "total": project_total_processes,
                "running": project_running_processes,
                "details": {name: proc.state for name, proc in processes.items()},
            },
            "resources": {
                "total": total_resources,
                "available": available_resources,
                "details": {name: res.state for name, res in resources.items()},
            },
        }

    def get_project_processes(self, project_name: str) -> dict[str, ProcessInfo]:
        """
        Get processes for a project.
        """
        project_data = self.project_registry.get_project(project_name)
        if not project_data:
            return {}
        return project_data["processes"]

    def get_project_resources(self, project_name: str) -> dict[str, ResourceInfo]:
        """
        Get resources for a project.
        """
        project_data = self.project_registry.get_project(project_name)
        if not project_data:
            return {}
        return project_data["resources"]

    def get_process(self, project_name: str, process_name: str) -> ProcessInfo | None:
        """
        Get a specific process.
        """
        processes = self.get_project_processes(project_name)
        return processes.get(process_name)

    def get_logs(self, limit: int = 100) -> list[LogEntry]:
        """
        Get recent log entries.
        """
        return list(self.log_entries)[-limit:]


__all__ = ["MonitorEngine"]
