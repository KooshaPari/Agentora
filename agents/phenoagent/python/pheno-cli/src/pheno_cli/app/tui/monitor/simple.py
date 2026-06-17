"""
Simple console-based monitor fallback.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pheno.domain.models.project import ProjectRegistry

    from .engine import MonitorEngine


class SimpleTUIMonitor:
    """
    Simple fallback TUI monitor using basic console output.
    """

    def __init__(self, project_registry: ProjectRegistry, monitor_engine: MonitorEngine):
        self.project_registry = project_registry
        self.monitor_engine = monitor_engine

    async def run(self) -> None:
        print("=== Pheno Control Center - Simple Monitor ===")
        print("Enhanced TUI not available (missing rich/textual)")
        print("Commands: 'status', 'quit', or any project command")
        print("=" * 50)

        while True:
            try:
                command = input("> ").strip()
                if command.lower() in ["quit", "exit", "q"]:
                    break
                if command.lower() == "status":
                    self._print_status()
                elif command:
                    print(f"Executed: {command}")
            except (EOFError, KeyboardInterrupt):
                break

        print("\nShutting down...")

    def _print_status(self) -> None:
        global_status = self.monitor_engine.get_global_status()
        print("\nGlobal Status:")
        print(
            f"  Projects: {global_status['summary']['healthy_projects']}/{global_status['summary']['total_projects']} healthy",
        )
        print(
            f"  Processes: {global_status['summary']['running_processes']}/{global_status['summary']['total_processes']} running",
        )

        for project_name, project_status in global_status["projects"].items():
            print(f"\n{project_name.upper()}:")
            print(f"  Overall: {project_status['overall_state']}")
            print(
                f"  Processes: {project_status['processes']['running']}/{project_status['processes']['total']}",
            )
            for process_name, state in project_status["processes"]["details"].items():
                print(f"    {process_name}: {state}")
        print()


__all__ = ["SimpleTUIMonitor"]
