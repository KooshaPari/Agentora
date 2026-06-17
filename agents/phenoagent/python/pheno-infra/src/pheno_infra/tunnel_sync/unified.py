"""
Unified tunnel management: add services and generate unified config.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .models import TunnelInfo

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


class UnifiedMixin:
    def _generate_unified_config(self) -> Path:
        config_path = self.cloudflared_dir / f"config-{self.domain.split('.')[0]}.yml"
        creds_file = self.cloudflared_dir / f"{self._unified_tunnel_id}.json"
        ingress_rules: list[dict] = []
        sorted_services = sorted(
            self._service_routes.items(),
            key=lambda x: (0 if x[1][1] != "/" else 1, len(x[1][1])),
            reverse=True,
        )
        for _service_name, (port, path) in sorted_services:
            if path != "/":
                ingress_rules.append(
                    {
                        "hostname": self.domain,
                        "path": f"{path}/*",
                        "service": f"http://127.0.0.1:{port}",
                    },
                )
        for (port, path) in self._service_routes.values():
            if path == "/":
                ingress_rules.append(
                    {"hostname": self.domain, "service": f"http://127.0.0.1:{port}"},
                )
        ingress_rules.append({"service": "http_status:404"})
        config_content = f"""tunnel: {self._unified_tunnel_id}
credentials-file: {creds_file}

ingress:
"""
        for rule in ingress_rules:
            config_content += "  - "
            if "hostname" in rule:
                config_content += f"hostname: {rule['hostname']}\n"
                if "path" in rule:
                    config_content += f"    path: {rule['path']}\n"
                config_content += f"    service: {rule['service']}\n"
            else:
                config_content += f"service: {rule['service']}\n"
        with open(config_path, "w") as f:
            f.write(config_content)
        self._log_tunnel(
            "Generated unified tunnel config with %d services",
            len(self._service_routes),
            verbose=True,
        )
        logger.debug("Config: %s", config_path)
        return config_path

    def _start_unified_tunnel_service(self, service_name: str, port: int, path: str) -> TunnelInfo:
        self._log_tunnel(
            "Adding service '%s' to unified tunnel: port=%s, path='%s'",
            service_name,
            port,
            path,
            verbose=True,
        )
        self._service_routes[service_name] = (port, path)
        if not self._unified_tunnel_id:
            tunnel_name = f"{self.domain.split('.')[0]}-unified"
            self._log_tunnel("Initializing unified tunnel: %s", tunnel_name, verbose=True)
            self._unified_tunnel_id = self._find_existing_tunnel(tunnel_name)
            if self._unified_tunnel_id:
                self._log_tunnel(
                    "Found existing tunnel '%s' with ID: %s",
                    tunnel_name,
                    self._unified_tunnel_id,
                    verbose=True,
                )
            else:
                self._log_tunnel("Creating new tunnel '%s'", tunnel_name, verbose=True)
                self._unified_tunnel_id = self._create_cloudflare_tunnel(tunnel_name)
                self._log_tunnel(
                    "Created tunnel '%s' with ID: %s",
                    tunnel_name,
                    self._unified_tunnel_id,
                    verbose=True,
                )
            self._log_tunnel("Setting up DNS for domain: %s", self.domain, verbose=True)
            self._setup_dns_route(self._unified_tunnel_id, self.domain)
            self._log_tunnel(
                "DNS configured: %s -> tunnel %s",
                self.domain,
                self._unified_tunnel_id,
                verbose=True,
            )
        self._log_tunnel(
            "Generating unified config with %d service(s)", len(self._service_routes), verbose=True,
        )
        self._unified_config_path = self._generate_unified_config()
        if "unified" in self._running_processes:
            self._log_tunnel(
                "Restarting unified tunnel process with updated configuration", verbose=True,
            )
            self._stop_tunnel_process("unified")
        else:
            self._log_tunnel("Starting unified tunnel process", verbose=True)
        self._start_tunnel_process("unified", self._unified_config_path)
        self.registry.update_service(
            service_name,
            tunnel_id=self._unified_tunnel_id,
            tunnel_hostname=self.domain,
            config_path=str(self._unified_config_path),
        )
        self._log_tunnel(
            "Service '%s' added to unified tunnel successfully", service_name, verbose=True,
        )
        self._log_tunnel("Service URL: https://%s%s", self.domain, path, verbose=True)
        return TunnelInfo(
            tunnel_id=self._unified_tunnel_id,
            hostname=self.domain,
            config_path=str(self._unified_config_path),
            port=port,
            status="running",
        )

    def _unregister_unified_service(self, service_name: str) -> None:
        if service_name in self._service_routes:
            self._log_tunnel(
                "Removing service '%s' from unified tunnel", service_name, verbose=True,
            )
            self._service_routes.pop(service_name, None)
        if not self._service_routes:
            self._log_tunnel(
                "No services remain in unified tunnel; stopping tunnel process", verbose=True,
            )
            self._stop_tunnel_process("unified")
