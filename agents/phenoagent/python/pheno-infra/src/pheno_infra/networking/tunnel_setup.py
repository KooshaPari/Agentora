"""
Cloudflared named tunnel setup helpers and quick-tunnel adapter.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from pheno.infra.utils.dns import dns_safe_slug

from .options import DefaultLogger, Logger, TunnelConfig


async def ensure_named_tunnel_autocreate(
    srvc: str, domain: str, port: int, logger: Logger | None = None,
) -> tuple[str, str, str]:
    """
    Create or reuse a named tunnel, set DNS route, write config, and start cloudflared.
    """
    if logger is None:
        logger = DefaultLogger()

    srvc_clean = dns_safe_slug(srvc)
    hostname = f"{srvc_clean}.{domain.lower()}"
    logger.info(f"Auto-creating named tunnel: {hostname} -> http://localhost:{port}")

    cf_dir = Path.home() / ".cloudflared"
    cf_dir.mkdir(exist_ok=True)

    tunnel_name = f"{srvc_clean}-tunnel"
    tunnel_id: str | None = None

    # List existing tunnels
    try:
        result = subprocess.run(
            ["cloudflared", "tunnel", "list", "--output", "json"],
            capture_output=True,
            text=True,
            check=True,
        )
        tunnels = json.loads(result.stdout) if result.stdout else []
        for t in tunnels:
            if t.get("name") == tunnel_name:
                tunnel_id = t.get("id")
                logger.info(f"Found existing tunnel: {tunnel_name} ({tunnel_id})")
                break
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        logger.warn(f"Could not list existing tunnels: {e}")

    # Create if missing
    if not tunnel_id:
        logger.info(f"Creating new tunnel: {tunnel_name}")
        try:
            result = subprocess.run(
                ["cloudflared", "tunnel", "create", tunnel_name],
                capture_output=True,
                text=True,
                check=True,
            )
            for line in result.stdout.splitlines():
                if "Created tunnel" in line and "with id" in line:
                    parts = line.split()
                    if "id" in parts:
                        idx = parts.index("id") + 1
                        if idx < len(parts):
                            tunnel_id = parts[idx]
                            logger.info(f"Created tunnel: {tunnel_name} with ID {tunnel_id}")
                            break
            if not tunnel_id:
                raise RuntimeError(f"Could not extract tunnel ID: {result.stdout}")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to create tunnel {tunnel_name}: {e.stderr}")

    # DNS route
    logger.info(f"Setting up DNS route: {hostname} -> {tunnel_id}")
    try:
        subprocess.run(
            ["cloudflared", "tunnel", "route", "dns", tunnel_id, hostname],
            capture_output=True,
            text=True,
            check=True,
        )
        logger.info(f"DNS route configured: {hostname}")
    except subprocess.CalledProcessError as e:
        logger.warn(f"DNS route setup warning (may already exist): {e.stderr}")

    # Config file
    creds_file = cf_dir / f"{tunnel_id}.json"
    config_path = cf_dir / f"config-{srvc_clean}.yml"
    yaml_content = f"""tunnel: {tunnel_id}
credentials-file: {creds_file}

ingress:
  - hostname: {hostname}
    service: http://localhost:{port}
  - service: http_status:404
"""
    config_path.write_text(yaml_content)
    logger.info(f"Config written: {config_path}")

    # Start cloudflared
    logger.info(f"Starting cloudflared for {hostname}")
    subprocess.Popen(
        ["cloudflared", "tunnel", "--config", str(config_path), "run"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    return tunnel_id, hostname, str(config_path)


async def ensure_named_tunnel_route(port: int, logger: Logger | None = None) -> tuple[str, str]:
    """Set up a named tunnel route with cloudflared using existing TUNNEL_ID.

    Legacy path preserved for compatibility.
    """
    if logger is None:
        logger = DefaultLogger()

    domain_env = os.getenv("TUNNEL_DOMAIN", "kooshapari.com").lower()
    raw_srvc = (
        os.getenv("SRVC") or os.getenv("SERVICE_SLUG") or os.getenv("SERVICE_NAME") or "local"
    )
    srvc = dns_safe_slug(raw_srvc)
    prefix = dns_safe_slug(os.getenv("TUNNEL_PATH_PREFIX", srvc))
    expected_host = f"{srvc}.{domain_env}"
    tunnel_id = os.getenv("TUNNEL_ID")

    if not tunnel_id:
        logger.info("No TUNNEL_ID found, auto-creating tunnel")
        tunnel_id, hostname, config_path = await ensure_named_tunnel_autocreate(
            srvc, domain_env, port, logger,
        )
        return hostname, config_path

    cf_dir = Path.home() / ".cloudflared"
    creds_file = cf_dir / f"{tunnel_id}.json"
    config_path = cf_dir / f"config-{srvc}.yml"
    cf_dir.mkdir(exist_ok=True)

    with_path = os.getenv("TUNNEL_PATH_ROUTE", "").lower() == "true"
    yaml_content = f"""tunnel: {tunnel_id}
