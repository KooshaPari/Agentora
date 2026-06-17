"""
Factory for creating monitors.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..base.monitor_base import BaseMonitor
from ..components.health_monitor import HealthMonitor
from ..components.process_manager import ProcessManager


class DefaultMonitor(BaseMonitor):
    """
    Default monitor implementation.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pm = ProcessManager()
        self.hm = HealthMonitor()
        self._health_task = None
        self._process_health_map = {}  # Map process names to health check names

    def start(self):
        """
        Start all processes.
        """
        print(f"🚀 Starting {self.name} monitor...")

        # Start processes
        for proc_config in self.processes:
            proc_name = proc_config.get("name")
            self.pm.start_process(**proc_config)

            # Auto-create health check for processes with ports
            port = proc_config.get("port")
            if port and not any(c.get("port") == port for c in self.health_checks):
                # Add port health check
                self.hm.add_port_check(port, interval=5)
                self._process_health_map[proc_name] = f"Port:{port}"

        # Setup explicit health checks
        for check_config in self.health_checks:
            if "url" in check_config:
                self.hm.add_http_check(
                    check_config["url"],
                    timeout=check_config.get("timeout", 5),
                    interval=check_config.get("interval", 10),
                )
                # Try to map to process
                url = check_config["url"]
                for proc_config in self.processes:
                    port = proc_config.get("port")
                    if port and str(port) in url:
                        self._process_health_map[proc_config["name"]] = f"HTTP:{url}"
            elif "port" in check_config:
                self.hm.add_port_check(
                    check_config["port"], interval=check_config.get("interval", 5),
                )

        # Start health monitoring in background
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                self._health_task = loop.create_task(self.hm.start_monitoring())
            else:
                # Create new loop for health monitoring
                import threading

                def run_health_monitoring():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.hm.start_monitoring())

                health_thread = threading.Thread(target=run_health_monitoring, daemon=True)
                health_thread.start()
        except Exception as e:
            print(f"⚠️  Could not start health monitoring: {e}")

        self.running = True
        print(f"✅ {self.name} monitor started")

    def stop(self):
        """
        Stop all processes.
        """
        print(f"🛑 Stopping {self.name} monitor...")
        self.pm.stop_all()
        self.hm.stop_monitoring()
        self.running = False
        print(f"✅ {self.name} monitor stopped")

    def get_status(self) -> dict[str, Any]:
        """
        Get monitor status.
        """
        # Get health status
        health_status = self.hm.get_status()
        health_checks = health_status.get("checks", {})

        # Map health to processes
        process_health = {}
        for proc_name, health_check_name in self._process_health_map.items():
            is_healthy = health_checks.get(health_check_name, False)
            process_health[proc_name] = {"healthy": is_healthy}

        return {
            "name": self.name,
            "running": self.running,
            "processes": self.pm.get_all_status(),
            "health": process_health,
        }


class MonitorFactory:
    """
    Factory for creating monitors.
    """

    @staticmethod
    def create(
        name: str,
        processes: list[dict[str, Any]] | None = None,
        health_checks: list[dict[str, Any]] | None = None,
        infrastructure=None,
    ) -> BaseMonitor:
        """Create a monitor from configuration.

        Args:
            name: Monitor name
            processes: Process configurations
            health_checks: Health check configurations
            infrastructure: Optional KInfra instance for port/tunnel management

        Returns:
            Monitor instance
        """
        # Process ServiceInfra integration if available
        if infrastructure:
            processes = MonitorFactory._integrate_service_infra(processes, infrastructure)

        return DefaultMonitor(
            name=name, processes=processes or [], health_checks=health_checks or [],
        )

    @staticmethod
    def from_config(config_path: str) -> BaseMonitor:
        """Create monitor from YAML config file.

        Args:
            config_path: Path to config file

        Returns:
            Monitor instance
        """
        import yaml

        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_file) as f:
            config = yaml.safe_load(f)

        return MonitorFactory.create(
            name=config.get("name", "monitor"),
            processes=config.get("processes", []),
            health_checks=config.get("health_checks", []),
        )

    @staticmethod
    def _integrate_service_infra(
        processes: list[dict[str, Any]], infrastructure,
    ) -> list[dict[str, Any]]:
        """Integrate with ServiceInfra for port allocation and tunnels.

        Args:
            processes: Process configurations
            infrastructure: ServiceInfraManager-like instance

        Returns:
            Updated process configurations
        """
        updated = []

        for proc in processes:
            proc = proc.copy()

            # Auto-allocate port if requested
            if proc.get("port") == "auto":
                port = infrastructure.allocate_port(proc["name"])
                proc["port"] = port

            # Create tunnel if requested
            if proc.get("tunnel"):
                tunnel_url = infrastructure.create_tunnel(proc["name"], proc.get("port"))
                proc["tunnel_url"] = tunnel_url

            updated.append(proc)

        return updated
