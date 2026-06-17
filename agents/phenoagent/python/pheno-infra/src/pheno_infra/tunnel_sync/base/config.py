"""
Configuration and setup helpers for tunnel manager.
"""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from ...exceptions import ConfigurationError
from ..models import CLOUDFLARE_API_TOKEN_FALLBACK

logger = logging.getLogger(__name__)


@dataclass
class TunnelConfig:
    """
    Runtime configuration for tunnel operations.
    """

    domain: str = "kooshapari.com"
    cloudflared_dir: Path = Path.home() / ".cloudflared"
    tunnel_startup_timeout: float = 30.0
    health_check_interval: float = 60.0
    use_unified_tunnel: bool = True
    cleanup_on_start: bool = True
    cloudflare_api_token: str | None = None
    verbose: bool | None = None

    def ensure_dirs(self) -> None:
        self.cloudflared_dir.mkdir(exist_ok=True)

    def determine_verbose(self) -> bool:
        if self.verbose is not None:
            return self.verbose
        env_verbose = os.getenv("KINFRA_TUNNEL_VERBOSE")
        if env_verbose is not None:
            return env_verbose.strip().lower() in {"1", "true", "yes", "on"}
        return logger.isEnabledFor(logging.DEBUG)


def resolve_cloudflare_token(
    config: TunnelConfig, explicit_token: str | None = None,
) -> str | None:
    """
    Resolve a Cloudflare API token from explicit value, env, or local files.
    """

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
                logger.debug("Using Cloudflare token from %s", kinfra_token_file)
                return token
        except Exception as exc:
            logger.warning("Failed to read token from %s: %s", kinfra_token_file, exc)

    cf_token_file = config.cloudflared_dir / "cloudflare_token"
    if cf_token_file.exists():
        try:
            token = cf_token_file.read_text().strip()
            if token:
                logger.debug("Using Cloudflare token from %s", cf_token_file)
                return token
        except Exception as exc:
            logger.debug("Failed to read token from %s: %s", cf_token_file, exc)

    if "kooshapari.com" in config.domain and CLOUDFLARE_API_TOKEN_FALLBACK:
        logger.debug("Using hardcoded fallback Cloudflare token")
        return CLOUDFLARE_API_TOKEN_FALLBACK

    logger.debug("No Cloudflare API token found")
    return None


def verify_cloudflared_setup(config: TunnelConfig) -> None:
    """
    Ensure cloudflared binary and authentication are available.
    """

    if not shutil.which("cloudflared"):
        raise ConfigurationError(
            "cloudflared not found. Install it: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/",
        )
    cert_path = config.cloudflared_dir / "cert.pem"
    if not cert_path.exists():
        raise ConfigurationError("cloudflared not authenticated. Run: cloudflared tunnel login")


__all__ = ["TunnelConfig", "resolve_cloudflare_token", "verify_cloudflared_setup"]
