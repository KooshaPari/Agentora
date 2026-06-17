"""
Provider catalog loading utilities.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ..shared import ProviderType

logger = logging.getLogger(__name__)

# Global catalog cache
_catalog_cache: dict[ProviderType, dict[str, Any]] = {}


def load_provider_catalogs(catalog_dir: Path | None = None) -> dict[ProviderType, dict[str, Any]]:
    """Load provider model catalogs from JSON files.

    Args:
        catalog_dir: Directory containing catalog JSON files. If None, uses default.

    Returns:
        Dictionary mapping ProviderType to catalog data
    """
    global _catalog_cache

    if catalog_dir is None:
        # Try to find catalogs relative to this module
        this_file = Path(__file__).resolve()
        catalog_dir = this_file.parent.parent.parent.parent / "conf" / "catalogs"

    if not catalog_dir.exists():
        logger.warning(f"Catalog directory not found: {catalog_dir}")
        return {}

    catalog_files = {
        ProviderType.AZURE: "azure_models.json",
        ProviderType.GEMINI: "gemini_models.json",
        ProviderType.OPENAI: "openai_models.json",
        ProviderType.OPENROUTER: "openrouter_models.json",
        ProviderType.XAI: "xai_models.json",
        ProviderType.DIAL: "dial_models.json",
        ProviderType.CUSTOM: "custom_models.json",
    }

    catalogs: dict[ProviderType, dict[str, Any]] = {}

    for provider_type, filename in catalog_files.items():
        catalog_file = catalog_dir / filename
        if catalog_file.exists():
            try:
                data = json.loads(catalog_file.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    catalogs[provider_type] = data
                    logger.debug(f"Loaded catalog for {provider_type.value} from {filename}")
                else:
                    logger.warning(f"Invalid catalog format in {filename}")
            except Exception as exc:
                logger.warning(f"Failed to load catalog {filename}: {exc}")
        else:
            logger.debug(f"Catalog file not found: {filename}")

    _catalog_cache = catalogs
    return catalogs


def get_catalog_for_provider(provider_type: ProviderType) -> dict[str, Any]:
    """Get catalog data for a specific provider.

    Args:
        provider_type: The provider type to get catalog for

    Returns:
        Catalog data dictionary (potentially empty if not found)
    """
    if not _catalog_cache:
        load_provider_catalogs()

    return _catalog_cache.get(provider_type, {})


def get_all_models_for_provider(provider_type: ProviderType) -> list[str]:
    """Get all model names for a provider from the catalog.

    Args:
        provider_type: The provider type

    Returns:
        List of model names, potentially empty
    """
    catalog = get_catalog_for_provider(provider_type)

    models = []
    for model_data in catalog.values():
        if isinstance(model_data, dict) and "name" in model_data:
            models.append(model_data["name"])

    return models


def get_model_info(provider_type: ProviderType, model_name: str) -> dict[str, Any]:
    """Get information about a specific model from the catalog.

    Args:
        provider_type: The provider type
        model_name: Name of the model to look up

    Returns:
        Model information dictionary, potentially empty
    """
    catalog = get_catalog_for_provider(provider_type)

    # Search by exact name match first
    if model_name in catalog:
        return catalog[model_name]

    # Search by case-insensitive match
    for value in catalog.values():
        if isinstance(value, dict) and value.get("name", "").lower() == model_name.lower():
            return value

    return {}
