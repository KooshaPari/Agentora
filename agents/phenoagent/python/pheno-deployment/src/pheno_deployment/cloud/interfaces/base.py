"""
Core cloud provider interface declarations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types import (
        Capability,
        Credentials,
        ProviderMetadata,
        Resource,
        ResourceConfig,
        ResourceFilter,
        ResourceType,
    )


class CloudProvider(ABC):
    """
    Contract that Pheno cloud providers must satisfy.
    """

    @abstractmethod
    def get_metadata(self) -> ProviderMetadata: ...

    @abstractmethod
    def supports_resource(self, resource_type: ResourceType) -> bool: ...

    @abstractmethod
    def get_capabilities(self) -> list[Capability]: ...

    @abstractmethod
    async def initialize(self, credentials: Credentials) -> None: ...

    @abstractmethod
    async def validate_credentials(self) -> bool: ...

    @abstractmethod
    async def create_resource(self, config: ResourceConfig) -> Resource: ...

    @abstractmethod
    async def get_resource(self, resource_id: str) -> Resource: ...

    @abstractmethod
    async def update_resource(self, resource_id: str, config: ResourceConfig) -> Resource: ...

    @abstractmethod
    async def delete_resource(self, resource_id: str) -> None: ...

    @abstractmethod
    async def list_resources(self, filter: ResourceFilter | None = None) -> list[Resource]: ...


__all__ = ["CloudProvider"]
