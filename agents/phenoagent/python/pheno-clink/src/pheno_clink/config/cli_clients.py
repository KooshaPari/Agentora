"""
CLI client configuration loading and validation.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from .models import CLIClientConfig, ClientConfig

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

# Add pheno-sdk config bridge support
try:
    from pheno.config import get_config as get_pheno_config

    PHENO_CONFIG_AVAILABLE = True
except ImportError:
    PHENO_CONFIG_AVAILABLE = False

    def get_pheno_config():
        class _ConfigMock:
            def get(self, key, default=None):
                return default

        return _ConfigMock()


def load_client_configs(config_dir: Path) -> ClientConfig:
    """
    Load and merge all CLI client JSON configs from a directory.
    """
    if not config_dir.is_dir():
        logger.debug(f"CLI client config directory not found: {config_dir}")
        return ClientConfig()

    merged_clients: dict[str, CLIClientConfig] = {}

    for client_file in config_dir.glob("*.json"):
        try:
            raw = json.loads(client_file.read_text())
            if not isinstance(raw, dict):
                logger.warning(f"Invalid client config format in {client_file}")
                continue

            client_id = client_file.stem
            client_config = CLIClientConfig(**raw)
            merged_clients[client_id] = client_config
            logger.debug(f"Loaded CLI client config: {client_id} from {client_file}")

        except Exception as exc:
            logger.warning(f"Failed to load client config {client_file}: {exc}")
            continue

    return ClientConfig(cli_clients=merged_clients)


def save_client_config(client_id: str, config: CLIClientConfig, config_dir: Path) -> None:
    """
    Save a client configuration to JSON file.
    """
    config_dir.mkdir(parents=True, exist_ok=True)
    client_file = config_dir / f"{client_id}.json"

    with client_file.open("w", encoding="utf-8") as f:
        json.dump(config.dict(), f, indent=2, sort_keys=True)

    logger.debug(f"Saved CLI client config: {client_id} to {client_file}")
