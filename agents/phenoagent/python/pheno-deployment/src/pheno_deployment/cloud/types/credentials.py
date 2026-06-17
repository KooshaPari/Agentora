"""
Credentials and provider metadata types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .enums import Capability, ResourceType


@dataclass
class Credentials:
    """
    Authentication credentials supplied to cloud providers.
    """

    type: str
    data: dict[str, str]
    region: str | None = None
    endpoint: str | None = None


@dataclass
class Region:
    """
    Geographic region available for resource provisioning.
    """

    id: str
    name: str
    location: str
    available: bool
    deprecated: bool = False
    zones: list[str] = field(default_factory=list)


@dataclass
class ProviderMetadata:
    """
    Metadata describing a provider's capabilities and supported regions.
    """

    name: str
    version: str
    supported_resources: list[ResourceType]
    capabilities: list[Capability]
    regions: list[Region]
    auth_types: list[str]
    description: str


__all__ = ["Credentials", "ProviderMetadata", "Region"]
