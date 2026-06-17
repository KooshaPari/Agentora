"""
Provider registry and management for pheno-sdk.
"""

from __future__ import annotations

from .registry import ModelProviderRegistry, get_registry
from .shared import (
    ProviderRequestContext,
    ProviderResponseMetadata,
    ProviderType,
)

try:
    from .catalogs.loader import get_all_models_for_provider
except Exception:  # pragma: no cover - optional dependency
    get_all_models_for_provider = None  # type: ignore[assignment]

__all__ = [
    "ModelProviderRegistry",
    "ProviderRequestContext",
    "ProviderResponseMetadata",
    "ProviderType",
    "get_registry",
]

# Try to import catalogs but don't fail if missing
if get_all_models_for_provider is not None:
    __all__.append("get_all_models_for_provider")
