"""
Shared provider enums and transport data classes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping, MutableMapping


class ProviderType(StrEnum):
    """
    Enumeration of supported model providers.
    """

    GOOGLE = "google"
    OPENAI = "openai"
    AZURE = "azure"
    XAI = "xai"
    DIAL = "dial"
    CUSTOM = "custom"
    OPENROUTER = "openrouter"


class ModelCategory(StrEnum):
    """
    Categories for model capabilities and tool requirements.
    """

    FAST = "fast"
    BALANCED = "balanced"
    POWERFUL = "powerful"


@dataclass(slots=True)
class ProviderRequestContext:
    """Additional metadata supplied by routing layers when invoking providers.

    These fields are optional and allow downstream adapters to make informed decisions
    about prioritisation, budgeting, and telemetry without coupling the provider surface
    to a specific router implementation.
    """

    logical_model: str | None = None
    routing_priority: str | None = None
    budget_remaining_usd: float | None = None
    user_id: str | None = None
    organisation_id: str | None = None
    extra: MutableMapping[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProviderResponseMetadata:
    """
    Supplementary metadata returned by provider adapters.
    """

    model_actual: str | None = None
    duration_ms: float | None = None
    cost_usd: float | None = None
    usage: Mapping[str, int] = field(default_factory=dict)
    retry_hint: str | None = None
    extra: Mapping[str, Any] = field(default_factory=dict)
