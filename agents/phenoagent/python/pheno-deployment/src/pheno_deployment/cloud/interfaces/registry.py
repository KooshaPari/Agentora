"""
Provider registry abstraction.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types import Credentials, ProviderMetadata, ResourceType
    from .base import CloudProvider


class ProviderRegistry(ABC):
    """
    Registry responsible for discovering and instantiating cloud providers.
    """

    @abstractmethod
    def register(self, metadata: ProviderMetadata, factory: callable) -> None: ...

    @abstractmethod
    def unregister(self, provider_name: str) -> None: ...

    @abstractmethod
    def get(self, provider_name: str, credentials: Credentials) -> CloudProvider: ...

    @abstractmethod
    def list(self) -> list[ProviderMetadata]: ...

    @abstractmethod
    def supports(self, provider_name: str, resource_type: ResourceType) -> bool: ...

    @abstractmethod
    def get_metadata(self, provider_name: str) -> ProviderMetadata: ...


__all__ = ["ProviderRegistry"]
