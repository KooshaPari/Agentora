"""In-Memory Resource Provider.

Implementation of ResourceProvider with built-in scheme handlers.
"""

import logging
import re
from typing import Any

from pheno.mcp.types import Resource
from pheno.ports.mcp import ResourceProvider, ResourceSchemeHandler

logger = logging.getLogger(__name__)


class InMemoryResourceProvider(ResourceProvider):
    """In-memory resource provider with scheme handlers.

    Supports registering custom scheme handlers and provides
    built-in handlers for common schemes.

    Example:
        >>> provider = InMemoryResourceProvider()
        >>> provider.register_scheme("config", ConfigSchemeHandler())
        >>> config = await provider.get_resource("config://app/database")
    """

    def __init__(self):
        self._schemes: dict[str, ResourceSchemeHandler] = {}
        self._resources: dict[str, Resource] = {}

    def _parse_uri(self, uri: str) -> tuple[str, str]:
        """
        Parse URI into scheme and path.
        """
        if "://" not in uri:
            raise ValueError(f"Invalid URI format: {uri}")

        scheme, path = uri.split("://", 1)
        return scheme, path

    async def get_resource(self, uri: str) -> Any:
        """
        Get a resource by URI.
        """
        scheme, _path = self._parse_uri(uri)

        if scheme not in self._schemes:
            raise ValueError(f"Unsupported scheme: {scheme}://")

        handler = self._schemes[scheme]
        return await handler.get_resource(uri)

    async def list_resources(self, pattern: str) -> list[str]:
        """
        List resources matching a pattern.
        """
        scheme, _path_pattern = self._parse_uri(pattern)

        if scheme not in self._schemes:
            raise ValueError(f"Unsupported scheme: {scheme}://")

        handler = self._schemes[scheme]
        return await handler.list_resources(pattern)

    def register_scheme(self, scheme: str, handler: ResourceSchemeHandler) -> None:
        """
        Register a scheme handler.
        """
        self._schemes[scheme] = handler
        logger.info(f"Registered resource scheme: {scheme}://")

    def unregister_scheme(self, scheme: str) -> None:
        """
        Unregister a scheme handler.
        """
        if scheme in self._schemes:
            del self._schemes[scheme]
            logger.info(f"Unregistered resource scheme: {scheme}://")

    def get_scheme_handler(self, scheme: str) -> ResourceSchemeHandler:
        """
        Get the handler for a scheme.
        """
        if scheme not in self._schemes:
            raise ValueError(f"Unsupported scheme: {scheme}://")
        return self._schemes[scheme]

    def list_schemes(self) -> list[str]:
        """
        List all registered schemes.
        """
        return list(self._schemes.keys())

    async def create_resource(
        self, uri: str, data: Any, metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Create a new resource.
        """
        resource = Resource(uri=uri, data=data, metadata=metadata or {})
        self._resources[uri] = resource
        logger.info(f"Created resource: {uri}")
        return uri

    async def update_resource(self, uri: str, data: Any) -> None:
        """
        Update an existing resource.
        """
        if uri not in self._resources:
            raise ValueError(f"Resource not found: {uri}")

        self._resources[uri].update(data)
        logger.info(f"Updated resource: {uri}")

    async def delete_resource(self, uri: str) -> None:
        """
        Delete a resource.
        """
        if uri in self._resources:
            del self._resources[uri]
            logger.info(f"Deleted resource: {uri}")


class ConfigSchemeHandler(ResourceSchemeHandler):
    """Handler for config:// scheme.

    Provides access to configuration values.

    Example:
        >>> handler = ConfigSchemeHandler()
        >>> config = await handler.get_resource("config://app/database/host")
    """

    def __init__(self):
        self._config: dict[str, Any] = {}

    def _get_nested(self, path: str) -> Any:
        """
        Get nested config value by dot-separated path.
        """
        parts = path.split("/")
        current = self._config

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                raise ValueError(f"Config not found: {path}")

        return current

    async def get_resource(self, uri: str) -> Any:
        """
        Get config value.
        """
        _, path = uri.split("://", 1)
        return self._get_nested(path)

    async def list_resources(self, uri: str) -> list[str]:
        """
        List config keys.
        """
        _, path = uri.split("://", 1)

        try:
            current = self._get_nested(path)
            if isinstance(current, dict):
                return [f"config://{path}/{key}" for key in current]
        except ValueError:
            pass

        return []

    def supports_scheme(self, scheme: str) -> bool:
        """
        Check if scheme is supported.
        """
        return scheme == "config"

    def set_config(self, config: dict[str, Any]) -> None:
        """
        Set the configuration data.
        """
        self._config = config


class MemorySchemeHandler(ResourceSchemeHandler):
    """Handler for memory:// scheme.

    Simple in-memory key-value store.

    Example:
        >>> handler = MemorySchemeHandler()
        >>> await handler.set("memory://cache/user-123", {"name": "Alice"})
        >>> user = await handler.get_resource("memory://cache/user-123")
    """

    def __init__(self):
        self._store: dict[str, Any] = {}

    async def get_resource(self, uri: str) -> Any:
        """
        Get value from memory.
        """
        if uri not in self._store:
            raise ValueError(f"Resource not found: {uri}")
        return self._store[uri]

    async def list_resources(self, uri: str) -> list[str]:
        """
        List resources matching pattern.
        """
        pattern = uri.replace("*", ".*")
        regex = re.compile(pattern)
        return [key for key in self._store if regex.match(key)]

    def supports_scheme(self, scheme: str) -> bool:
        """
        Check if scheme is supported.
        """
        return scheme == "memory"

    async def set(self, uri: str, value: Any) -> None:
        """
        Set value in memory.
        """
        self._store[uri] = value

    async def delete(self, uri: str) -> None:
        """
        Delete value from memory.
        """
        if uri in self._store:
            del self._store[uri]


__all__ = [
    "ConfigSchemeHandler",
    "InMemoryResourceProvider",
    "MemorySchemeHandler",
]
