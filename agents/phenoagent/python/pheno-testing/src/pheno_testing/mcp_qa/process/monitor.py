"""Process Monitoring System.

Tracks running processes, collects PIDs, and provides health status. Integrates with the
Rich TUI framework for beautiful display.
"""

import subprocess
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

import psutil

from pheno.testing.mcp_qa.logging import get_logger

try:
    from rich.box import ROUNDED
    from rich.console import Console
    from rich.table import Table

    HAS_RICH = True
except ImportError:
    HAS_RICH = False


class ProcessStatus(Enum):
    """
    Process status.
    """

    RUNNING = "running"
    STOPPED = "stopped"
    STARTING = "starting"
    STOPPING = "stopping"
    FAILED = "failed"
    UNKNOWN = "unknown"


class HealthStatus(Enum):
    """
    Health status.
    """

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    ACTIVE = "active"
    UNKNOWN = "unknown"


@dataclass
class ProcessInfo:
    """
    Information about a monitored process.
    """

    name: str
    pid: Optional[int] = None
    port: Optional[int] = None
    status: ProcessStatus = ProcessStatus.UNKNOWN
    health: HealthStatus = HealthStatus.UNKNOWN
    command: Optional[str] = None
    cwd: Optional[str] = None
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    started_at: Optional[datetime] = None
    last_checked: Optional[datetime] = None

    @property
    def status_emoji(self) -> str:
        """
        Get emoji for status.
        """
        return {
            ProcessStatus.RUNNING: "●",
            ProcessStatus.STOPPED: "○",
            ProcessStatus.STARTING: "◐",
            ProcessStatus.STOPPING: "◑",
            ProcessStatus.FAILED: "✗",
            ProcessStatus.UNKNOWN: "?",
        }.get(self.status, "?")

    @property
    def health_emoji(self) -> str:
        """
        Get emoji for health.
        """
        return {
            HealthStatus.HEALTHY: "●",
            HealthStatus.UNHEALTHY: "✗",
            HealthStatus.DEGRADED: "◐",
            HealthStatus.ACTIVE: "●",
            HealthStatus.UNKNOWN: "?",
        }.get(self.health, "?")


