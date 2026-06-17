"""
Tunnel sync handlers - DNS setup, config generation, cleanup operations.
"""

import json
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path

logger = logging.getLogger(__name__)

CLOUDFLARE_API_TOKEN_FALLBACK = "F5lBjouWaymoiTgptvaWrJp-mDMLPXvHybDik_Bk"

HAS_CF_SDK = False
Cloudflare = None
try:
    from cloudflare import Cloudflare

    HAS_CF_SDK = True
    Cloudflare = Cloudflare
except ImportError:
    pass


def load_cloudflare_token(
    domain: str,
    explicit_token: str | None = None,
    cloudflared_dir: Path | None = None,
) -> str | None:
    """Load Cloudflare API token from multiple sources."""
    if explicit_token:
        logger.debug("Using explicitly provided Cloudflare token")
        return explicit_token

    env_token = os.getenv("CLOUDFLARE_API_TOKEN")
    if env_token:
        logger.debug("Using CLOUDFLARE_API_TOKEN from environment")
        return env_token

    kinfra_token_file = Path.home() / ".kinfra" / "cloudflare_token"
    if kinfra_token_file.exists():
        try:
            token = kinfra_token_file.read_text().strip()
            if token:
                logger.debug(f"Using Cloudflare token from {kinfra_token_file}")
                return token
        except Exception as e:
            logger.debug(f"Failed to read token from {kinfra_token_file}: {e}")

    cf_dir = cloudflared_dir or (Path.home() / ".cloudflared")
    cf_token_file = cf_dir / "cloudflare_token"
    if cf_token_file.exists():
        try:
            token = cf_token_file.read_text().strip()
            if token:
                logger.debug(f"Using Cloudflare token from {cf_token_file}")
                return token
        except Exception as e:
            logger.debug(f"Failed to read token from {cf_token_file}: {e}")

    if "kooshapari.com" in domain and CLOUDFLARE_API_TOKEN_FALLBACK:
        logger.debug("Using hardcoded fallback Cloudflare token")
        return CLOUDFLARE_API_TOKEN_FALLBACK

    logger.debug("No Cloudflare API token found")
    return None


def verify_cloudflared_setup(cloudflared_dir: Path) -> None:
    """Verify cloudflared is available and authenticated."""
    if not shutil.which("cloudflared"):
        from ..exceptions import ConfigurationError

        raise ConfigurationError(
            "cloudflared not found. Install it with: "
            "https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/",
        )

    cert_path = cloudflared_dir / "cert.pem"
    if not cert_path.exists():
        from ..exceptions import ConfigurationError

        raise ConfigurationError(
            "cloudflared not authenticated. Run: cloudflared tunnel login"
        )


