"""
DNS setup helpers (API or CLI) for tunnels.
"""

from __future__ import annotations

import logging
import subprocess
import time

from ..exceptions import TunnelError

logger = logging.getLogger(__name__)


class DNSMixin:
    def _setup_dns_route(self, tunnel_id: str, hostname: str) -> None:
        self._log_tunnel("Setting up DNS route: %s -> tunnel %s", hostname, tunnel_id, verbose=True)
        if getattr(self, "cf_client", None) and getattr(self, "cf_zone_id", None):
            try:
                self._setup_dns_via_api(tunnel_id, hostname)
                return
            except Exception as e:
                logger.warning("API DNS setup failed: %s, falling back to CLI", e)
        self._setup_dns_via_cli(tunnel_id, hostname)

    def _setup_dns_via_api(self, tunnel_id: str, hostname: str) -> None:
        if not getattr(self, "cf_client", None) or not getattr(self, "cf_zone_id", None):
            raise TunnelError("Cloudflare API client not initialized")
        deleted_count = 0
        for record_type in ["A", "AAAA", "CNAME"]:
            try:
                records = self.cf_client.dns.records.list(
                    zone_id=self.cf_zone_id, name=hostname, type=record_type,
                )
                for record in records.result:
                    if record.name == hostname:
                        self._log_tunnel(
                            "Deleting existing %s record: %s -> %s",
                            record_type,
                            hostname,
                            record.content,
                            verbose=True,
                        )
                        self.cf_client.dns.records.delete(
                            dns_record_id=record.id, zone_id=self.cf_zone_id,
                        )
                        deleted_count += 1
                        time.sleep(0.5)
            except Exception as e:
                logger.debug("Error cleaning up %s records: %s", record_type, e)
        if deleted_count > 0:
            self._log_tunnel("Deleted %d existing DNS record(s)", deleted_count, verbose=True)
            time.sleep(2)
        cname_target = f"{tunnel_id}.cfargotunnel.com"
        self._log_tunnel("Creating CNAME record: %s -> %s", hostname, cname_target, verbose=True)
        try:
            record = self.cf_client.dns.records.create(  # type: ignore[attr-defined]
                zone_id=self.cf_zone_id,  # type: ignore[attr-defined]
                name=hostname,
                type="CNAME",
                content=cname_target,
                proxied=True,
                ttl=1,
            )
            self._log_tunnel(
                "\u2713 DNS record created successfully: %s -> %s",
                hostname,
                cname_target,
                verbose=True,
            )
            time.sleep(1)
            verify_records = self.cf_client.dns.records.list(zone_id=self.cf_zone_id, name=hostname, type="CNAME")  # type: ignore[attr-defined]
            verified = any(
                vr.name == hostname and vr.content == cname_target for vr in verify_records.result
            )
            if not verified:
                logger.warning("DNS record created but verification failed")
        except Exception as e:
            msg = str(e)
            if "already exists" in msg.lower() or "duplicate" in msg.lower():
                logger.warning("DNS record already exists: %s", hostname)
            else:
                raise TunnelError(f"Failed to create DNS record: {e}")

    def _setup_dns_via_cli(self, tunnel_id: str, hostname: str) -> None:
        try:
            result = subprocess.run(
                ["cloudflared", "tunnel", "route", "dns", tunnel_id, hostname],
                check=False, capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode != 0:
                stderr = (result.stderr or "").lower()
                if "already exists" in stderr or "duplicate" in stderr:
                    # Attempt API replacement if available (handles overwrite automatically)
                    if getattr(self, "cf_client", None) and getattr(self, "cf_zone_id", None):
                        try:
                            self._log_tunnel(
                                "CLI reported existing record; attempting API replacement for %s",
                                hostname,
                                verbose=True,
                            )
                            self._setup_dns_via_api(tunnel_id, hostname)
                            self._log_tunnel(
                                "\u2713 DNS record replaced via API: %s", hostname, verbose=True,
                            )
                            return
                        except Exception as api_exc:
                            logger.warning("CLI duplicate; API replacement failed: %s", api_exc)
                    # Otherwise, benign: record exists; keep going
                else:
                    logger.warning("DNS route setup warning: %s", result.stderr)
            else:
                self._log_tunnel("\u2713 DNS route configured via CLI: %s", hostname, verbose=True)
        except subprocess.TimeoutExpired:
            logger.warning("Timeout setting up DNS route for %s", hostname)
