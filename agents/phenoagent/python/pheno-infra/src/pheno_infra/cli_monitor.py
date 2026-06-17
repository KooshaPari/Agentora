"""CLI Monitoring System for KINFRA.

Provides live health checks, log dumps, and service monitoring capabilities for KINFRA-
managed services.
"""

import asyncio
import logging
import signal
import time
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class HealthCheckResult:
    """
    Result of a health check operation.
    """

    def __init__(
        self,
        service_name: str,
        is_healthy: bool,
        response_time: float,
        status_code: int | None = None,
        error: str | None = None,
    ):
        self.service_name = service_name
        self.is_healthy = is_healthy
        self.response_time = response_time
        self.status_code = status_code
        self.error = error
        self.timestamp = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.
        """
        return {
            "service_name": self.service_name,
            "is_healthy": self.is_healthy,
            "response_time": self.response_time,
            "status_code": self.status_code,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }


class ServiceMonitor:
    """
    Monitors a KINFRA service with health checks and log monitoring.
    """

    def __init__(self, service_name: str, port: int, health_endpoint: str = "/health"):
        self.service_name = service_name
        self.port = port
        self.health_endpoint = health_endpoint
        self.base_url = f"http://127.0.0.1:{port}"
        self.health_url = f"{self.base_url}{health_endpoint}"
        self.mcp_url = f"{self.base_url}/api/mcp"

        self.is_monitoring = False
        self.health_history: list[HealthCheckResult] = []
        self.log_buffer: list[str] = []
        self.max_log_entries = 1000

    async def check_health(self) -> HealthCheckResult:
        """Perform a health check on the service.

        Returns:
            HealthCheckResult with health status
        """
        start_time = time.time()

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(self.health_url, timeout=5) as response:
                    response_time = time.time() - start_time
                    is_healthy = response.status == 200

                    return HealthCheckResult(
                        service_name=self.service_name,
                        is_healthy=is_healthy,
                        response_time=response_time,
                        status_code=response.status,
                    )
        except Exception as e:
            response_time = time.time() - start_time
            return HealthCheckResult(
                service_name=self.service_name,
                is_healthy=False,
                response_time=response_time,
                error=str(e),
            )

    def get_service_info(self) -> dict[str, Any]:
        """Get information about the service process.

        Returns:
            Dictionary with service information
        """
        if not PSUTIL_AVAILABLE:
            return {"error": "psutil not available"}

        try:
            # Find the service process
            for proc in psutil.process_iter(
                ["pid", "name", "cmdline", "memory_info", "cpu_percent"],
            ):
                try:
                    cmdline = proc.info.get("cmdline", [])
                    if any(self.service_name in str(arg) for arg in cmdline):
                        return {
                            "pid": proc.info.get("pid"),
                            "name": proc.info.get("name"),
                            "cmdline": cmdline,
                            "memory_mb": proc.info.get("memory_info", {}).get("rss", 0)
                            / 1024
                            / 1024,
                            "cpu_percent": proc.info.get("cpu_percent", 0),
                            "status": "running",
                        }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            return {"status": "not_found"}
        except Exception as e:
            return {"error": str(e)}

    def add_log_entry(self, entry: str) -> None:
        """Add a log entry to the buffer.

        Args:
            entry: Log entry to add
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_entry = f"[{timestamp}] {entry}"
        self.log_buffer.append(formatted_entry)

        # Keep only the last max_log_entries
        if len(self.log_buffer) > self.max_log_entries:
            self.log_buffer = self.log_buffer[-self.max_log_entries :]

    def get_recent_logs(self, count: int = 50) -> list[str]:
        """Get recent log entries.

        Args:
            count: Number of recent entries to return

        Returns:
            List of recent log entries
        """
        return self.log_buffer[-count:] if self.log_buffer else []


