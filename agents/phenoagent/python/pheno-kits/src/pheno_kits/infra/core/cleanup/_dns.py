"""DNS and tunnel cleanup logic."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Sequence

from pheno.kits.infra.core.cleanup._constants import HAS_CLOUDFLARE
from pheno.kits.infra.core.cleanup._models import CleanupConfig

logger = logging.getLogger(__name__)


class DnsCleanup:
    """Handles DNS record and tunnel cleanup via CLI and Cloudflare API."""

    def __init__(self, config: Any) -> None:
        self.config = config

    def cleanup_dns(self, domains: Sequence[str]) -> dict[str, Any]:
        """Attempt to remove lingering DNS records and config files."""
        summary: dict[str, Any] = {
            "domains": list(domains),
            "records_removed": 0,
            "config_files_removed": 0,
            "tunnels_deleted": 0,
            "errors": 0,
            "details": [],
        }

        for domain in domains:
            detail, stats = self._cleanup_dns_for_domain(domain)
            summary["details"].append(detail)
            summary["records_removed"] += stats.get("records_removed", 0)
            summary["config_files_removed"] += stats.get("config_files_removed", 0)
            summary["tunnels_deleted"] += stats.get("tunnels_deleted", 0)
            summary["errors"] += stats.get("errors", 0)

        return summary

    def _cleanup_dns_for_domain(
        self,
        domain: str,
    ) -> tuple[dict[str, Any], dict[str, int]]:
        detail: dict[str, Any] = {"domain": domain, "actions": []}
        stats: dict[str, int] = {
            "records_removed": 0,
            "config_files_removed": 0,
            "tunnels_deleted": 0,
            "errors": 0,
        }

        domain = domain.lower().strip()
        prefix = domain.split(".")[0]

        cloudflared_dir = Path.home() / ".cloudflared"
        if cloudflared_dir.exists():
            for pattern in (
                f"config-{prefix}*.yml",
                f"{prefix}-unified.json",
                f"{prefix}-unified.yml",
            ):
                for file_path in cloudflared_dir.glob(pattern):
                    try:
                        file_path.unlink()
                        stats["config_files_removed"] += 1
                        detail["actions"].append(f"Removed {file_path.name}")
                    except Exception as exc:
                        stats["errors"] += 1
                        logger.debug("Failed to remove %s: %s", file_path, exc)

        tunnels_deleted = self._cleanup_tunnels_cli(prefix, domain, detail, stats)
        if tunnels_deleted:
            stats["tunnels_deleted"] = tunnels_deleted

        self._cleanup_cloudflare_api(domain, detail, stats)

        return detail, stats

    def _cleanup_tunnels_cli(
        self,
        prefix: str,
        domain: str,
        detail: dict[str, Any],
        stats: dict[str, int],
    ) -> int:
        tunnels_deleted = 0
        try:
            result = subprocess.run(
                ["cloudflared", "tunnel", "list", "--output", "json"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                tunnels = json.loads(result.stdout)
                for tunnel in tunnels if isinstance(tunnels, list) else []:
                    name = str(tunnel.get("name", ""))
                    if prefix in name or domain in name:
                        delete_result = subprocess.run(
                            ["cloudflared", "tunnel", "delete", name],
                            input="y\n",
                            capture_output=True,
                            text=True,
                            timeout=30,
                            check=False,
                        )
                        if delete_result.returncode == 0:
                            tunnels_deleted += 1
                            detail["actions"].append(f"Deleted tunnel {name}")
                        else:
                            stats["errors"] += 1
                            logger.debug(
                                "Failed to delete tunnel %s: %s",
                                name,
                                delete_result.stderr.strip(),
                            )
        except FileNotFoundError:
            logger.info(
                "cloudflared CLI not available - skipping tunnel deletion for %s",
                domain,
            )
        except subprocess.TimeoutExpired:
            stats["errors"] += 1
            logger.warning("Timeout while inspecting tunnels for %s", domain)
        except json.JSONDecodeError as exc:
            stats["errors"] += 1
            logger.debug("Could not parse cloudflared tunnel list: %s", exc)
        return tunnels_deleted

    def _cleanup_cloudflare_api(
        self,
        domain: str,
        detail: dict[str, Any],
        stats: dict[str, int],
    ) -> None:
        if not HAS_CLOUDFLARE:
            return

        token = os.getenv("CLOUDFLARE_API_TOKEN")
        if not token:
            return

        try:
            from cloudflare import Cloudflare

            client = Cloudflare(api_token=token)
            zone_id = self._lookup_zone_id(client, domain)
            if zone_id:
                records = client.dns.records.list(zone_id=zone_id, name=domain)
                for record in records.result:
                    client.dns.records.delete(dns_record_id=record.id, zone_id=zone_id)
                    stats["records_removed"] += 1
                    detail["actions"].append(
                        f"Deleted {record.type} record -> {record.content}",
                    )
                    time.sleep(0.5)
        except Exception as exc:  # pragma: no cover - defensive coding
            stats["errors"] += 1
            logger.debug("Cloudflare DNS cleanup failed for %s: %s", domain, exc)

    def _lookup_zone_id(self, client: Any, domain: str) -> str | None:
        try:
            parts = domain.split(".")
            root_domain = ".".join(parts[-2:]) if len(parts) > 2 else domain
            response = client.zones.list(name=root_domain)
            if response and getattr(response, "result", None):
                return response.result[0].id
        except Exception as exc:
            logger.debug("Unable to resolve Cloudflare zone for %s: %s", domain, exc)
        return None