def stop_all_cloudflared_processes() -> None:
    """Stop all running cloudflared processes."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "cloudflared"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            logger.info(f"Found {len(pids)} cloudflared process(es) to stop")

            for pid in pids:
                try:
                    logger.debug(f"Stopping cloudflared process PID: {pid}")
                    subprocess.run(["kill", pid], timeout=2)
                except Exception as e:
                    logger.debug(f"Could not stop process {pid}: {e}")

            time.sleep(2)

            result = subprocess.run(
                ["pgrep", "-f", "cloudflared"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                remaining_pids = result.stdout.strip().split("\n")
                logger.warning(
                    f"Force killing {len(remaining_pids)} remaining process(es)"
                )
                for pid in remaining_pids:
                    try:
                        subprocess.run(["kill", "-9", pid], timeout=2)
                    except Exception as e:
                        logger.debug(f"Could not force kill process {pid}: {e}")

            logger.info("All cloudflared processes stopped")
        else:
            logger.info("No running cloudflared processes found")

    except subprocess.TimeoutExpired:
        logger.warning("Timeout while stopping cloudflared processes")
    except Exception as e:
        logger.warning(f"Error stopping cloudflared processes: {e}")


def list_all_tunnels() -> list[dict]:
    """List all existing Cloudflare tunnels."""
    try:
        result = subprocess.run(
            ["cloudflared", "tunnel", "list", "--output", "json"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            tunnels = json.loads(result.stdout)
            return tunnels if isinstance(tunnels, list) else []
    except (
        subprocess.TimeoutExpired,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ) as e:
        logger.warning(f"Failed to list tunnels: {e}")

    return []


def cleanup_dns_records(domain: str, cf_client, cf_zone_id: str | None) -> None:
    """Delete all DNS records for the domain."""
    if cf_client and cf_zone_id:
        try:
            _cleanup_dns_via_api(domain, cf_client, cf_zone_id)
            return
        except Exception as e:
            logger.warning(f"API DNS cleanup failed: {e}")

    logger.info("Cannot cleanup DNS records without Cloudflare API access")
    logger.info(
        "You may need to manually remove old DNS records from Cloudflare dashboard"
    )


def _cleanup_dns_via_api(domain: str, cf_client, cf_zone_id: str) -> None:
    """Delete DNS records using Cloudflare API."""
    deleted_count = 0
    record_types = ["A", "AAAA", "CNAME"]

    for record_type in record_types:
        try:
            records = cf_client.dns.records.list(
                zone_id=cf_zone_id,
                name=domain,
                type=record_type,
            )

            for record in records.result:
                if record.name == domain:
                    logger.info(
                        f"Deleting {record_type} record: {domain} -> {record.content}"
                    )
                    cf_client.dns.records.delete(
                        dns_record_id=record.id, zone_id=cf_zone_id
                    )
                    deleted_count += 1
                    time.sleep(0.5)
        except Exception as e:
            logger.debug(f"Error cleaning up {record_type} records: {e}")

    if deleted_count > 0:
        logger.info(f"Deleted {deleted_count} DNS record(s) for {domain}")
    else:
        logger.info(f"No existing DNS records found for {domain}")


def cleanup_old_configs(domain: str, cloudflared_dir: Path) -> None:
    """Remove old config files for this domain."""
    domain_prefix = domain.split(".")[0]
    pattern = f"config-{domain_prefix}*.yml"

    deleted_count = 0
    for config_file in cloudflared_dir.glob(pattern):
        try:
            logger.debug(f"Removing old config: {config_file}")
            config_file.unlink()
            deleted_count += 1
        except Exception as e:
            logger.debug(f"Could not remove {config_file}: {e}")

    if deleted_count > 0:
        logger.info(f"Removed {deleted_count} old config file(s)")
    else:
        logger.debug("No old config files to remove")


def get_zone_id(domain: str, cf_client) -> str | None:
    """Get Cloudflare zone ID for the domain."""
    if not cf_client:
        return None

    try:
        parts = domain.split(".")
        root_domain = ".".join(parts[-2:]) if len(parts) > 2 else domain

        logger.debug(f"Looking up zone for root domain: {root_domain}")
        zones = cf_client.zones.list(name=root_domain)

        if zones and len(zones.result) > 0:
            zone_id = zones.result[0].id
            logger.debug(f"Found zone ID for {root_domain}: {zone_id}")

            _configure_ssl_for_tunnels(zone_id, cf_client)

            return zone_id
    except Exception as e:
        logger.warning(f"Failed to get zone ID: {e}")

    return None


def _configure_ssl_for_tunnels(zone_id: str, cf_client) -> None:
    """Configure SSL/TLS settings for optimal tunnel compatibility."""
    if not cf_client:
        return

    try:
        current_ssl = cf_client.zones.settings.get(zone_id=zone_id, setting_id="ssl")

        if current_ssl.value != "full":
            logger.info(
                f"Updating SSL mode from '{current_ssl.value}' to 'full' for tunnel compatibility",
            )
            cf_client.zones.settings.edit(
                zone_id=zone_id, setting_id="ssl", value="full"
            )
            logger.info("SSL mode set to 'full'")

        try:
            cf_client.zones.settings.edit(
                zone_id=zone_id, setting_id="tls_1_3", value="on"
            )
            logger.debug("TLS 1.3 enabled")
        except Exception:
            pass

        try:
            cf_client.zones.settings.edit(
                zone_id=zone_id,
                setting_id="min_tls_version",
                value="1.2",
            )
            logger.debug("Minimum TLS version set to 1.2")
        except Exception:
            pass

    except Exception as e:
        logger.warning(f"Could not configure SSL settings: {e}")
        logger.info(
            "You may need to manually set SSL/TLS mode to 'Full' in Cloudflare dashboard"
        )


def setup_dns_route(
    tunnel_id: str,
    hostname: str,
    cf_client,
    cf_zone_id: str | None,
    cloudflared_dir: Path,
) -> None:
    """Set up DNS routing for the tunnel."""
    logger.info(f"Setting up DNS route: {hostname} -> tunnel {tunnel_id}")

    if cf_client and cf_zone_id:
        try:
            setup_dns_via_api(tunnel_id, hostname, cf_client, cf_zone_id)
            return
        except Exception as e:
            logger.warning(f"API DNS setup failed: {e}, falling back to CLI")

    setup_dns_via_cli(tunnel_id, hostname)


def setup_dns_via_api(
    tunnel_id: str, hostname: str, cf_client, cf_zone_id: str
) -> None:
    """Set up DNS using Cloudflare API."""
    logger.info(f"Cleaning up existing DNS records for: {hostname}")
    deleted_count = 0
    record_types = ["A", "AAAA", "CNAME"]

    for record_type in record_types:
        try:
            records = cf_client.dns.records.list(
                zone_id=cf_zone_id,
                name=hostname,
                type=record_type,
            )

            for record in records.result:
                if record.name == hostname:
                    logger.info(
                        f"Deleting existing {record_type} record: {hostname} -> {record.content}",
                    )
                    cf_client.dns.records.delete(
                        dns_record_id=record.id, zone_id=cf_zone_id
                    )
                    deleted_count += 1
                    time.sleep(0.5)
        except Exception as e:
            logger.debug(f"Error cleaning up {record_type} records: {e}")

    if deleted_count > 0:
        logger.info(f"Deleted {deleted_count} existing DNS record(s)")
        time.sleep(2)

    cname_target = f"{tunnel_id}.cfargotunnel.com"
    logger.info(f"Creating CNAME record: {hostname} -> {cname_target}")

    try:
        record = cf_client.dns.records.create(
            zone_id=cf_zone_id,
            name=hostname,
            type="CNAME",
            content=cname_target,
            proxied=True,
            ttl=1,
        )
        logger.info(f"DNS record created successfully: {hostname} -> {cname_target}")
        logger.info(f"  Record ID: {record.id}, Proxied: {record.proxied}")

        time.sleep(1)
        verify_records = cf_client.dns.records.list(
            zone_id=cf_zone_id,
            name=hostname,
            type="CNAME",
        )

        verified = False
        for verify_record in verify_records.result:
            if verify_record.name == hostname and verify_record.content == cname_target:
                verified = True
                logger.info("DNS record verified in Cloudflare")
                break

        if not verified:
            logger.warning("DNS record created but verification failed")

    except Exception as e:
        error_msg = str(e)
        if "already exists" in error_msg.lower() or "duplicate" in error_msg.lower():
            logger.warning(f"DNS record already exists: {hostname}")
        else:
            from ..exceptions import TunnelError

            raise TunnelError(f"Failed to create DNS record: {e}")


def setup_dns_via_cli(tunnel_id: str, hostname: str) -> None:
    """Set up DNS using cloudflared CLI (fallback method)."""
    try:
        result = subprocess.run(
            ["cloudflared", "tunnel", "route", "dns", tunnel_id, hostname],
            capture_output=True,
            text=True,
            timeout=15,
        )

        if result.returncode != 0:
            stderr = result.stderr.lower()
            if "already exists" not in stderr and "duplicate" not in stderr:
                logger.warning(f"DNS route setup warning: {result.stderr}")
        else:
            logger.info(f"DNS route configured via CLI: {hostname}")

    except subprocess.TimeoutExpired:
        logger.warning(f"Timeout setting up DNS route for {hostname}")


def generate_tunnel_config(
    service_slug: str,
    tunnel_id: str,
    hostname: str,
    port: int,
    cloudflared_dir: Path,
) -> Path:
    """Generate cloudflared configuration file."""
    config_path = cloudflared_dir / f"config-{service_slug}.yml"
    creds_file = cloudflared_dir / f"{tunnel_id}.json"

    config_content = f"""tunnel: {tunnel_id}