credentials-file: {creds_file}
ingress:
  - hostname: {expected_host}
    service: http://localhost:{port}
"""
    if with_path:
        yaml_content += f"""  - hostname: {domain_env}
    path: /{prefix}/*
    service: http://localhost:{port}
"""
    yaml_content += "  - service: http_status:404\n"

    config_path.write_text(yaml_content)

    logger.info(f"Ensuring named route: https://{expected_host} -> http://localhost:{port}")
    if with_path:
        logger.info(
            f"Ensuring path route: https://{domain_env}/{prefix}/* -> http://localhost:{port}",
        )

    # Ensure DNS route exists for provided TUNNEL_ID (legacy path)
    try:
        subprocess.run(
            ["cloudflared", "tunnel", "route", "dns", tunnel_id, expected_host],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except Exception:
        # Non-fatal: continue to start cloudflared process
        pass

    try:
        subprocess.Popen(
            ["cloudflared", "tunnel", "--config", str(config_path), "run"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info(f"Started cloudflared process for {expected_host}")
    except Exception as e:
        logger.warn(f"Failed to spawn cloudflared for {expected_host}: {e}")

    return expected_host, str(config_path)


async def create_kinfra_tunnel_if_enabled(
    port: int, options: dict[str, Any] | None = None,
) -> str | None:
    """
    Create a KInfra quick tunnel if ENABLE_KINFRA_TUNNEL is true and no TUNNEL_ID set.
    """
    if options is None:
        options = {}

    logger: Logger = options.get("logger", DefaultLogger())

    if os.getenv("ENABLE_KINFRA_TUNNEL") != "true":
        logger.info("KInfra tunnel disabled (ENABLE_KINFRA_TUNNEL not set to true)")
        return None

    if os.getenv("TUNNEL_ID"):
        logger.info("Named tunnel configured, skipping quick tunnel creation")
        return None

    try:
        import importlib

        lib_path = (
            options.get("kinfra_lib_path")
            or os.getenv("KINFRA_PYTHON_LIB")
            or "kinfra_tunnel_manager"
        )
        logger.info(f"Loading KInfra library: {lib_path}")
        module = importlib.import_module(lib_path)
        TunnelManager = getattr(module, "TunnelManager", None)
        if not TunnelManager:
            raise ImportError("TunnelManager not found in KInfra module")

        domain_env = os.getenv("TUNNEL_DOMAIN", "kooshapari.com")
        srvc = (
            os.getenv("SRVC") or os.getenv("SERVICE_SLUG") or os.getenv("SERVICE_NAME") or "local"
        )
        expected_host = f"{srvc}.{domain_env}"
        name = f" name={os.getenv('TUNNEL_NAME')}" if os.getenv("TUNNEL_NAME") else ""

        logger.info(f"Starting KInfra tunnel on port {port} ({domain_env}){name}")
        logger.info(f"Expected public hostname: https://{expected_host}")

        manager = TunnelManager()
        tunnel_config = TunnelConfig(
            port=port, startup_timeout=60000, protocol="http", env=dict(os.environ),
        )
        tunnel = await manager.create_quick_tunnel(tunnel_config.__dict__)  # type: ignore[attr-defined]

        if hasattr(tunnel, "url") and tunnel.url:
            logger.info(f"Tunnel ready: {tunnel.url}")
            return tunnel.url
        logger.info("Tunnel started (named tunnel in use)")
        return None

    except Exception as e:
        logger.warn(f"KInfra tunnel unavailable: {e}")
        return None
