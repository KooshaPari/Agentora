"""
Model catalog registries built on top of the unified provider registry.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .core import ProviderRegistry as _ProviderRegistry

if TYPE_CHECKING:
    from collections.abc import Iterable


class ModelCatalogRegistry(_ProviderRegistry):
    """
    Registry that tracks model metadata in addition to provider entries.
    """


class CapabilityCatalogRegistry(ModelCatalogRegistry):
    """
    Registry supporting alias resolution and capability lookups.
    """

    def __init__(self) -> None:
        super().__init__()
        self._models: dict[str, dict[str, Any]] = {}
        self._alias_index: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Metadata helpers
    # ------------------------------------------------------------------
    def register_model(
        self, model_name: str, *, aliases: Iterable[str] = (), **metadata: Any,
    ) -> None:
        """
        Register a model and optional aliases/metadata.
        """
        canonical = model_name
        payload = {"model_name": canonical, "aliases": list(aliases), **metadata}
        self._models[canonical] = payload

        self._alias_index[canonical.lower()] = canonical
        for alias in aliases:
            self._alias_index[alias.lower()] = canonical

    def list_models(self) -> list[str]:
        """
        Return all registered model names.
        """
        return sorted(self._models.keys())

    def resolve(self, identifier: str) -> dict[str, Any] | None:
        """
        Resolve a model identifier (name or alias) to its metadata.
        """
        canonical = self._alias_index.get(identifier.lower())
        if not canonical:
            return None
        return dict(self._models[canonical])

    def get_capabilities(self, identifier: str) -> dict[str, Any] | None:
        """
        Return the capabilities for a model identifier.
        """
        entry = self.resolve(identifier)
        if not entry:
            return None
        entry.setdefault("friendly_name", f"{self.__class__.__name__} ({entry['model_name']})")
        return entry


class OpenAIModelCatalog(CapabilityCatalogRegistry):
    """
    Model catalog that reads OpenAI models from a JSON configuration file.
    """

    ENV_VAR = "OPENAI_MODELS_CONFIG_PATH"

    def __init__(self, config_path: str | None = None) -> None:
        super().__init__()
        self.config_path = config_path or os.getenv(self.ENV_VAR)
        self._load_catalog()

    def _load_catalog(self) -> None:
        if not self.config_path:
            return

        path = Path(self.config_path).expanduser()
        if not path.exists():
            return

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return

        models = data.get("models", [])
        if not isinstance(models, list):
            return

        for entry in models:
            if not isinstance(entry, dict):
                continue
            name = entry.get("model_name")
            if not name:
                continue
            aliases = entry.get("aliases", [])
            if not isinstance(aliases, list):
                aliases = []

            metadata = {k: v for k, v in entry.items() if k not in {"model_name", "aliases"}}
            metadata.setdefault("friendly_name", f"OpenAI ({name})")
            self.register_model(name, aliases=aliases, **metadata)


class AnthropicModelCatalog(CapabilityCatalogRegistry):
    """
    Model catalog seeded with Anthropic defaults.
    """

    def __init__(self, config_path: str | None = None) -> None:
        super().__init__()
        self.config_path = config_path
        try:
            from .providers import AnthropicProvider

            if os.getenv("ANTHROPIC_API_KEY"):
                self.register_provider("anthropic-default", AnthropicProvider, {})
        except ImportError:  # pragma: no cover - optional dependency
            pass


class GoogleModelCatalog(CapabilityCatalogRegistry):
    """
    Model catalog for Google offerings.
    """


class GeminiModelCatalog(GoogleModelCatalog):
    """
    Alias of Google model catalog for Gemini.
    """


class AzureModelCatalog(CapabilityCatalogRegistry):
    """
    Model catalog for Azure OpenAI deployments.
    """


class XAIModelCatalog(CapabilityCatalogRegistry):
    """
    Model catalog for xAI models.
    """


class DialModelCatalog(CapabilityCatalogRegistry):
    """
    Model catalog for Dial integrations.
    """


class OpenRouterModelCatalog(CapabilityCatalogRegistry):
    """
    Model catalog for OpenRouter providers.
    """


class CustomEndpointModelCatalog(CapabilityCatalogRegistry):
    """
    Model catalog for custom endpoint integrations.
    """


# Backwards compatible aliases to support phased migration away from legacy names.
ModelProviderRegistry = ModelCatalogRegistry
CapabilityModelRegistry = CapabilityCatalogRegistry
OpenAIModelRegistry = OpenAIModelCatalog
AnthropicModelRegistry = AnthropicModelCatalog
GoogleModelRegistry = GoogleModelCatalog
GeminiModelRegistry = GeminiModelCatalog
AzureModelRegistry = AzureModelCatalog
XAIModelRegistry = XAIModelCatalog
DialModelRegistry = DialModelCatalog
OpenRouterModelRegistry = OpenRouterModelCatalog
CustomModelRegistryBase = CapabilityCatalogRegistry
CustomEndpointModelRegistry = CustomEndpointModelCatalog

__all__ = [
    "AnthropicModelCatalog",
    "AzureModelCatalog",
    "CapabilityCatalogRegistry",
    "CustomEndpointModelCatalog",
    "DialModelCatalog",
    "GeminiModelCatalog",
    "GoogleModelCatalog",
    "ModelCatalogRegistry",
    "OpenAIModelCatalog",
    "OpenRouterModelCatalog",
    "XAIModelCatalog",
]
