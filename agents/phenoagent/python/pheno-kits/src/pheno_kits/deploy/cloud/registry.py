"""
Provider registry for managing cloud providers.
"""

import threading
from collections.abc import Callable

from .errors import ConflictError, ResourceNotFoundError, ValidationError
from .interfaces import CloudProvider, ProviderRegistry
from .types import Credentials, ProviderMetadata, ResourceType


class _ProviderRegistry(ProviderRegistry):
    """Thread-safe provider registry implementation.

    This is a singleton that manages all registered cloud providers.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._providers: dict[str, dict] = {}

    def register(
        self,
        metadata: ProviderMetadata,
        factory: Callable[[Credentials], CloudProvider],
    ) -> None:
        """
        Register a provider with the registry.
        """
        with self._lock:
            if not metadata.name:
                raise ValidationError(
                    provider="registry",
                    field="name",
                    message="Provider name cannot be empty",
                )

            if factory is None:
                raise ValidationError(
                    provider="registry",
                    field="factory",
                    message="Provider factory cannot be None",
                )

            if metadata.name in self._providers:
                raise ConflictError(
                    provider="registry",
                    message=f"Provider '{metadata.name}' is already registered",
                    conflicting_resource=metadata.name,
                )

            self._providers[metadata.name] = {
                "metadata": metadata,
                "factory": factory,
            }

    def unregister(self, provider_name: str) -> None:
        """
        Remove a provider from the registry.
        """
        with self._lock:
            if provider_name not in self._providers:
                raise ResourceNotFoundError(
                    provider="registry",
                    resource_id=provider_name,
                )

            del self._providers[provider_name]

    def get(self, provider_name: str, credentials: Credentials) -> CloudProvider:
        """
        Create a provider instance with credentials.
        """
        with self._lock:
            if provider_name not in self._providers:
                raise ResourceNotFoundError(
                    provider="registry",
                    resource_id=provider_name,
                )

            registered = self._providers[provider_name]
            factory = registered["factory"]

        try:
            return factory(credentials)
        except Exception as e:
            raise RuntimeError(f"Failed to create provider '{provider_name}': {e!s}") from e

    def list(self) -> list[ProviderMetadata]:
        """
        List all registered providers.
        """
        with self._lock:
            return [p["metadata"] for p in self._providers.values()]

    def supports(self, provider_name: str, resource_type: ResourceType) -> bool:
        """
        Check if provider supports a resource type.
        """
        with self._lock:
            if provider_name not in self._providers:
                return False

            metadata = self._providers[provider_name]["metadata"]
            return resource_type in metadata.supported_resources

    def get_metadata(self, provider_name: str) -> ProviderMetadata:
        """
        Get provider metadata.
        """
        with self._lock:
            if provider_name not in self._providers:
                raise ResourceNotFoundError(
                    provider="registry",
                    resource_id=provider_name,
                )

            return self._providers[provider_name]["metadata"]


# Global registry instance
_global_registry: _ProviderRegistry | None = None
_registry_lock = threading.Lock()


def get_registry() -> ProviderRegistry:
    """
    Get the global provider registry (singleton).
    """
    global _global_registry

    if _global_registry is None:
        with _registry_lock:
            if _global_registry is None:
                _global_registry = _ProviderRegistry()

    return _global_registry


def register_provider(
    metadata: ProviderMetadata,
    factory: Callable[[Credentials], CloudProvider],
) -> None:
    """
    Register a provider with the global registry.
    """
    get_registry().register(metadata, factory)


def unregister_provider(provider_name: str) -> None:
    """
    Unregister a provider from the global registry.
    """
    get_registry().unregister(provider_name)


def get_provider(provider_name: str, credentials: Credentials) -> CloudProvider:
    """
    Get a provider instance from the global registry.
    """
    return get_registry().get(provider_name, credentials)


def list_providers() -> list[ProviderMetadata]:
    """
    List all registered providers.
    """
    return get_registry().list()


def provider_supports(provider_name: str, resource_type: ResourceType) -> bool:
    """
    Check if a provider supports a resource type.
    """
    return get_registry().supports(provider_name, resource_type)


def get_provider_metadata(provider_name: str) -> ProviderMetadata:
    """
    Get metadata for a specific provider.
    """
    return get_registry().get_metadata(provider_name)


def get_supported_providers(resource_type: ResourceType) -> list[str]:
    """
    Get list of providers that support a resource type.
    """
    all_providers = list_providers()
    return [
        metadata.name for metadata in all_providers if resource_type in metadata.supported_resources
    ]


def provider_exists(provider_name: str) -> bool:
    """
    Check if a provider is registered.
    """
    try:
        get_registry().get_metadata(provider_name)
        return True
    except ResourceNotFoundError:
        return False


class ProviderInfo:
    """
    Detailed information about a registered provider.
    """

    def __init__(self, metadata: ProviderMetadata):
        self.metadata = metadata
        self.is_registered = True
        self.resource_types = metadata.supported_resources
        self.capabilities = metadata.capabilities


def get_provider_info(provider_name: str) -> ProviderInfo:
    """
    Get detailed information about a provider.
    """
    metadata = get_registry().get_metadata(provider_name)
    return ProviderInfo(metadata)


def must_register(
    metadata: ProviderMetadata,
    factory: Callable[[Credentials], CloudProvider],
) -> None:
    """Register a provider and raise exception on error.

    This is useful for init-time registration where you want to fail fast.
    """
    try:
        register_provider(metadata, factory)
    except Exception as e:
        raise RuntimeError(f"Failed to register provider '{metadata.name}': {e!s}") from e
