"""
Core tunnel base implementation.
"""

from __future__ import annotations

import contextlib
import json
import logging
import subprocess
import time
from typing import TYPE_CHECKING

from ...port_registry import PortRegistry
from .config import TunnelConfig, resolve_cloudflare_token, verify_cloudflared_setup

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

try:  # Optional Cloudflare SDK
    from cloudflare import Cloudflare

    HAS_CF_SDK = True
except Exception:  # pragma: no cover - optional dependency
    Cloudflare = None  # type: ignore
    HAS_CF_SDK = False


class TunnelBase:
    """
    Base tunnel orchestration shared by mixins.
    """

    _cleanup_done: bool = False
    _cleanup_domains: set[str] = set()

    def __init__(
        self,
        registry: PortRegistry | None = None,
        domain: str = "kooshapari.com",
        cf_api_token: str | None = None,
        use_unified_tunnel: bool = True,
        cleanup_on_start: bool = True,
    ) -> None:
        self.registry = registry or PortRegistry()
        self.config = TunnelConfig(
            domain=domain.lower(),
            use_unified_tunnel=use_unified_tunnel,
            cleanup_on_start=cleanup_on_start,
        )
        self.config.ensure_dirs()
        self._tunnel_verbose = self.config.determine_verbose()
        self.tunnel_startup_timeout = self.config.tunnel_startup_timeout
        self.health_check_interval = self.config.health_check_interval
        self._running_processes: dict[str, subprocess.Popen] = {}
        self._unified_tunnel_id: str | None = None
        self._unified_config_path: Path | None = None
        self._service_routes: dict[str, tuple[int, str]] = {}

        self.cf_client = None
        self.cf_zone_id = None
        if HAS_CF_SDK:
            api_token = resolve_cloudflare_token(self.config, cf_api_token)
            if api_token:
                try:
                    self.cf_client = Cloudflare(api_token=api_token)
                    self.cf_zone_id = self._get_zone_id()
                    self._log_tunnel(
                        "Cloudflare API initialized for domain %s", self.config.domain, verbose=True,
                    )
                except Exception as exc:
                    logger.warning("Failed to initialize Cloudflare API: %s", exc)
                    self._log_tunnel(
                        "Falling back to cloudflared CLI for DNS management", verbose=True,
                    )
            else:
                self._log_tunnel(
                    "No CLOUDFLARE_API_TOKEN found, using cloudflared CLI for DNS", verbose=True,
                )

        verify_cloudflared_setup(self.config)
        if (
            cleanup_on_start
            and use_unified_tunnel
            and self.config.domain not in TunnelBase._cleanup_domains
        ):
            self._log_tunnel(
                "Performing automatic cleanup for unified tunnel setup...", verbose=True,
            )
            self.cleanup_all_unified_tunnels()
            TunnelBase._cleanup_done = True
            TunnelBase._cleanup_domains.add(self.config.domain)

    # ------------------------------------------------------------------
    # Logging & helpers
    # ------------------------------------------------------------------
    def _log_tunnel(
        self, message: str, *args, level: int = logging.INFO, verbose: bool = False,
    ) -> None:
        if verbose and not self._tunnel_verbose:
            logger.debug(message, *args)
            return
        logger.log(level, message, *args)

    # ------------------------------------------------------------------
    # Cleanup helpers
    # ------------------------------------------------------------------
    def cleanup_all_unified_tunnels(self) -> None:
        """
        Clean up all unified tunnels and related resources.
        """
        self._log_tunnel(
            "Starting cleanup for unified tunnel on domain: %s", self.config.domain, verbose=True,
        )

        self._stop_cloudflared_processes()
        self._delete_existing_tunnels()
        self._cleanup_dns_and_configs()

        self._log_tunnel("Cleanup complete. Ready for unified tunnel setup.", verbose=True)

    def _stop_cloudflared_processes(self) -> None:
        """
        Stop all running cloudflared processes.
        """
        self._stop_all_cloudflared_processes()

    def _delete_existing_tunnels(self) -> int:
        """
        Delete existing unified tunnels and return count of deleted tunnels.
        """
        existing = self._list_all_tunnels()
        target_tunnel = f"{self.config.domain.split('.')[0]}-unified"
        deleted_tunnels = 0

        for tunnel in existing:
            name = tunnel.get("name")
            tunnel_id = tunnel.get("id")
            self._log_tunnel("  - %s (ID: %s)", name, tunnel_id, verbose=True)

            if name == target_tunnel:
                if self._delete_cloudflared_tunnel(name, tunnel_id):
                    deleted_tunnels += 1

        if deleted_tunnels:
            self._log_tunnel(
                "Deleted %d existing unified tunnel(s) named '%s'",
                deleted_tunnels,
                target_tunnel,
                verbose=True,
            )

        return deleted_tunnels

    def _cleanup_dns_and_configs(self) -> None:
        """
        Clean up DNS records and old configuration files.
        """
        self._log_tunnel("Cleaning up DNS records for domain: %s", self.config.domain, verbose=True)
        self._cleanup_dns_records()

        self._log_tunnel("Cleaning up old config files...", verbose=True)
        self._cleanup_old_configs()

    def _delete_cloudflared_tunnel(
        self, tunnel_name: str | None, tunnel_id: str | None,
    ) -> bool:
        if not tunnel_name:
            return False
        self._log_tunnel("Deleting existing tunnel '%s'", tunnel_name, verbose=True)
        try:
            result = subprocess.run(
                ["cloudflared", "tunnel", "delete", tunnel_name],
                check=False, input="y\n",
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                logger.warning(
                    "Failed to delete tunnel '%s': %s", tunnel_name, result.stderr.strip(),
                )
                return False
        except subprocess.TimeoutExpired:
            logger.warning("Timeout deleting tunnel '%s'", tunnel_name)
            return False
        except Exception as exc:
            logger.warning("Error deleting tunnel '%s': %s", tunnel_name, exc)
            return False

        if tunnel_id:
            creds_file = self.config.cloudflared_dir / f"{tunnel_id}.json"
            if creds_file.exists():
                try:
                    creds_file.unlink()
                    self._log_tunnel("Removed credentials file %s", creds_file, verbose=True)
                except Exception as exc:
                    logger.debug("Failed to remove credentials file %s: %s", creds_file, exc)
        return True

    def _stop_all_cloudflared_processes(self) -> None:
        try:
            result = subprocess.run(
                ["pgrep", "-f", "cloudflared"], check=False, capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split("\n")
                self._log_tunnel(
                    "Found %d cloudflared process(es) to stop", len(pids), verbose=True,
                )
                for pid in pids:
                    try:
                        subprocess.run(["kill", pid], check=False, timeout=2)
                    except Exception as exc:
                        logger.debug("Could not stop process %s: %s", pid, exc)
                time.sleep(2)
                result = subprocess.run(
                    ["pgrep", "-f", "cloudflared"], check=False, capture_output=True, text=True, timeout=5,
                )
                if result.returncode == 0 and result.stdout.strip():
                    remaining = result.stdout.strip().split("\n")
                    logger.warning("Force killing %d remaining process(es)", len(remaining))
                    for pid in remaining:
                        try:
                            subprocess.run(["kill", "-9", pid], check=False, timeout=2)
                        except Exception as exc:
                            logger.debug("Could not force kill process %s: %s", pid, exc)
                self._log_tunnel("All cloudflared processes stopped", verbose=True)
            else:
                self._log_tunnel("No running cloudflared processes found", verbose=True)
        except subprocess.TimeoutExpired:
            logger.warning("Timeout while stopping cloudflared processes")
        except Exception as exc:
            logger.warning("Error stopping cloudflared processes: %s", exc)

    def _list_all_tunnels(self) -> list[dict]:
        try:
            result = subprocess.run(
                ["cloudflared", "tunnel", "list", "--output", "json"],
                check=False, capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                tunnels = json.loads(result.stdout)
                return tunnels if isinstance(tunnels, list) else []
        except (subprocess.TimeoutExpired, json.JSONDecodeError, subprocess.SubprocessError) as exc:
            logger.warning("Failed to list tunnels: %s", exc)
        return []

    def _cleanup_old_configs(self) -> None:
        domain_prefix = self.config.domain.split(".")[0]
        pattern = f"config-{domain_prefix}*.yml"
        for config_file in self.config.cloudflared_dir.glob(pattern):
            try:
                config_file.unlink()
            except Exception as exc:
                logger.debug("Could not remove %s: %s", config_file, exc)

    # ------------------------------------------------------------------
    # Cloudflare API helpers
    # ------------------------------------------------------------------
    def _cleanup_dns_records(self) -> None:
        if self.cf_client and self.cf_zone_id:
            try:
                self._cleanup_dns_via_api()
                self._log_tunnel(
                    "\u2713 DNS records cleaned up for %s", self.config.domain, verbose=True,
                )
                return
            except Exception as exc:
                logger.warning("Failed to cleanup DNS records via API: %s", exc)
                self._log_tunnel(
                    "DNS records may need manual cleanup from Cloudflare dashboard", verbose=True,
                )
                return
        logger.debug("Cloudflare API not configured - skipping DNS cleanup")

    def _cleanup_dns_via_api(self) -> None:
        if not self.cf_client or not self.cf_zone_id:
            return
        for record_type in ["A", "AAAA", "CNAME"]:
            try:
                records = self.cf_client.dns.records.list(
                    zone_id=self.cf_zone_id, name=self.config.domain, type=record_type,
                )
                for record in records.result:
                    if record.name == self.config.domain:
                        self._log_tunnel(
                            "Deleting %s record: %s -> %s",
                            record_type,
                            self.config.domain,
                            record.content,
                            verbose=True,
                        )
                        self.cf_client.dns.records.delete(
                            dns_record_id=record.id, zone_id=self.cf_zone_id,
                        )
                        time.sleep(0.5)
            except Exception as exc:
                logger.debug("Error cleaning up %s records: %s", record_type, exc)

    def _get_zone_id(self) -> str | None:
        if not self.cf_client:
            return None
        try:
            parts = self.config.domain.split(".")
            root_domain = ".".join(parts[-2:]) if len(parts) > 2 else self.config.domain
            zones = self.cf_client.zones.list(name=root_domain)
            if zones and zones.result:
                zone_id = zones.result[0].id
                self._configure_ssl_for_tunnels(zone_id)
                return zone_id
        except Exception as exc:
            logger.warning("Failed to get zone ID: %s", exc)
        return None

    def _configure_ssl_for_tunnels(self, zone_id: str) -> None:
        if not self.cf_client:
            return
        try:
            current_ssl = self.cf_client.zones.settings.get(zone_id=zone_id, setting_id="ssl")
            if current_ssl.value != "full":
                self.cf_client.zones.settings.edit(zone_id=zone_id, setting_id="ssl", value="full")
            with contextlib.suppress(Exception):
                self.cf_client.zones.settings.edit(
                    zone_id=zone_id, setting_id="tls_1_3", value="on",
                )
            with contextlib.suppress(Exception):
                self.cf_client.zones.settings.edit(
                    zone_id=zone_id, setting_id="min_tls_version", value="1.2",
                )
        except Exception as exc:
            logger.warning("Could not configure SSL settings: %s", exc)


__all__ = ["TunnelBase"]