class ProcessMonitor:
    """Monitor running processes with PID collection and health checking.

    Features:
    - Find PIDs by port, name, or command
    - Check process health
    - Track resource usage
    - Rich table display
    """

    def __init__(self):
        """
        Initialize process monitor.
        """
        self.processes: Dict[str, ProcessInfo] = {}
        self.logger = get_logger(__name__)

    def find_pid_by_port(self, port: int) -> Optional[int]:
        """Find PID of process listening on a port.

        Args:
            port: Port number

        Returns:
            PID if found, None otherwise
        """
        try:
            # Try lsof first (more reliable on macOS)
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"], capture_output=True, text=True, check=False
            )

            if result.returncode == 0 and result.stdout.strip():
                pid = int(result.stdout.strip().split()[0])
                self.logger.debug(f"Found PID {pid} on port {port} (lsof)")
                return pid
        except Exception as e:
            self.logger.debug(f"lsof failed: {e}")

        try:
            # Fallback: Use psutil
            for conn in psutil.net_connections():
                if conn.status == "LISTEN" and conn.laddr.port == port:
                    if conn.pid:
                        self.logger.debug(f"Found PID {conn.pid} on port {port} (psutil)")
                        return conn.pid
        except Exception as e:
            self.logger.debug(f"psutil failed: {e}")

        return None

    def find_pids_by_name(self, name: str) -> List[int]:
        """Find PIDs of processes by name.

        Args:
            name: Process name (partial match)

        Returns:
            List of PIDs
        """
        pids = []
        try:
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    proc_name = proc.info["name"] or ""
                    cmdline = " ".join(proc.info["cmdline"] or [])

                    if name.lower() in proc_name.lower() or name.lower() in cmdline.lower():
                        pids.append(proc.info["pid"])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            self.logger.warning(f"Error finding PIDs by name: {e}")

        return pids

    def find_pid_by_command(self, command_pattern: str) -> Optional[int]:
        """Find PID of process by command pattern.

        Args:
            command_pattern: Pattern to match in command line

        Returns:
            First matching PID, or None
        """
        pids = []
        try:
            result = subprocess.run(
                ["pgrep", "-f", command_pattern], capture_output=True, text=True, check=False
            )

            if result.returncode == 0 and result.stdout.strip():
                pids = [int(p) for p in result.stdout.strip().split("\n")]
        except Exception as e:
            self.logger.debug(f"pgrep failed: {e}")

        return pids[0] if pids else None

    def get_process_info(self, pid: int) -> Optional[ProcessInfo]:
        """Get detailed information about a process.

        Args:
            pid: Process ID

        Returns:
            ProcessInfo if process exists, None otherwise
        """
        try:
            proc = psutil.Process(pid)

            # Get basic info
            info = ProcessInfo(
                name=proc.name(),
                pid=pid,
                status=ProcessStatus.RUNNING,
                command=" ".join(proc.cmdline()),
                cwd=proc.cwd(),
                cpu_percent=proc.cpu_percent(interval=0.1),
                memory_mb=proc.memory_info().rss / 1024 / 1024,
                started_at=datetime.fromtimestamp(proc.create_time()),
                last_checked=datetime.now(),
            )

            # Try to get listening port
            for conn in proc.connections():
                if conn.status == "LISTEN" and conn.laddr:
                    info.port = conn.laddr.port
                    break

            return info

        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            self.logger.debug(f"Cannot access process {pid}: {e}")
            return None

    def register_process(
        self,
        name: str,
        port: Optional[int] = None,
        pid: Optional[int] = None,
        command_pattern: Optional[str] = None,
    ) -> ProcessInfo:
        """Register a process for monitoring.

        Args:
            name: Display name for process
            port: Port to check (will find PID automatically)
            pid: Known PID
            command_pattern: Pattern to find PID by command

        Returns:
            ProcessInfo object
        """
        # Try to find PID if not provided
        if not pid:
            if port:
                pid = self.find_pid_by_port(port)
            elif command_pattern:
                pid = self.find_pid_by_command(command_pattern)

        # Get detailed info if PID found
        if pid:
            info = self.get_process_info(pid)
            if info:
                info.name = name  # Use display name
                if port:
                    info.port = port
                self.processes[name] = info
                self.logger.info(f"Registered process: {name} (PID {pid})")
                return info

        # Create placeholder if PID not found
        info = ProcessInfo(name=name, port=port, status=ProcessStatus.STOPPED)
        self.processes[name] = info
        self.logger.warning(f"Registered process without PID: {name}")
        return info

    def update_process(self, name: str) -> Optional[ProcessInfo]:
        """Update information for a registered process.

        Args:
            name: Process name

        Returns:
            Updated ProcessInfo, or None if not found
        """
        if name not in self.processes:
            return None

        info = self.processes[name]

        # Try to find PID if missing
        if not info.pid:
            if info.port:
                info.pid = self.find_pid_by_port(info.port)

        # Update info if PID available
        if info.pid:
            updated = self.get_process_info(info.pid)
            if updated:
                # Preserve display name and port
                updated.name = info.name
                updated.port = info.port or updated.port
                self.processes[name] = updated
                return updated
            else:
                # Process not found - mark as stopped
                info.status = ProcessStatus.STOPPED
                info.pid = None

        return info

    def update_all(self):
        """
        Update all registered processes.
        """
        for name in list(self.processes.keys()):
            self.update_process(name)

    def check_health(self, name: str, health_url: Optional[str] = None) -> HealthStatus:
        """Check health of a process.

        Args:
            name: Process name
            health_url: Optional URL to check health endpoint

        Returns:
            HealthStatus
        """
        if name not in self.processes:
            return HealthStatus.UNKNOWN

        info = self.processes[name]

        # Basic check: is process running?
        if not info.pid or info.status != ProcessStatus.RUNNING:
            info.health = HealthStatus.UNHEALTHY
            return HealthStatus.UNHEALTHY

        # Check if process is still alive
        try:
            proc = psutil.Process(info.pid)
            if not proc.is_running():
                info.health = HealthStatus.UNHEALTHY
                return HealthStatus.UNHEALTHY
        except psutil.NoSuchProcess:
            info.health = HealthStatus.UNHEALTHY
            return HealthStatus.UNHEALTHY

        # TODO: Check health_url if provided
        # For now, just mark as active if running
        info.health = HealthStatus.ACTIVE
        return HealthStatus.ACTIVE

    def create_status_table(self) -> Optional[Table]:
        """Create a Rich table showing process status.

        Returns:
            Rich Table object
        """
        if not HAS_RICH:
            return None

        table = Table(title="Process Status", show_header=True, box=ROUNDED, border_style="cyan")

        table.add_column("Process", style="cyan", no_wrap=True)
        table.add_column("Status", justify="center")
        table.add_column("Port", justify="right")
        table.add_column("PID", justify="right")
        table.add_column("Health", justify="center")
        table.add_column("CPU %", justify="right")
        table.add_column("Memory (MB)", justify="right")

        for name, info in self.processes.items():
            table.add_row(
                name,
                f"{info.status_emoji} {info.status.value}",
                str(info.port) if info.port else "-",
                str(info.pid) if info.pid else "-",
                f"{info.health_emoji} {info.health.value}",
                f"{info.cpu_percent:.1f}" if info.cpu_percent else "-",
                f"{info.memory_mb:.1f}" if info.memory_mb else "-",
            )

        return table

    def print_status(self, console: Optional[Console] = None):
        """Print process status table.

        Args:
            console: Rich Console instance
        """
        if not HAS_RICH:
            # Fallback to simple print
            print("\nProcess Status:")
            for name, info in self.processes.items():
                print(f"  {name}: PID={info.pid}, Port={info.port}, Status={info.status.value}")
            return

        console = console or Console()
        table = self.create_status_table()
        if table:
            console.print(table)

    def get_all_pids(self) -> Dict[str, Optional[int]]:
        """Get all process PIDs.

        Returns:
            Dictionary mapping process name to PID
        """
        return {name: info.pid for name, info in self.processes.items()}

    def stop_process(self, name: str, timeout: int = 10) -> bool:
        """Stop a monitored process.

        Args:
            name: Process name
            timeout: Timeout in seconds

        Returns:
            True if stopped successfully
        """
        if name not in self.processes:
            return False

        info = self.processes[name]
        if not info.pid:
            return False

        try:
            proc = psutil.Process(info.pid)
            proc.terminate()

            # Wait for process to stop
            try:
                proc.wait(timeout=timeout)
                info.status = ProcessStatus.STOPPED
                info.pid = None
                self.logger.info(f"Stopped process: {name}")
                return True
            except psutil.TimeoutExpired:
                # Force kill if needed
                proc.kill()
                proc.wait(timeout=5)
                info.status = ProcessStatus.STOPPED
                info.pid = None
                self.logger.warning(f"Force killed process: {name}")
                return True

        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            self.logger.error(f"Cannot stop process {name}: {e}")
            return False

    def cleanup(self):
        """
        Clean up monitor (stop all processes if needed).
        """
        self.processes.clear()


# Convenience function
def create_process_monitor() -> ProcessMonitor:
    """Create a process monitor instance.

    Returns:
        ProcessMonitor instance
    """
    return ProcessMonitor()
