"""
Smart Infrastructure Manager - KInfra Unified Infrastructure Component

⚠️ DEPRECATED: This module is deprecated in favor of the new architecture.

Use instead:
- ServiceOrchestrator + ServiceManager for service management
- ResourceManager + adapters for resource management
- KInfra for unified API

See CONSOLIDATION.md for migration guide.

This module is kept for backward compatibility and will be removed in v2.0.

---

Legacy documentation:

Intelligent port allocation, process management, and tunnel orchestration for local testing:
- Port persistence: Uses consistent ports across test runs
- Process isolation: Domain-specific process management
- Tunnel health: Built-in 503/530 detection and recovery
- Resource optimization: Reuses existing tunnels when possible
- MCP server management: Start/stop local MCP server for testing
- Test integration: Automatic fallback from local to production

Consolidated from zen-mcp-server and atoms_mcp-old for infrastructure standardization.
"""

import json
import logging
import os
import random
import shutil
import socket
import subprocess
import time
import warnings
from pathlib import Path
from threading import Thread
from urllib.parse import urlparse

import psutil
import requests

# Use standard logging that can be configured by the consuming application
logger = logging.getLogger(__name__)


class SmartInfraManager:
    """Intelligent infrastructure management for persistent ports and tunnels.

    ⚠️ DEPRECATED: Use ServiceOrchestrator + ServiceManager instead.

    Example migration:
        # Old
        manager = SmartInfraManager(project_name="zen")

        # New
        from kinfra import ServiceOrchestrator, OrchestratorConfig, KInfra
        config = OrchestratorConfig(project_name="zen")
        orchestrator = ServiceOrchestrator(config, KInfra())
    """

    def __init__(self, project_name: str = "default", domain: str = "kooshapari.com"):
        """Initialize Smart Infrastructure Manager.

        ⚠️ DEPRECATED: This class will be removed in v2.0.

        Args:
            project_name: Name of the project (e.g., 'atoms_mcp', 'zen')
            domain: Domain for tunnel configuration
        """
        warnings.warn(
            "SmartInfraManager is deprecated. Use ServiceOrchestrator + ServiceManager instead. "
            "See KInfra/libraries/python/kinfra/CONSOLIDATION.md for migration guide.",
            DeprecationWarning,
            stacklevel=2,
        )

        self.project_name = project_name
        self.domain = domain
        self.config_dir = Path.home() / ".kinfra_smart_infra"
        self.config_file = self.config_dir / f"{project_name}_config.json"
        self.config_dir.mkdir(exist_ok=True)

        # Port range for this project - configurable per project
        # Default ranges: atoms=50002, zen=8000-9000
        self.port_range = self._get_port_range(project_name)

    def _get_port_range(self, project_name: str) -> tuple[int, int]:
        """
        Get port range based on project name.
        """
        port_ranges = {
            "atoms_mcp": (50002, 50002),  # Fixed port for atoms
            "zen": (8000, 9000),
            "default": (50000, 51000),
        }
        return port_ranges.get(project_name, port_ranges["default"])

    def get_project_config(self) -> dict:
        """
        Load project configuration from disk.
        """
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load project config: {e}")

        return {
            "project_name": self.project_name,
            "domain": self.domain,
            "assigned_port": None,
            "tunnel_url": None,
            "last_healthy_check": None,
            "process_pid": None,
            "server_running": False,
            "server_start_time": None,
        }

    def save_project_config(self, config: dict) -> None:
        """
        Save project configuration to disk.
        """
        try:
            with open(self.config_file, "w") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save project config: {e}")

    def is_port_available(self, port: int) -> bool:
        """
        Check if a port is available.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return True
        except OSError:
            return False

    def get_port_occupant(self, port: int) -> dict | None:
        """Best-effort lookup for the process occupying a port.

        Strategy:
        1) Fast path via `lsof` when available (macOS/Linux), small timeout.
        2) Fallback to time-boxed psutil scan.

        Timeouts:
        - SMART_INFRA_LSOF_TIMEOUT (default 1.0s)
        - SMART_INFRA_LOOKUP_TIMEOUT (default 1.5s)
        """

        # 1) Try lsof (fast path on macOS/Linux)
        occ = self._occupant_via_lsof(port)
        if occ is not None:
            return occ

        # 2) Fallback to time-boxed psutil scan
        timeout_s = float(os.getenv("SMART_INFRA_LOOKUP_TIMEOUT", "1.5"))

        result: dict | None = None

        def _scan():
            nonlocal result
            for conn in psutil.net_connections(kind="inet"):
                # conn.laddr may be empty for some entries
                if not getattr(conn, "laddr", None):
                    continue
                if getattr(conn.laddr, "port", None) != port:
                    continue
                pid = getattr(conn, "pid", None)
                if not pid:
                    continue
                try:
                    proc = psutil.Process(pid)
                    cmdline_list = proc.cmdline() or []
                    cmdline = (
                        " ".join(cmdline_list)
                        if isinstance(cmdline_list, list)
                        else str(cmdline_list)
                    )
                    result = {
                        "pid": pid,
                        "name": proc.name(),
                        "cmdline": cmdline,
                        "cwd": proc.cwd() if hasattr(proc, "cwd") else None,
                        "is_our_project": self.is_our_project_process(proc),
                    }
                    return
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        t = Thread(target=_scan, daemon=True)
        t.start()
        t.join(timeout_s)
        if t.is_alive():
            logger.warning(
                f"Port occupant lookup timed out after {timeout_s}s for port {port}; skipping heavy scan",
            )
            return None
        return result

    def _occupant_via_lsof(self, port: int) -> dict | None:
        """Use lsof to quickly identify the PID listening on a port.

        Returns a dict similar to the psutil-based result or None if not
        found/unavailable.
        """
        try:
            if not shutil.which("lsof"):
                return None

            timeout_s = float(os.getenv("SMART_INFRA_LSOF_TIMEOUT", "1.0"))
            # Show only listening sockets on the given TCP port; suppress DNS lookups (-n) and service names (-P)
            # Output with PIDs only (-t) for speed; fallback parse with default format if needed.
            cmd = ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
            if proc.returncode == 0 and proc.stdout.strip():
                pid_str = proc.stdout.strip().splitlines()[0].strip()
                if pid_str.isdigit():
                    pid = int(pid_str)
                    try:
                        p = psutil.Process(pid)
                        cmdline_list = p.cmdline() or []
                        cmdline = (
                            " ".join(cmdline_list)
                            if isinstance(cmdline_list, list)
                            else str(cmdline_list)
                        )
                        return {
                            "pid": pid,
                            "name": p.name(),
                            "cmdline": cmdline,
                            "cwd": p.cwd() if hasattr(p, "cwd") else None,
                            "is_our_project": self.is_our_project_process(p),
                        }
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        return None
            # Fallback: try without -t to parse the first line
            cmd = ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
            if proc.returncode == 0 and proc.stdout:
                # Typical columns: COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME
                # We'll scan for the first numeric token after the command name
                for line in proc.stdout.splitlines()[1:]:
                    parts = line.split()
                    if len(parts) >= 2 and parts[1].isdigit():
                        pid = int(parts[1])
                        try:
                            p = psutil.Process(pid)
                            cmdline_list = p.cmdline() or []
                            cmdline = (
                                " ".join(cmdline_list)
                                if isinstance(cmdline_list, list)
                                else str(cmdline_list)
                            )
                            return {
                                "pid": pid,
                                "name": p.name(),
                                "cmdline": cmdline,
                                "cwd": p.cwd() if hasattr(p, "cwd") else None,
                                "is_our_project": self.is_our_project_process(p),
                            }
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            return None
        except subprocess.TimeoutExpired:
            logger.warning(f"lsof timeout while checking port {port}")
        except Exception as e:
            # Non-fatal: just fall back to psutil path
            logger.debug(f"lsof check failed for port {port}: {e}")
        return None

    def is_our_project_process(self, proc: psutil.Process) -> bool:
        """
        Check if a process belongs to our project.
        """
        try:
            cmdline_list = proc.cmdline()
            if not cmdline_list:
                return False

            cmdline = (
                " ".join(cmdline_list) if isinstance(cmdline_list, list) else str(cmdline_list)
            )

            try:
                cwd = proc.cwd()
            except (psutil.AccessDenied, AttributeError):
                cwd = None

            # Check if it's a server.py process in our project directory
            if "server.py" in cmdline:
                if cwd and self.project_name in cwd:
                    return True
                # Check if the server.py path contains our project
                for arg in cmdline_list:
                    if "server.py" in str(arg) and self.project_name in str(arg):
                        return True

            return False
        except Exception:
            return False

    def kill_our_project_processes(self) -> list[int]:
        """
        Kill existing processes from our project.
        """
        killed_pids = []
        try:
            current_pid = os.getpid()
            for proc in psutil.process_iter(["pid", "name", "cmdline", "cwd"]):
                try:
                    if proc.info["pid"] == current_pid:
                        continue

                    if self.is_our_project_process(proc):
                        logger.info(
                            f"Killing old {self.project_name} process: PID {proc.info['pid']}",
                        )
                        proc.terminate()
                        killed_pids.append(proc.info["pid"])

                        # Wait up to 5 seconds for graceful termination
                        try:
                            proc.wait(timeout=5)
                        except psutil.TimeoutExpired:
                            logger.warning(f"Force killing PID {proc.info['pid']}")
                            proc.kill()

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        except Exception as e:
            logger.warning(f"Error during process cleanup: {e}")

        return killed_pids

    def allocate_persistent_port(self) -> int:
        """
        Allocate a persistent port for the project.
        """
        config = self.get_project_config()

        # Try to reuse the previously assigned port
        if config.get("assigned_port"):
            port = config["assigned_port"]
            if self.is_port_available(port):
                logger.info(f"Reusing persistent port: {port}")
                return port
            # Best-effort occupant detection within time budget
            occupant = self.get_port_occupant(port)
            if occupant and occupant.get("is_our_project"):
                logger.info(f"Killing old {self.project_name} process on port {port}")
                try:
                    psutil.Process(occupant["pid"]).terminate()
                    time.sleep(2)  # Wait for cleanup
                    if self.is_port_available(port):
                        logger.info(f"Reclaimed persistent port: {port}")
                        return port
                except Exception as e:
                    logger.warning(f"Failed to kill old process: {e}")
            elif occupant:
                logger.info(f"Port {port} occupied by external service: {occupant.get('name')}")
            else:
                logger.info(
                    f"Port {port} is occupied (unknown occupant); selecting a new persistent port",
                )

        # Find a new available port
        attempts = 0
        while attempts < 100:
            port = random.randint(*self.port_range)
            if self.is_port_available(port):
                logger.info(f"Allocated new persistent port: {port}")
                config["assigned_port"] = port
                self.save_project_config(config)
                return port
            attempts += 1

        raise RuntimeError("Failed to allocate a port after 100 attempts")

    def check_tunnel_health(self, tunnel_url: str) -> tuple[bool, str | None]:
        """
        Check if tunnel is healthy by making HTTP requests.
        """
        if not tunnel_url:
            return False, "No tunnel URL"

        try:
            # Test both /health and /healthz endpoints
            for endpoint in ["/health", "/healthz"]:
                try:
                    response = requests.get(f"{tunnel_url}{endpoint}", timeout=10)
                    if response.status_code == 200:
                        return True, "Healthy"
                    if response.status_code in [503, 530]:
                        return False, f"Tunnel error: {response.status_code}"
                except requests.exceptions.RequestException:
                    continue
            return False, "No health endpoint responded"
        except requests.exceptions.RequestException as e:
            return False, f"Request failed: {e}"

    def check_mcp_server_health(self, port: int) -> tuple[bool, str | None]:
        """
        Check if local MCP server is healthy.
        """
        try:
            # Check if port is listening
            if self.is_port_available(port):
                return False, "Port not listening"

            # Try to connect to MCP endpoint
            response = requests.get(f"http://localhost:{port}/health", timeout=5)
            if response.status_code == 200:
                return True, "Healthy"
            return False, f"Unexpected status: {response.status_code}"
        except requests.exceptions.RequestException as e:
            return False, f"Request failed: {e}"

    def get_existing_cloudflared_processes(self) -> list[dict]:
        """
        Get information about existing cloudflared processes.
        """
        processes = []
        try:
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    if proc.info["name"] == "cloudflared" and proc.info["cmdline"]:
                        cmdline = (
                            " ".join(proc.info["cmdline"])
                            if isinstance(proc.info["cmdline"], list)
                            else str(proc.info["cmdline"])
                        )
                        # Extract port from URL argument
                        port = None
                        url = None
                        if isinstance(proc.info["cmdline"], list):
                            for i, arg in enumerate(proc.info["cmdline"]):
                                if arg == "--url" and i + 1 < len(proc.info["cmdline"]):
                                    url = proc.info["cmdline"][i + 1]
                                    parsed = urlparse(url)
                                    port = parsed.port
                                    break

                        processes.append(
                            {
                                "pid": proc.info["pid"],
                                "cmdline": cmdline,
                                "port": port,
                                "url_arg": url if port else None,
                            },
                        )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.warning(f"Error getting cloudflared processes: {e}")

        return processes

    def kill_tunnel_for_port(self, port: int) -> bool:
        """
        Kill cloudflared process for a specific port.
        """
        processes = self.get_existing_cloudflared_processes()
        for proc_info in processes:
            if proc_info["port"] == port:
                try:
                    proc = psutil.Process(proc_info["pid"])
                    logger.info(f"Killing existing tunnel for port {port}: PID {proc_info['pid']}")
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except psutil.TimeoutExpired:
                        proc.kill()
                    return True
                except Exception as e:
                    logger.warning(f"Failed to kill tunnel process {proc_info['pid']}: {e}")
        return False

    def start_cloudflare_tunnel(self, port: int, force_restart: bool = False) -> str | None:
        """
        Start CloudFlare tunnel with health checking.
        """
        config = self.get_project_config()

        # Check if we should reuse existing tunnel
        if not force_restart and config.get("tunnel_url"):
            is_healthy, reason = self.check_tunnel_health(config["tunnel_url"])
            if is_healthy:
                logger.info(f"Reusing healthy tunnel: {config['tunnel_url']}")
                return config["tunnel_url"]
            logger.warning(f"Tunnel unhealthy ({reason}), will restart")

        # Kill any existing tunnel for this port
        self.kill_tunnel_for_port(port)

        # Start new tunnel
        try:
            cmd = ["cloudflared", "tunnel", "--no-autoupdate", "--url", f"http://localhost:{port}"]

            logger.info(f"Starting CloudFlare tunnel: {' '.join(cmd)}")

            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            )

            # Parse tunnel URL from output
            tunnel_url = None
            start_time = time.time()
            while time.time() - start_time < 30:  # 30 second timeout
                line = proc.stdout.readline()
                if not line:
                    break

                if "trycloudflare.com" in line or "https://" in line:
                    import re

                    match = re.search(r"https://[\w\.-]+\.trycloudflare\.com", line)
                    if match:
                        tunnel_url = match.group(0)
                        logger.info(f"Tunnel URL discovered: {tunnel_url}")
                        break

            if tunnel_url:
                # Verify tunnel health
                time.sleep(5)  # Give tunnel time to stabilize
                is_healthy, reason = self.check_tunnel_health(tunnel_url)
                if is_healthy:
                    config["tunnel_url"] = tunnel_url
                    config["last_healthy_check"] = time.time()
                    self.save_project_config(config)
                    return tunnel_url
                logger.warning(f"New tunnel failed health check: {reason}")

        except Exception as e:
            logger.exception(f"Failed to start CloudFlare tunnel: {e}")

        return None

    def start_test_server(self, port: int, server_script: Path | None = None) -> bool:
        """Start local MCP server for testing.

        Args:
            port: Port to run the server on
            server_script: Path to server script (defaults to ../server.py from utils/)

        Returns:
            bool: True if server started successfully
        """
        config = self.get_project_config()

        # Check if server is already running
        if config.get("server_running"):
            is_healthy, reason = self.check_mcp_server_health(port)
            if is_healthy:
                logger.info(f"Local MCP server already running on port {port}")
                return True
            logger.warning(f"Server unhealthy ({reason}), will restart")
            self.stop_test_server()

        # Start server
        try:
            # Determine server script location
            if server_script is None:
                # Try to find server.py in project root
                project_root = Path(__file__).parent.parent
                server_script = project_root / "server.py"

            if not server_script.exists():
                logger.error(f"Server script not found: {server_script}")
                return False

            # Start server process
            cmd = ["python", str(server_script)]
            env = os.environ.copy()
            env["PORT"] = str(port)
            env["ATOMS_LOCAL_TEST"] = "true"
            # Ensure FastMCP runs with an HTTP transport so health checks work
            env["ATOMS_FASTMCP_TRANSPORT"] = "http"
            env["ATOMS_FASTMCP_HOST"] = env.get("ATOMS_FASTMCP_HOST", "127.0.0.1")
            env["ATOMS_FASTMCP_PORT"] = str(port)
            env.setdefault("ATOMS_FASTMCP_HTTP_PATH", "/api/mcp")

            logger.info(f"Starting local MCP server: {' '.join(cmd)}")

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd=str(server_script.parent),
            )

            # Wait for server to be ready
            start_time = time.time()
            while time.time() - start_time < 30:  # 30 second timeout
                time.sleep(1)
                is_healthy, _ = self.check_mcp_server_health(port)
                if is_healthy:
                    config["server_running"] = True
                    config["process_pid"] = proc.pid
                    config["server_start_time"] = time.time()
                    self.save_project_config(config)
                    logger.info(f"Local MCP server started successfully on port {port}")
                    return True

            logger.error("Server failed to become healthy within timeout")
            proc.terminate()
            return False

        except Exception as e:
            logger.exception(f"Failed to start local MCP server: {e}")
            return False

    def stop_test_server(self) -> bool:
        """Stop local MCP server.

        Returns:
            bool: True if server was stopped successfully
        """
        config = self.get_project_config()

        if not config.get("server_running"):
            logger.info("No local MCP server running")
            return True

        # Kill server process
        pid = config.get("process_pid")
        if pid:
            try:
                proc = psutil.Process(pid)
                logger.info(f"Stopping local MCP server (PID {pid})")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except psutil.TimeoutExpired:
                    logger.warning(f"Force killing server process {pid}")
                    proc.kill()
            except psutil.NoSuchProcess:
                logger.warning(f"Server process {pid} not found")
            except Exception as e:
                logger.exception(f"Failed to stop server process {pid}: {e}")
                return False

        # Update config
        config["server_running"] = False
        config["process_pid"] = None
        config["server_start_time"] = None
        self.save_project_config(config)

        logger.info("Local MCP server stopped")
        return True

    def setup_infrastructure(
        self, force_restart_tunnel: bool = False, start_server: bool = False,
    ) -> tuple[int, str | None]:
        """Set up complete infrastructure: port allocation and tunnel.

        Args:
            force_restart_tunnel: Force restart of CloudFlare tunnel
            start_server: Start local MCP server for testing

        Returns:
            tuple: (port, tunnel_url)
        """
        logger.info(f"Setting up smart infrastructure for {self.project_name}")

        # Clean up old processes from our project
        killed_pids = self.kill_our_project_processes()
        if killed_pids:
            logger.info(f"Cleaned up {len(killed_pids)} old processes")

        # Allocate persistent port
        port = self.allocate_persistent_port()

        # Start local server if requested
        if start_server:
            success = self.start_test_server(port)
            if not success:
                logger.error("Failed to start local MCP server")

        # Set up tunnel if enabled
        tunnel_url = None
        if os.getenv("AUTO_TUNNEL", "").lower() in ("1", "true", "yes", "on"):
            tunnel_url = self.start_cloudflare_tunnel(port, force_restart_tunnel)
            if tunnel_url:
                logger.info(f"Public access: {tunnel_url}")
            else:
                logger.warning("Failed to establish tunnel")

        # Update config with current process
        config = self.get_project_config()
        config["process_pid"] = os.getpid()
        config["assigned_port"] = port
        if tunnel_url:
            config["tunnel_url"] = tunnel_url
        self.save_project_config(config)

        return port, tunnel_url


def get_smart_infra_manager(
    project_name: str = "default", domain: str = "kooshapari.com",
) -> SmartInfraManager:
    """Get a SmartInfraManager instance.

    Args:
        project_name: Name of the project (e.g., 'atoms_mcp', 'zen')
        domain: Domain for tunnel configuration

    Returns:
        SmartInfraManager instance
    """
    return SmartInfraManager(project_name, domain)
