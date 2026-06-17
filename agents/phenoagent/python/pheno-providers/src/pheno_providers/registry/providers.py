"""Unified Provider Implementations.

Consolidated from all pheno.providers.registries.* implementations into unified provider
classes.
"""

import os
from abc import ABC


class BaseProvider(ABC):
    """
    Base provider class for all unified providers.
    """

    def __init__(self, api_key: str | None = None, **kwargs):
        self.api_key = api_key or os.getenv(self._get_env_var())
        self.config = kwargs

    def _get_env_var(self) -> str:
        """
        Override in subclasses to return the environment variable name.
        """
        return ""

    def get_supported_models(self) -> list[str]:
        """
        Return list of supported models.
        """
        return []

    async def validate_config(self) -> bool:
        """
        Validate provider configuration.
        """
        return self.api_key is not None


class OpenAIProvider(BaseProvider):
    """OpenAI Provider - Unified."""

    def _get_env_var(self) -> str:
        return "OPENAI_API_KEY"

    def get_supported_models(self) -> list[str]:
        return ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]


class AnthropicProvider(BaseProvider):
    """Anthropic Provider - Unified."""

    def _get_env_var(self) -> str:
        return "ANTHROPIC_API_KEY"

    def get_supported_models(self) -> list[str]:
        return ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"]


class GoogleProvider(BaseProvider):
    """Google Provider - Unified."""

    def _get_env_var(self) -> str:
        return "GOOGLE_API_KEY"

    def get_supported_models(self) -> list[str]:
        return ["gemini-pro", "gemini-pro-vision", "gemini-ultra"]


class AzureProvider(BaseProvider):
    """Azure Provider - Unified."""

    def __init__(
        self, endpoint: str, deployment_name: str, api_version: str = "2023-05-15", **kwargs,
    ):
        super().__init__(**kwargs)
        self.endpoint = endpoint
        self.deployment_name = deployment_name
        self.api_version = api_version

    def _get_env_var(self) -> str:
        return "AZURE_OPENAI_API_KEY"

    def get_supported_models(self) -> list[str]:
        return ["gpt-35-turbo", "gpt-4", "gpt-4-32k"]


class XAIProvider(BaseProvider):
    """XAI Provider - Unified."""

    def _get_env_var(self) -> str:
        return "XAI_API_KEY"

    def get_supported_models(self) -> list[str]:
        return ["grok-1", "grok-1-chat"]


class DialProvider(BaseProvider):
    """DIAL Provider - Unified."""

    def _get_env_var(self) -> str:
        return "DIAL_API_KEY"

    def get_supported_models(self) -> list[str]:
        return ["dial-chat", "dial-completion"]


class OpenRouterProvider(BaseProvider):
    """OpenRouter Provider - Unified."""

    def _get_env_var(self) -> str:
        return "OPENROUTER_API_KEY"

    def get_supported_models(self) -> list[str]:
        return ["openai/gpt-4", "anthropic/claude-3"]


class CustomProvider(BaseProvider):
    """Custom Provider - Unified placeholder."""

    def _get_env_var(self) -> str:
        return "CUSTOM_PROVIDER_API_KEY"

    def get_supported_models(self) -> list[str]:
        return ["custom-model"]