credentials-file: {creds_file}

ingress:
  - hostname: {hostname}
    service: http://127.0.0.1:{port}
  - service: http_status:404
"""

    with open(config_path, "w") as f:
        f.write(config_content)

    logger.debug(f"Generated tunnel config: {config_path}")
    return config_path


def generate_unified_config(
    domain: str,
    tunnel_id: str,
    service_routes: dict[str, tuple[int, str]],
    cloudflared_dir: Path,
) -> Path:
    """Generate unified tunnel config with all services using path-based routing."""
    config_path = cloudflared_dir / f"config-{domain.split('.')[0]}.yml"
    creds_file = cloudflared_dir / f"{tunnel_id}.json"

    ingress_rules = []

    sorted_services = sorted(
        service_routes.items(),
        key=lambda x: (0 if x[1][1] != "/" else 1, len(x[1][1])),
        reverse=True,
    )

    for _service_name, (port, path) in sorted_services:
        if path != "/":
            ingress_rules.append(
                {
                    "hostname": domain,
                    "path": f"{path}/*",
                    "service": f"http://127.0.0.1:{port}",
                },
            )

    for port, path in service_routes.values():
        if path == "/":
            ingress_rules.append(
                {"hostname": domain, "service": f"http://127.0.0.1:{port}"}
            )

    ingress_rules.append({"service": "http_status:404"})

    config_content = f"""tunnel: {tunnel_id}
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

    logger.info(f"Generated unified tunnel config with {len(service_routes)} services")
    logger.debug(f"Config: {config_path}")

    return config_path
