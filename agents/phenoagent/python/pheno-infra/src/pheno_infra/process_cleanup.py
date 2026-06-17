"""Enhanced Process Cleanup for KINFRA.

Provides intelligent process cleanup before service startup, with configurable resource
cleanup options for shared vs dedicated resources.
"""

import logging
import os
import time
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class ProcessCleanupConfig:
    """
    Configuration for process cleanup operations.
    """

    def __init__(
        self,
        cleanup_shared_resources: bool = False,
        cleanup_tunnels: bool = True,
        cleanup_dns_servers: bool = True,
        cleanup_related_services: bool = True,
        grace_period: float = 3.0,
        force_kill: bool = True,
    ):
        self.cleanup_shared_resources = cleanup_shared_resources
        self.cleanup_tunnels = cleanup_tunnels
        self.cleanup_dns_servers = cleanup_dns_servers
        self.cleanup_related_services = cleanup_related_services
        self.grace_period = grace_period
        self.force_kill = force_kill


class ProcessCleanupManager:
    """
    Manages process cleanup operations for KINFRA services.
    """

    # Process patterns to identify related services
    TUNNEL_PATTERNS = ["cloudflared", "ngrok", "localtunnel", "tunnel", "tunnel-sync"]

    DNS_SERVER_PATTERNS = ["dnsmasq", "unbound", "bind9", "named", "dns-server"]

    RELATED_SERVICE_PATTERNS = ["atoms-mcp", "zen-mcp", "mcp-server", "fastmcp", "pheno-sdk"]

    def __init__(self, config: Optional[ProcessCleanupConfig] = None, registry=None):
        self.config = config or ProcessCleanupConfig()
        self.current_pid = os.getpid()
        self.registry = registry
        self.cleanup_stats = {
            "inspected": 0,
            "terminated": 0,
            "force_killed": 0,
            "skipped": 0,
            "errors": 0,
        }

    def cleanup_before_startup(self, service_name: str) -> Dict[str, int]:
        """Perform comprehensive cleanup before starting a service.

        Args:
            service_name: Name of the service being started

        Returns:
            Dictionary with cleanup statistics
        """
        logger.info(f"🧹 Starting process cleanup for service '{service_name}'")

        # Reset stats
        self.cleanup_stats = {
            "inspected": 0,
            "terminated": 0,
            "force_killed": 0,
            "skipped": 0,
            "errors": 0,
        }

        if not PSUTIL_AVAILABLE:
            logger.warning("psutil not available, skipping process cleanup")
            return self.cleanup_stats

        try:
            # Clean up tunnels if enabled
            if self.config.cleanup_tunnels:
                self._cleanup_processes(self.TUNNEL_PATTERNS, "tunnel")

            # Clean up DNS servers if enabled
            if self.config.cleanup_dns_servers:
                self._cleanup_processes(self.DNS_SERVER_PATTERNS, "DNS server")

            # Clean up related services if enabled
            if self.config.cleanup_related_services:
                self._cleanup_processes(self.RELATED_SERVICE_PATTERNS, "related service")

            # Clean up shared resources if enabled
            if self.config.cleanup_shared_resources:
                self._cleanup_shared_resources()

            logger.info(f"✅ Process cleanup completed: {self.cleanup_stats}")
            return self.cleanup_stats

        except Exception as e:
            logger.error(f"❌ Process cleanup failed: {e}")
            self.cleanup_stats["errors"] += 1
            return self.cleanup_stats

    def _cleanup_processes(self, patterns: List[str], process_type: str) -> None:
        """Clean up processes matching the given patterns.

        Args:
            patterns: List of process name patterns to match
            process_type: Human-readable description of the process type
        """
        logger.debug(f"Cleaning up {process_type} processes...")

        processes_to_terminate = []

        for proc in psutil.process_iter(["pid", "name", "cmdline", "ppid"]):
            self.cleanup_stats["inspected"] += 1

            try:
                pid = proc.info.get("pid")
                if pid is None or pid == self.current_pid:
                    self.cleanup_stats["skipped"] += 1
                    continue

                # Skip if parent process is current process
                if proc.info.get("ppid") == self.current_pid:
                    self.cleanup_stats["skipped"] += 1
                    continue

                name = (proc.info.get("name") or "").lower()
                cmdline = proc.info.get("cmdline") or []
                cmdline_str = " ".join(str(part) for part in cmdline).lower()

                # Check if process matches any pattern
                matches = False
                for pattern in patterns:
                    if pattern.lower() in name or pattern.lower() in cmdline_str:
                        matches = True
                        break

                if matches:
                    logger.info(f"Found {process_type} process: {name} (PID: {pid})")
                    processes_to_terminate.append(proc)

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception as e:
                logger.debug(f"Error inspecting process: {e}")
                self.cleanup_stats["errors"] += 1
                continue

        # Terminate matching processes
        if processes_to_terminate:
            self._terminate_processes(processes_to_terminate, process_type)

    def _terminate_processes(self, processes: List[psutil.Process], process_type: str) -> None:
        """Terminate a list of processes.

        Args:
            processes: List of processes to terminate
            process_type: Human-readable description of the process type
        """
        logger.info(f"Terminating {len(processes)} {process_type} processes...")

        # For tunnel processes (especially cloudflared), use SIGKILL immediately
        # They don't respond well to SIGTERM and often become zombies
        use_sigkill = process_type == "tunnel"

        # Send termination signal to all processes
        for proc in processes:
            try:
                if use_sigkill:
                    proc.kill()  # SIGKILL for tunnels
                    logger.debug(f"Sent SIGKILL to {process_type} process {proc.pid}")
                else:
                    proc.terminate()  # SIGTERM for others
                    logger.debug(f"Sent SIGTERM to {process_type} process {proc.pid}")
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                logger.debug(f"Could not terminate {process_type} process {proc.pid}: {e}")
                continue
            except Exception as e:
                logger.warning(f"Error terminating {process_type} process {proc.pid}: {e}")
                self.cleanup_stats["errors"] += 1
                continue

        # Wait for termination
        if processes:
            try:
                timeout = 2.0 if use_sigkill else self.config.grace_period
                gone, alive = psutil.wait_procs(processes, timeout=timeout)

                if use_sigkill:
                    # All were force killed
                    self.cleanup_stats["force_killed"] += len(gone)
                    self.cleanup_stats["terminated"] += len(gone)
                else:
                    self.cleanup_stats["terminated"] += len(gone)

                # Force kill remaining processes if enabled (only for non-tunnel processes)
                if alive and self.config.force_kill and not use_sigkill:
                    logger.warning(
                        f"Force killing {len(alive)} stubborn {process_type} processes..."
                    )
                    for proc in alive:
                        try:
                            proc.kill()
                            logger.debug(f"Force killed {process_type} process {proc.pid}")
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                        except Exception as e:
                            logger.warning(
                                f"Error force killing {process_type} process {proc.pid}: {e}"
                            )
                            self.cleanup_stats["errors"] += 1
                            continue

                    # Wait for force killed processes
                    gone_after_kill, still_alive = psutil.wait_procs(alive, timeout=2.0)
                    self.cleanup_stats["force_killed"] += len(gone_after_kill)
                    alive = still_alive

                # Log any processes that still won't die
                for proc in alive:
                    logger.error(
                            f"{process_type} process {proc.pid} survived all termination attempts"
                        )
                        self.cleanup_stats["errors"] += 1

            except Exception as e:
                logger.error(f"Error during process termination: {e}")
                self.cleanup_stats["errors"] += 1

    def _cleanup_shared_resources(self) -> None:
        """Clean up shared resources that might conflict with the service.

        This includes things like shared ports, temporary files, etc.
        """
        logger.debug("Cleaning up shared resources...")

        # Clean up temporary files
        self._cleanup_temp_files()

        # Clean up shared ports
        self._cleanup_shared_ports()

    def _cleanup_temp_files(self) -> None:
        """
        Clean up temporary files that might conflict.
        """
        import glob
        import tempfile

        temp_dirs = [
            tempfile.gettempdir(),
            "/tmp",
            os.path.expanduser("~/.cache"),
            os.path.expanduser("~/.kinfra"),
        ]

        for temp_dir in temp_dirs:
            if not os.path.exists(temp_dir):
                continue

            # Look for KINFRA-related temp files
            patterns = ["kinfra_*", "atoms_*", "mcp_*", "pheno_*"]

            for pattern in patterns:
                try:
                    files = glob.glob(os.path.join(temp_dir, pattern))
                    for file_path in files:
                        try:
                            if os.path.isfile(file_path):
                                os.remove(file_path)
                                logger.debug(f"Removed temp file: {file_path}")
                        except OSError:
                            pass
                except Exception:
                    pass

    def _cleanup_shared_ports(self) -> None:
        """
        Clean up shared ports that might conflict.
        """
        # This would be implemented based on specific port cleanup needs
        # For now, we rely on the port allocator to handle port conflicts
        pass

    def get_cleanup_stats(self) -> Dict[str, int]:
        """Get the current cleanup statistics.

        Returns:
            Dictionary with cleanup statistics
        """
        return self.cleanup_stats.copy()

    def reset_stats(self) -> None:
        """
        Reset cleanup statistics.
        """
        self.cleanup_stats = {
            "inspected": 0,
            "terminated": 0,
            "force_killed": 0,
            "skipped": 0,
            "errors": 0,
        }

    def cleanup_by_metadata(
        self,
        project: Optional[str] = None,
        service: Optional[str] = None,
        scope: Optional[str] = None,
    ) -> Dict[str, int]:
        """Clean up processes using metadata-aware filtering instead of name heuristics.

        Args:
            project: Optional project identifier to filter by
            service: Optional service type to filter by
            scope: Optional scope identifier to filter by

        Returns:
            Dictionary with cleanup statistics
        """
        logger.info(f"🧹 Starting metadata-aware cleanup (project={project}, service={service}, scope={scope})")

        # Reset stats
        self.reset_stats()

        if not self.registry:
            logger.warning("No registry available, falling back to pattern-based cleanup")
            return self.cleanup_stats

        if not PSUTIL_AVAILABLE:
            logger.warning("psutil not available, skipping process cleanup")
            return self.cleanup_stats

        try:
            # Get all services from registry
            all_services = self.registry.get_all_services()

            # Filter services by metadata
            matching_services = []
            for service_name, service_info in all_services.items():
                if project and getattr(service_info, "project", None) != project:
                    continue
                if service and getattr(service_info, "service", None) != service:
                    continue
                if scope and getattr(service_info, "scope", None) != scope:
                    continue
                matching_services.append((service_name, service_info))

            logger.info(f"Found {len(matching_services)} services matching metadata filters")

            # Clean up processes for matching services
            processes_to_terminate = []
            for service_name, service_info in matching_services:
                pid = service_info.pid
                if pid and pid != self.current_pid:
                    try:
                        proc = psutil.Process(pid)
                        logger.info(f"Found process for service '{service_name}': PID {pid}")
                        processes_to_terminate.append(proc)
                        self.cleanup_stats["inspected"] += 1
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        logger.debug(f"Process {pid} for service '{service_name}' no longer exists")
                        self.cleanup_stats["skipped"] += 1
                    except Exception as e:
                        logger.warning(f"Error accessing process {pid}: {e}")
                        self.cleanup_stats["errors"] += 1

            # Terminate matching processes
            if processes_to_terminate:
                self._terminate_processes(processes_to_terminate, "metadata-filtered")

            logger.info(f"✅ Metadata-aware cleanup completed: {self.cleanup_stats}")
            return self.cleanup_stats

        except Exception as e:
            logger.error(f"❌ Metadata-aware cleanup failed: {e}")
            self.cleanup_stats["errors"] += 1
            return self.cleanup_stats


def cleanup_before_startup(
    service_name: str, config: Optional[ProcessCleanupConfig] = None
) -> Dict[str, int]:
    """Convenience function to perform process cleanup before startup.

    Args:
        service_name: Name of the service being started
        config: Optional cleanup configuration

    Returns:
        Dictionary with cleanup statistics
    """
    manager = ProcessCleanupManager(config)
    return manager.cleanup_before_startup(service_name)


__all__ = ["ProcessCleanupConfig", "ProcessCleanupManager", "cleanup_before_startup"]
