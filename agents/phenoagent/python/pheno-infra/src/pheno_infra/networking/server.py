"""
Server startup with smart networking (port allocation + optional tunnel + health).
"""

from __future__ import annotations

import contextlib
import os

from pheno.infra.utils.dns import dns_safe_slug

from .health_checks import wait_for_health
from .options import DefaultLogger, Logger, NetworkingOptions, NetworkStartResult
from .ports import allocate_free_port
from .tunnel_setup import create_kinfra_tunnel_if_enabled, ensure_named_tunnel_route


async def start_server_with_smart_networking(
    app: object, options: NetworkingOptions | None = None,
) -> NetworkStartResult:
    if options is None:
        options = NetworkingOptions()

    if options.logger is None:
        options.logger = DefaultLogger()

    logger: Logger = options.logger

    # Respect PORT from env
    if options.respect_env_port and os.getenv("PORT"):
        try:
            env_port = int(os.getenv("PORT", ""))
            if not options.preferred_port:
                options.preferred_port = env_port
        except ValueError:
            pass

    # Force dynamic port
    if os.getenv("FORCE_DYNAMIC_PORT") == "true":
        options.preferred_port = None

    port = allocate_free_port(options.preferred_port, logger)

    logger.info(f"Server started on port {port}")
    logger.info(f"Local: http://localhost:{port}")
    logger.info(f"Health: http://localhost:{port}/healthz")

    result = NetworkStartResult(port=port)

    if options.enable_tunnel:
        logger.info(f"Starting tunnel setup for port {port}")

        if os.getenv("TUNNEL_ID"):
            expected_host, _ = await ensure_named_tunnel_route(port, logger)
            result.expected_host = expected_host
            logger.info(f"Expected public hostname: https://{expected_host}")
            health_ok = await wait_for_health(f"https://{expected_host}", 20, logger)
            if health_ok:
                logger.info(f"Reachable: https://{expected_host}/healthz")
            else:
                logger.warn(f"Health probe timed out: https://{expected_host}/healthz")

            if os.getenv("TUNNEL_PATH_ROUTE", "").lower() == "true":
                domain_env = os.getenv("TUNNEL_DOMAIN", "kooshapari.com").lower()
                raw_srvc = (
                    os.getenv("SRVC")
                    or os.getenv("SERVICE_SLUG")
                    or os.getenv("SERVICE_NAME")
                    or "local"
                )
                prefix = dns_safe_slug(os.getenv("TUNNEL_PATH_PREFIX", raw_srvc))
                path_base = f"https://{domain_env}/{prefix}"
                if await wait_for_health(path_base, 20, logger):
                    logger.info(f"Reachable (path): {path_base}/healthz")
                else:
                    logger.warn(f"Health probe timed out (path): {path_base}/healthz")

        elif os.getenv("ENABLE_KINFRA_TUNNEL") == "true":
            tunnel_url = await create_kinfra_tunnel_if_enabled(
                port,
                {
                    "kinfra_lib_path": options.kinfra_lib_path,
                    "logger": logger,
                },
            )
            if tunnel_url:
                result.tunnel_url = tunnel_url
                logger.info(f"Public: {tunnel_url}")
                logger.info(f"Health: {tunnel_url}/healthz")
                if await wait_for_health(tunnel_url, 20, logger):
                    logger.info(f"Reachable: {tunnel_url.rstrip('/')}/healthz")
                else:
                    logger.warn(f"Health probe timed out: {tunnel_url.rstrip('/')}/healthz")

    return result


def get_networking_config_from_env() -> NetworkingOptions:
    preferred_port = None
    port_env = os.getenv("PREFERRED_PORT")
    if port_env:
        with contextlib.suppress(ValueError):
            preferred_port = int(port_env)

    return NetworkingOptions(
        preferred_port=preferred_port,
        respect_env_port=os.getenv("RESPECT_ENV_PORT", "true") != "false",
        dynamic_fallback=os.getenv("DYNAMIC_FALLBACK", "true") != "false",
        enable_tunnel=os.getenv("ENABLE_KINFRA_TUNNEL") == "true" or bool(os.getenv("TUNNEL_ID")),
        kinfra_lib_path=os.getenv("KINFRA_PYTHON_LIB"),
        logger=DefaultLogger(),
    )
