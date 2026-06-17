"""Mixin for providers backed by capability registries.

Caches a registry instance and exposes convenience methods for providers that read their
supported models from JSON catalogs.
"""

from __future__ import annotations


class RegistryProviderMixin:
    """Mixin that wires a provider to a CapabilityModelRegistry subclass.

    Subclasses must set REGISTRY_CLASS to a class implementing:
      - list_models()
      - resolve(name_or_alias)
      - get_capabilities(name_or_alias)
    """

    REGISTRY_CLASS = None  # override in subclass

    # Cached per-provider registry instance
    _MODEL_REGISTRY = None

    @classmethod
    def get_model_registry(cls):
        if cls.REGISTRY_CLASS is None:
            raise NotImplementedError("REGISTRY_CLASS must be set on subclasses")
        if cls._MODEL_REGISTRY is None:
            cls._MODEL_REGISTRY = cls.REGISTRY_CLASS()
        return cls._MODEL_REGISTRY

    @classmethod
    def get_all_model_capabilities(cls) -> list[dict]:
        reg = cls.get_model_registry()
        return [reg.get_capabilities(name) or {} for name in reg.list_models()]

    @classmethod
    def resolve_model(cls, name_or_alias: str) -> dict | None:
        return cls.get_model_registry().resolve(name_or_alias)
