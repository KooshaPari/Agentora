"""
Separate tunnel lifecycle: per-service tunnels and config generation.
"""

from __future__ import annotations

import json
import logging
import subprocess
from typing import TYPE_CHECKING

from ..exceptions import TunnelError
from ..utils.dns import dns_safe_slug
from .models import TunnelInfo

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


class SeparateMixin:
    def _start_separate_tunnel(self, service_name: str, port: int) -> TunnelInfo:
        service_slug = dns_safe_slug(service_name)
        hostname = f"{service_slug}.{self.domain}"
        service_info = self.registry.get_service(service_name)
        if service_info and service_info.tunnel_id:
            if service_info.assigned_port != port:
                self._log_tunnel(
                    "Port changed for '%s': %s -> %s",
                    service_name,
                    service_info.assigned_port,
                    port,
                    verbose=True,
                )
                return self._update_tunnel_port(
                    service_name, service_info.tunnel_id, hostname, port,
                )
            if self._is_tunnel_running(service_info.tunnel_id, hostname):
                self._log_tunnel("Tunnel for '%s' already running", service_name, verbose=True)
                return TunnelInfo(
                    tunnel_id=service_info.tunnel_id,
                    hostname=hostname,
                    config_path=service_info.config_path or "",
                    port=port,
                    status="running",
                )
        return self._create_tunnel(service_name, service_slug, hostname, port)

    def _create_tunnel(
        self, service_name: str, service_slug: str, hostname: str, port: int,
    ) -> TunnelInfo:
        self._log_tunnel("Creating new tunnel: %s -> localhost:%s", hostname, port, verbose=True)
        tunnel_name = f"{service_slug}-tunnel"
        tunnel_id = self._find_existing_tunnel(tunnel_name)
        if not tunnel_id:
            tunnel_id = self._create_cloudflare_tunnel(tunnel_name)
        self._setup_dns_route(tunnel_id, hostname)
        config_path = self._generate_tunnel_config(service_slug, tunnel_id, hostname, port)
        self._start_tunnel_process(service_name, config_path)
        self.registry.update_service(
            service_name,
            tunnel_id=tunnel_id,
            tunnel_hostname=hostname,
            config_path=str(config_path),
        )
        self._log_tunnel("Tunnel created: %s", hostname, verbose=True)
        return TunnelInfo(
            tunnel_id=tunnel_id,
            hostname=hostname,
            config_path=str(config_path),
            port=port,
            status="starting",
        )

    def _update_tunnel_port(
        self, service_name: str, tunnel_id: str, hostname: str, new_port: int,
    ) -> TunnelInfo:
        self._log_tunnel(
            "Updating tunnel port for '%s': %s -> localhost:%s",
            service_name,
            hostname,
            new_port,
            verbose=True,
        )
        self._stop_tunnel_process(service_name)
        service_slug = hostname.split(".", maxsplit=1)[0]
        config_path = self._generate_tunnel_config(service_slug, tunnel_id, hostname, new_port)
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
        try:
            result = subprocess.run(
                ["cloudflared", "tunnel", "list", "--output", "json"],
                check=False, capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                tunnels = json.loads(result.stdout)
                for tunnel in tunnels:
                    if tunnel.get("name") == tunnel_name:
                        return tunnel.get("id")
        except (subprocess.TimeoutExpired, json.JSONDecodeError, subprocess.SubprocessError) as e:
            logger.warning("Failed to list tunnels: %s", e)
        return None

    def _create_cloudflare_tunnel(self, tunnel_name: str) -> str:
        self._log_tunnel("Creating cloudflare tunnel: %s", tunnel_name, verbose=True)
        try:
            result = subprocess.run(
                ["cloudflared", "tunnel", "create", tunnel_name],
                check=False, capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                raise TunnelError(f"Failed to create tunnel '{tunnel_name}': {result.stderr}")
            tunnel_id = self._find_existing_tunnel(tunnel_name)
            if not tunnel_id:
                raise TunnelError(f"Tunnel '{tunnel_name}' created but ID not found")
            self._log_tunnel(
                "Created tunnel '%s' with ID: %s", tunnel_name, tunnel_id, verbose=True,
            )
            return tunnel_id
        except subprocess.TimeoutExpired:
            raise TunnelError(f"Timeout creating tunnel '{tunnel_name}'")

    def _generate_tunnel_config(
        self, service_slug: str, tunnel_id: str, hostname: str, port: int,
    ) -> Path:
        config_path = self.cloudflared_dir / f"config-{service_slug}.yml"
        creds_file = self.cloudflared_dir / f"{tunnel_id}.json"
        content = f"""tunnel: {tunnel_id}
credentials-file: {creds_file}

ingress:
  - hostname: {hostname}
    service: http://127.0.0.1:{port}
  - service: http_status:404
"""
        with open(config_path, "w") as f:
            f.write(content)
        logger.debug("Generated tunnel config: %s", config_path)
        return config_path
