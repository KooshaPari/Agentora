"""
Tunnel sync core functionality - tunnel lifecycle and process management.
"""

import json
import logging
import shutil
import subprocess
from pathlib import Path

from ..exceptions import ConfigurationError, TunnelError
from ..port_registry import PortRegistry
from ..utils.dns import dns_safe_slug
from ..utils.health import check_tunnel_health
from .models import TunnelInfo
from . import handlers

logger = logging.getLogger(__name__)

class TunnelManager:
    """Intelligent tunnel manager with automatic configuration synchronization."""

    def __init__(
        self,
        registry: PortRegistry | None = None,
        domain: str = "kooshapari.com",
        cf_api_token: str | None = None,
        use_unified_tunnel: bool = True,
        cleanup_on_start: bool = True,
    ):
        self.registry = registry or PortRegistry()
        self.domain = domain.lower()
        self.cloudflared_dir = Path.home() / ".cloudflared"
        self.cloudflared_dir.mkdir(exist_ok=True)

        self.tunnel_startup_timeout = 30.0
        self.health_check_interval = 60.0
        self._running_processes: dict[str, subprocess.Popen] = {}

        self.use_unified_tunnel = use_unified_tunnel
        self._unified_tunnel_id: str | None = None
        self._unified_config_path: Path | None = None
        self._service_routes: dict[str, tuple[int, str]] = {}

        self.cf_client = None
        self.cf_zone_id = None
        if handlers.HAS_CF_SDK:
            api_token = handlers.load_cloudflare_token(
                self.domain,
                cf_api_token,
                self.cloudflared_dir,
            )

            if api_token:
                try:
                    self.cf_client = handlers.Cloudflare(api_token=api_token)
                    self.cf_zone_id = handlers.get_zone_id(self.domain, self.cf_client)
                    logger.info(f"Cloudflare API initialized for domain {self.domain}")
                except Exception as e:
                    logger.warning(f"Failed to initialize Cloudflare API: {e}")
                    logger.info("Falling back to cloudflared CLI for DNS management")
            else:
                logger.info(
                    "No CLOUDFLARE_API_TOKEN found, using cloudflared CLI for DNS"
                )

        handlers.verify_cloudflared_setup(self.cloudflared_dir)

        if cleanup_on_start and self.use_unified_tunnel:
            logger.info("Performing automatic cleanup for unified tunnel setup...")
            self._cleanup_for_unified_tunnel()

    def _cleanup_for_unified_tunnel(self):
        """Comprehensive cleanup before setting up unified tunnel."""
        logger.info(f"Starting cleanup for unified tunnel on domain: {self.domain}")

        logger.info("Stopping all running cloudflared processes...")
        handlers.stop_all_cloudflared_processes()

        logger.info("Listing existing Cloudflare tunnels...")
        existing_tunnels = handlers.list_all_tunnels()
        if existing_tunnels:
            logger.info(f"Found {len(existing_tunnels)} existing tunnel(s):")
            for tunnel in existing_tunnels:
                logger.info(f"  - {tunnel.get('name')} (ID: {tunnel.get('id')})")

        logger.info(f"Cleaning up DNS records for domain: {self.domain}")
        handlers.cleanup_dns_records(self.domain, self.cf_client, self.cf_zone_id)

        logger.info("Cleaning up old config files...")
        handlers.cleanup_old_configs(self.domain, self.cloudflared_dir)

        logger.info("Cleanup complete. Ready for unified tunnel setup.")
    def start_tunnel(self, service_name: str, port: int, path: str = "/") -> TunnelInfo:
        """Start or update a tunnel for a service."""
        logger.info(
            f"Starting tunnel for service '{service_name}' on port {port}, path '{path}'"
        )

        if self.use_unified_tunnel:
            return self._start_unified_tunnel_service(service_name, port, path)
        return self._start_separate_tunnel(service_name, port)
    def _start_unified_tunnel_service(
        self, service_name: str, port: int, path: str
    ) -> TunnelInfo:
        """Add service to unified tunnel with path-based routing."""
        logger.info(
            f"Adding service '{service_name}' to unified tunnel: port={port}, path='{path}'",
        )

        self._service_routes[service_name] = (port, path)

        if not self._unified_tunnel_id:
            tunnel_name = f"{self.domain.split('.')[0]}-unified"
            logger.info(f"Initializing unified tunnel: {tunnel_name}")

            self._unified_tunnel_id = self._find_existing_tunnel(tunnel_name)
            if self._unified_tunnel_id:
                logger.info(
                    f"Found existing tunnel '{tunnel_name}' with ID: {self._unified_tunnel_id}",
                )
            else:
                logger.info(f"Creating new tunnel '{tunnel_name}'")
                self._unified_tunnel_id = self._create_cloudflare_tunnel(tunnel_name)
                logger.info(
                    f"Created tunnel '{tunnel_name}' with ID: {self._unified_tunnel_id}"
                )

            logger.info(f"Setting up DNS for domain: {self.domain}")
            handlers.setup_dns_route(
                self._unified_tunnel_id,
                self.domain,
                self.cf_client,
                self.cf_zone_id,
                self.cloudflared_dir,
            )
            logger.info(
                f"DNS configured: {self.domain} -> tunnel {self._unified_tunnel_id}"
            )

        logger.info(
            f"Generating unified config with {len(self._service_routes)} service(s)"
        )
        self._unified_config_path = handlers.generate_unified_config(
            self.domain,
            self._unified_tunnel_id,
            self._service_routes,
            self.cloudflared_dir,
        )

        if "unified" in self._running_processes:
            logger.info("Restarting unified tunnel process with updated configuration")
            self._stop_tunnel_process("unified")
        else:
            logger.info("Starting unified tunnel process")

        assert self._unified_config_path is not None
        self._start_tunnel_process("unified", self._unified_config_path)

        self.registry.update_service(
            service_name,
            tunnel_id=self._unified_tunnel_id,
            tunnel_hostname=self.domain,
            config_path=str(self._unified_config_path),
        )

        logger.info(f"Service '{service_name}' added to unified tunnel successfully")
        logger.info(f"Service URL: https://{self.domain}{path}")

        return TunnelInfo(
            tunnel_id=self._unified_tunnel_id,
            hostname=self.domain,
            config_path=str(self._unified_config_path),
            port=port,
            status="running",
        )
    def _start_separate_tunnel(self, service_name: str, port: int) -> TunnelInfo:
        """Start individual tunnel for a service (old method)."""
        service_slug = dns_safe_slug(service_name)
        hostname = f"{service_slug}.{self.domain}"

        service_info = self.registry.get_service(service_name)
        if service_info and service_info.tunnel_id:
            if service_info.assigned_port != port:
                logger.info(
                    f"Port changed for '{service_name}': {service_info.assigned_port} -> {port}",
                )
                return self._update_tunnel_port(
                    service_name,
                    service_info.tunnel_id,
                    hostname,
                    port,
                )
            if self._is_tunnel_running(service_info.tunnel_id, hostname):
                logger.info(f"Tunnel for '{service_name}' already running")
                return TunnelInfo(
                    tunnel_id=service_info.tunnel_id,
                    hostname=hostname,
                    config_path=service_info.config_path or "",
                    port=port,
                    status="running",
                )

        return self._create_tunnel(service_name, service_slug, hostname, port)

    def _create_tunnel(
        self,
        service_name: str,
        service_slug: str,
        hostname: str,
        port: int,
    ) -> TunnelInfo:
        """Create a new tunnel for the service."""
        logger.info(f"Creating new tunnel: {hostname} -> localhost:{port}")

        tunnel_name = f"{service_slug}-tunnel"

        tunnel_id = self._find_existing_tunnel(tunnel_name)
        if not tunnel_id:
            tunnel_id = self._create_cloudflare_tunnel(tunnel_name)

        handlers.setup_dns_route(
            tunnel_id,
            hostname,
            self.cf_client,
            self.cf_zone_id,
            self.cloudflared_dir,
        )

        config_path = handlers.generate_tunnel_config(
            service_slug,
            tunnel_id,
            hostname,
            port,
            self.cloudflared_dir,
        )

        self._start_tunnel_process(service_name, config_path)

        self.registry.update_service(
            service_name,
            tunnel_id=tunnel_id,
            tunnel_hostname=hostname,
            config_path=str(config_path),
        )

        tunnel_info = TunnelInfo(
            tunnel_id=tunnel_id,
            hostname=hostname,
            config_path=str(config_path),
            port=port,
            status="starting",
        )

        logger.info(f"Tunnel created: {hostname}")
        return tunnel_info

    def _update_tunnel_port(
        self,
        service_name: str,
        tunnel_id: str,
        hostname: str,
        new_port: int,
    ) -> TunnelInfo:
        """Update tunnel configuration for port change."""
        logger.info(
            f"Updating tunnel port for '{service_name}': {hostname} -> localhost:{new_port}",
        )

        self._stop_tunnel_process(service_name)

        service_slug = hostname.split(".", maxsplit=1)[0]
        config_path = handlers.generate_tunnel_config(
            service_slug,
            tunnel_id,
            hostname,
            new_port,
            self.cloudflared_dir,
        )

        self._start_tunnel_process(service_name, config_path)

        self.registry.update_service(service_name, config_path=str(config_path))

        return TunnelInfo(
            tunnel_id=tunnel_id,
            hostname=hostname,
            config_path=str(config_path),
            port=new_port,
            status="starting",
        )

    def _find_existing_tunnel(self, tunnel_name: str) -> str | None:
        """Find existing cloudflare tunnel by name."""
        try:
            result = subprocess.run(
                ["cloudflared", "tunnel", "list", "--output", "json"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                tunnels = json.loads(result.stdout)
                for tunnel in tunnels:
                    if tunnel.get("name") == tunnel_name:
                        return tunnel.get("id")
        except (
            subprocess.TimeoutExpired,
            json.JSONDecodeError,
            subprocess.SubprocessError,
        ) as e:
            logger.warning(f"Failed to list tunnels: {e}")

        return None

    def _create_cloudflare_tunnel(self, tunnel_name: str) -> str:
        """Create a new cloudflare tunnel."""
        logger.info(f"Creating cloudflare tunnel: {tunnel_name}")

        try:
            result = subprocess.run(
                ["cloudflared", "tunnel", "create", tunnel_name],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                raise TunnelError(
                    f"Failed to create tunnel '{tunnel_name}': {result.stderr}"
                )

            tunnel_id = self._find_existing_tunnel(tunnel_name)
            if not tunnel_id:
                raise TunnelError(f"Tunnel '{tunnel_name}' created but ID not found")

            logger.info(f"Created tunnel '{tunnel_name}' with ID: {tunnel_id}")
            return tunnel_id

        except subprocess.TimeoutExpired:
            raise TunnelError(f"Timeout creating tunnel '{tunnel_name}'")

    def _start_tunnel_process(self, service_name: str, config_path: Path):
        """Start the cloudflared tunnel process."""
        logger.info(
            f"Starting tunnel process for '{service_name}' with config: {config_path}"
        )

        self._stop_tunnel_process(service_name)

        try:
            process = subprocess.Popen(
                ["cloudflared", "tunnel", "--config", str(config_path), "run"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            self._running_processes[service_name] = process
            logger.info(
                f"Started tunnel process for '{service_name}' (PID: {process.pid})"
            )

            self.registry.update_service(service_name, pid=process.pid)

        except OSError as e:
            raise TunnelError(
                f"Failed to start tunnel process for '{service_name}': {e}"
            )

    def _stop_tunnel_process(self, service_name: str) -> bool:
        """Stop the tunnel process for a service."""
        if service_name in self._running_processes:
            process = self._running_processes[service_name]
            logger.info(
                f"Stopping tunnel process for '{service_name}' (PID: {process.pid})"
            )

            try:
                process.terminate()
                process.wait(timeout=5.0)
                del self._running_processes[service_name]
                logger.info(f"Tunnel process for '{service_name}' stopped gracefully")
                return True
            except subprocess.TimeoutExpired:
                logger.warning(f"Force killing tunnel process for '{service_name}'")
                process.kill()
                process.wait()
                del self._running_processes[service_name]
                return True
            except Exception as e:
                logger.exception(
                    f"Error stopping tunnel process for '{service_name}': {e}"
                )
                return False

        return False

    def _is_tunnel_running(self, tunnel_id: str, hostname: str) -> bool:
        """Check if a tunnel is currently running."""
        for service_name, process in self._running_processes.items():
            if process and process.poll() is None:
                service_info = self.registry.get_service(service_name)
                if service_info and service_info.tunnel_id == tunnel_id:
                    logger.debug(f"Tunnel {tunnel_id} is running (PID: {process.pid})")
                    return True

        try:
            result = subprocess.run(
                ["pgrep", "-f", f"cloudflared.*{tunnel_id}"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0 and result.stdout.strip():
                logger.debug(f"Found cloudflared process for tunnel {tunnel_id}")
                return True
        except Exception as e:
            logger.debug(f"Error checking for cloudflared process: {e}")

        logger.debug(f"Tunnel {tunnel_id} is NOT running")
        return False

    def stop_tunnel(self, service_name: str) -> bool:
        """Stop the tunnel for a service."""
        logger.info(f"Stopping tunnel for service '{service_name}'")

        success = self._stop_tunnel_process(service_name)

        self.registry.update_service(
            service_name,
            tunnel_id=None,
            tunnel_hostname=None,
            config_path=None,
            pid=None,
        )

        return success

    def get_service_url(self, service_name: str) -> str | None:
        """Get the public URL for a service."""
        service_info = self.registry.get_service(service_name)
        if service_info and service_info.tunnel_hostname:
            return f"https://{service_info.tunnel_hostname}"
        return None

    def get_tunnel_status(self, service_name: str) -> dict:
        """Get detailed tunnel status for a service."""
        service_info = self.registry.get_service(service_name)
        if not service_info:
            return {
                "status": "not_found",
                "message": f"Service '{service_name}' not found",
            }

        status = {
            "service_name": service_name,
            "port": service_info.assigned_port,
            "tunnel_id": service_info.tunnel_id,
            "hostname": service_info.tunnel_hostname,
            "url": (
                f"https://{service_info.tunnel_hostname}"
                if service_info.tunnel_hostname
                else None
            ),
            "process_running": service_name in self._running_processes,
            "last_seen": service_info.last_seen,
        }

        if service_info.tunnel_id and service_info.tunnel_hostname:
            status["tunnel_running"] = self._is_tunnel_running(
                service_info.tunnel_id,
                service_info.tunnel_hostname,
            )

            if status["tunnel_running"]:
                status["tunnel_healthy"] = check_tunnel_health(
                    service_info.tunnel_hostname,
                    service_info.assigned_port,
                )

            if status["tunnel_running"]:
                status["tunnel_healthy"] = check_tunnel_health(
                    service_info.tunnel_hostname,
                    service_info.assigned_port,
                )

        return status

    def cleanup_all(self):
        """Clean up all running tunnel processes."""
        logger.info("Cleaning up all tunnel processes")

        for service_name in list(self._running_processes.keys()):
            self._stop_tunnel_process(service_name)

        self._running_processes.clear()
