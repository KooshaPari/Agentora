"""Unified Model Provider Registry using BaseRegistry.

This replaces the old ModelProviderRegistry with a simpler implementation based on
BaseRegistry[T].
"""

import logging
from typing import Any, Optional

from pheno.adapters.base_registry import BaseRegistry

from .shared import ProviderType

try:
    from utils.env import get_env
except ImportError:
    import os

    def get_env(key: str, default: str | None = None) -> str | None:
        return os.environ.get(key, default)


logger = logging.getLogger(__name__)


class ModelProvider:
    """
    Base class for model providers.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key

    def list_models(self, respect_restrictions: bool = True) -> list[str]:
        """
        List available models from this provider.
        """
        return []

    def get_model_info(self, model_name: str) -> dict[str, Any]:
        """
        Get information about a specific model.
        """
        return {}

    def validate_model_name(self, model_name: str) -> bool:
        """
        Validate if this provider can handle the given model name.
        """
        try:
            models = self.list_models(respect_restrictions=False)
            return model_name in models
        except Exception:
            return False

    def get_preferred_model(self, tool_category: str, allowed_models: list[str]) -> str | None:
        """
        Get preferred model for a given tool category from allowed models.
        """
        if not allowed_models:
            return None
        return allowed_models[0]

    def get_provider_type(self) -> ProviderType:
        """
        Get the provider type for this instance.
        """
        return ProviderType.CUSTOM


class ModelProviderRegistry(BaseRegistry[type]):
    """Unified model provider registry using BaseRegistry.

    Simplified implementation that uses BaseRegistry for storage and lookup. Maintains
    singleton pattern and provider priority order.
    """

    _instance: Optional["ModelProviderRegistry"] = None

    # Provider priority order for model selection
    PROVIDER_PRIORITY_ORDER = [
        ProviderType.GOOGLE,
        ProviderType.OPENAI,
        ProviderType.AZURE,
        ProviderType.XAI,
        ProviderType.DIAL,
        ProviderType.CUSTOM,
        ProviderType.OPENROUTER,
    ]

    def __new__(cls):
        """
        Singleton pattern.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Initialize BaseRegistry
            BaseRegistry.__init__(cls._instance)
            cls._instance._initialized_providers: dict[ProviderType, ModelProvider] = {}
            logger.debug("Created new ModelProviderRegistry instance")
        return cls._instance

    @classmethod
    def register_provider(cls, provider_type: ProviderType, provider_class: type) -> None:
        """
        Register a provider class.
        """
        instance = cls()
        instance.register(
            provider_type.value,
            provider_class,
            provider_type=provider_type,
            priority=(
                cls.PROVIDER_PRIORITY_ORDER.index(provider_type)
                if provider_type in cls.PROVIDER_PRIORITY_ORDER
                else 999
            ),
        )
        logger.debug(f"Registered provider: {provider_type.value}")

    def get_provider(self, provider_type: ProviderType) -> ModelProvider | None:
        """
        Get or create a provider instance.
        """
        # Check if already initialized
        if provider_type in self._initialized_providers:
            return self._initialized_providers[provider_type]

        # Get provider class
        try:
            provider_class = self.get(provider_type.value)
        except KeyError:
            logger.warning(f"Provider not registered: {provider_type.value}")
            return None

        # Get API key from environment
        api_key = self._get_api_key(provider_type)
        if not api_key:
            logger.warning(f"No API key found for provider: {provider_type.value}")
            return None

        # Create and cache provider instance
        try:
            provider = provider_class(api_key)
            self._initialized_providers[provider_type] = provider
            logger.debug(f"Initialized provider: {provider_type.value}")
            return provider
        except Exception as e:
            logger.exception(f"Failed to initialize provider {provider_type.value}: {e}")
            return None

    def _get_api_key(self, provider_type: ProviderType) -> str | None:
        """
        Get API key for a provider from environment.
        """
        env_var_map = {
            ProviderType.OPENAI: "OPENAI_API_KEY",
            ProviderType.GOOGLE: "GOOGLE_API_KEY",
            ProviderType.AZURE: "AZURE_OPENAI_API_KEY",
            ProviderType.XAI: "XAI_API_KEY",
            ProviderType.DIAL: "DIAL_API_KEY",
            ProviderType.OPENROUTER: "OPENROUTER_API_KEY",
            ProviderType.CUSTOM: "CUSTOM_API_KEY",
        }

        env_var = env_var_map.get(provider_type)
        if env_var:
            return get_env(env_var)
        return None

    def list_available_providers(self) -> list[ProviderType]:
        """
        List all available providers (with API keys).
        """
        available = []
        for provider_type in self.PROVIDER_PRIORITY_ORDER:
            if self._get_api_key(provider_type):
                available.append(provider_type)
        return available

    def list_all_models(self, respect_restrictions: bool = True) -> dict[str, list[str]]:
        """
        List all models from all available providers.
        """
        all_models = {}
        for provider_type in self.list_available_providers():
            provider = self.get_provider(provider_type)
            if provider:
                try:
                    models = provider.list_models(respect_restrictions)
                    all_models[provider_type.value] = models
                except Exception as e:
                    logger.exception(f"Error listing models for {provider_type.value}: {e}")
        return all_models

    def find_provider_for_model(self, model_name: str) -> ProviderType | None:
        """
        Find which provider can handle a given model name.
        """
        for provider_type in self.PROVIDER_PRIORITY_ORDER:
            provider = self.get_provider(provider_type)
            if provider and provider.validate_model_name(model_name):
                return provider_type
        return None

    def get_model_info(self, model_name: str) -> dict[str, Any] | None:
        """
        Get information about a model.
        """
        provider_type = self.find_provider_for_model(model_name)
        if provider_type:
            provider = self.get_provider(provider_type)
            if provider:
                return provider.get_model_info(model_name)
        return None

    @classmethod
    def reset(cls) -> None:
        """
        Reset the singleton instance (for testing).
        """
        cls._instance = None


# Singleton instance
def get_registry() -> ModelProviderRegistry:
    """
    Get the global model provider registry.
    """
    return ModelProviderRegistry()


__all__ = [
    "ModelProvider",
    "ModelProviderRegistry",
    "get_registry",
]
