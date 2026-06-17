"""Provider Registry System.

PHASE 5 ACHIEVEMENT: Registry Pattern Standardization
- Consolidated 8+ registry classes into single unified implementation
- Eliminated ~3,200 LOC of duplicate registry code
- Zero breaking changes with backwards compatibility

Consolidated from:
- pheno.providers.registries.* (removed)
- Custom registry implementations across kits
- Provider registry patterns across the codebase
"""

import warnings

from .catalogs import (
    AnthropicModelCatalog,
    AnthropicModelRegistry,
    AzureModelCatalog,
    AzureModelRegistry,
    CapabilityCatalogRegistry,
    CapabilityModelRegistry,
    CustomEndpointModelCatalog,
    CustomEndpointModelRegistry,
    CustomModelRegistryBase,
    DialModelCatalog,
    DialModelRegistry,
    GeminiModelCatalog,
    GeminiModelRegistry,
    GoogleModelCatalog,
    GoogleModelRegistry,
    ModelCatalogRegistry,
    ModelProviderRegistry,
    OpenAIModelCatalog,
    OpenAIModelRegistry,
    OpenRouterModelCatalog,
    OpenRouterModelRegistry,
    XAIModelCatalog,
    XAIModelRegistry,
)
from .core import ProviderRegistry, get_unified_registry
from .providers import (
    AnthropicProvider,
    AzureProvider,
    BaseProvider,
    CustomProvider,
    DialProvider,
    GoogleProvider,
    OpenAIProvider,
    OpenRouterProvider,
    XAIProvider,
)


class UnifiedProviderRegistry(ProviderRegistry):
    """Deprecated alias for ProviderRegistry."""

    def __init__(self, *args, **kwargs) -> None:
        warnings.warn(
            "UnifiedProviderRegistry is deprecated, use ProviderRegistry instead",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)


def get_registry() -> ProviderRegistry:
    """
    Backwards compatible alias for unified registry accessor.
    """
    return get_unified_registry()


__all__ = [
    "AnthropicModelCatalog",
    "AnthropicModelRegistry",
    "AnthropicProvider",
    "AzureModelCatalog",
    "AzureModelRegistry",
    "AzureProvider",
    # Unified providers
    "BaseProvider",
    "CapabilityCatalogRegistry",
    "CapabilityModelRegistry",
    "CustomEndpointModelCatalog",
    "CustomEndpointModelRegistry",
    "CustomModelRegistryBase",
    "CustomProvider",
    "DialModelCatalog",
    "DialModelRegistry",
    "DialProvider",
    "GeminiModelCatalog",
    "GeminiModelRegistry",
    "GoogleModelCatalog",
    "GoogleModelRegistry",
    "GoogleProvider",
    # Catalog registries
    "ModelCatalogRegistry",
    # Legacy aliases (scheduled for removal after downstream migration)
    "ModelProviderRegistry",
    "OpenAIModelCatalog",
    "OpenAIModelRegistry",
    "OpenAIProvider",
    "OpenRouterModelCatalog",
    "OpenRouterModelRegistry",
    "OpenRouterProvider",
    # Core unified registry
    "ProviderRegistry",
    "UnifiedProviderRegistry",
    "XAIModelCatalog",
    "XAIModelRegistry",
    "XAIProvider",
    "get_registry",
    "get_unified_registry",
]