class KINFRACLIMonitor:
    """
    Main CLI monitoring system for KINFRA services.
    """

    def __init__(self):
        self.monitors: dict[str, ServiceMonitor] = {}
        self.is_running = False
        self.refresh_interval = 2.0

    def add_service(self, service_name: str, port: int, health_endpoint: str = "/health") -> None:
        """Add a service to monitor.

        Args:
            service_name: Name of the service
            port: Port the service is running on
            health_endpoint: Health check endpoint path
        """
        monitor = ServiceMonitor(service_name, port, health_endpoint)
        self.monitors[service_name] = monitor
        logger.info(f"Added service monitor for '{service_name}' on port {port}")

    async def start_monitoring(self) -> None:
        """
        Start monitoring all registered services.
        """
        self.is_running = True
        logger.info("🔍 Starting KINFRA CLI monitoring...")

        try:
            while self.is_running:
                await self._monitor_cycle()
                await asyncio.sleep(self.refresh_interval)
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        except Exception as e:
            logger.exception(f"Monitoring error: {e}")
        finally:
            self.is_running = False

    async def _monitor_cycle(self) -> None:
        """
        Perform one monitoring cycle.
        """
        for monitor in self.monitors.values():
            try:
                # Perform health check
                health_result = await monitor.check_health()
                monitor.health_history.append(health_result)

                # Keep only last 100 health checks
                if len(monitor.health_history) > 100:
                    monitor.health_history = monitor.health_history[-100:]

                # Add to log buffer
                status = "✅" if health_result.is_healthy else "❌"
                monitor.add_log_entry(
                    f"{status} Health check: {health_result.response_time:.3f}s "
                    f"(status: {health_result.status_code or 'error'})",
                )

            except Exception as e:
                monitor.add_log_entry(f"❌ Health check failed: {e}")

    def stop_monitoring(self) -> None:
        """
        Stop monitoring.
        """
        self.is_running = False

    def get_status_summary(self) -> dict[str, Any]:
        """Get a summary of all monitored services.

        Returns:
            Dictionary with service status summary
        """
        summary = {"timestamp": datetime.now().isoformat(), "services": {}}

        for service_name, monitor in self.monitors.items():
            # Get latest health result
            latest_health = monitor.health_history[-1] if monitor.health_history else None

            # Get service info
            service_info = monitor.get_service_info()

            summary["services"][service_name] = {
                "port": monitor.port,
                "urls": {"health": monitor.health_url, "mcp": monitor.mcp_url},
                "health": latest_health.to_dict() if latest_health else None,
                "process": service_info,
                "log_count": len(monitor.log_buffer),
            }

        return summary

    def print_status(self) -> None:
        """
        Print current status to console.
        """
        summary = self.get_status_summary()

        print("\n" + "=" * 80)
        print(f"🔍 KINFRA Service Monitor - {summary['timestamp']}")
        print("=" * 80)

        for service_name, info in summary["services"].items():
            print(f"\n📡 Service: {service_name}")
            print(f"   Port: {info['port']}")
            print(f"   Health: {info['urls']['health']}")
            print(f"   MCP: {info['urls']['mcp']}")

            if info["health"]:
                health = info["health"]
                status_icon = "✅" if health["is_healthy"] else "❌"
                print(f"   Status: {status_icon} {health['response_time']:.3f}s")
                if health["error"]:
                    print(f"   Error: {health['error']}")

            if info["process"].get("status") == "running":
                print(
                    f"   Process: PID {info['process'].get('pid', 'unknown')} "
                    f"({info['process'].get('memory_mb', 0):.1f}MB, "
                    f"{info['process'].get('cpu_percent', 0):.1f}% CPU)",
                )
            else:
                print(f"   Process: {info['process'].get('status', 'unknown')}")

            print(f"   Logs: {info['log_count']} entries")

        print("\n" + "=" * 80)

    def print_recent_logs(self, service_name: str, count: int = 20) -> None:
        """Print recent logs for a service.

        Args:
            service_name: Name of the service
            count: Number of recent logs to show
        """
        if service_name not in self.monitors:
            print(f"❌ Service '{service_name}' not found")
            return

        monitor = self.monitors[service_name]
        logs = monitor.get_recent_logs(count)

        print(f"\n📋 Recent logs for '{service_name}':")
        print("-" * 60)
        for log in logs:
            print(log)
        print("-" * 60)

    def export_logs(self, service_name: str, file_path: str) -> None:
        """Export logs to a file.

        Args:
            service_name: Name of the service
            file_path: Path to export logs to
        """
        if service_name not in self.monitors:
            print(f"❌ Service '{service_name}' not found")
            return

        monitor = self.monitors[service_name]
        logs = monitor.log_buffer

        try:
            with open(file_path, "w") as f:
                f.write(f"KINFRA Logs for {service_name}\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n")
                f.write("=" * 60 + "\n\n")
                for log in logs:
                    f.write(log + "\n")
            print(f"✅ Logs exported to {file_path}")
        except Exception as e:
            print(f"❌ Failed to export logs: {e}")


def create_monitor() -> KINFRACLIMonitor:
    """Create a new KINFRA CLI monitor instance.

    Returns:
        KINFRACLIMonitor instance
    """
    return KINFRACLIMonitor()


async def monitor_service(service_name: str, port: int, health_endpoint: str = "/health") -> None:
    """Monitor a single service.

    Args:
        service_name: Name of the service
        port: Port the service is running on
        health_endpoint: Health check endpoint path
    """
    monitor = create_monitor()
    monitor.add_service(service_name, port, health_endpoint)

    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        print(f"\n🛑 Received signal {signum}, stopping monitor...")
        monitor.stop_monitoring()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start monitoring
    await monitor.start_monitoring()


__all__ = [
    "HealthCheckResult",
    "KINFRACLIMonitor",
    "ServiceMonitor",
    "create_monitor",
    "monitor_service",
]
