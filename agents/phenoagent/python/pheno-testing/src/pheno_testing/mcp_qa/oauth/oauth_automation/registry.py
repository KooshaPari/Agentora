"""
Simple registry for OAuth provider flow configurations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Mapping, Optional

from .config import OAuthFlowConfig, flow_config_from_dict, load_flow_config_from_yaml


class ProviderRegistry:
    """
    Keeps track of registered OAuth flow configurations.
    """

    def __init__(self, providers: Optional[Iterable[OAuthFlowConfig]] = None):
        self._providers: Dict[str, OAuthFlowConfig] = {}
        if providers:
            for config in providers:
                self.register(config)

    def register(self, config: OAuthFlowConfig) -> None:
        key = config.provider.lower()
        self._providers[key] = config

    def register_from_dict(self, data: Mapping[str, object]) -> OAuthFlowConfig:
        """
        Register a provider from a mapping payload.
        """

        config = flow_config_from_dict(data)
        self.register(config)
        return config

    def register_from_yaml(self, yaml_path: Path | str) -> OAuthFlowConfig:
        """
        Register a provider by loading a YAML configuration.
        """

        config = load_flow_config_from_yaml(yaml_path)
        self.register(config)
        return config

    def get(self, provider: str) -> OAuthFlowConfig:
        try:
            return self._providers[provider.lower()]
        except KeyError as exc:
            available = ", ".join(sorted(self._providers)) or "<none>"
            raise KeyError(
                f"Unknown OAuth provider '{provider}'. Registered providers: {available}"
            ) from exc

    def __contains__(self, provider: str) -> bool:
        return provider.lower() in self._providers

    def providers(self):
        return tuple(sorted(self._providers))
