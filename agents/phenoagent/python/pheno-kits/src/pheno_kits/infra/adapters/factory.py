"""
Resource Factory - Create resources from simple config dictionaries

Provides easy resource creation without needing to know adapter details.
"""

import logging
from typing import Any

from .api import APIAdapter
from .base import ResourceAdapter
from .command import CommandAdapter
from .daemon import SystemDaemonAdapter
from .docker import DockerAdapter


# Cloud provider adapters (lazy import to avoid dependency issues)
def _get_cloud_adapters():
    try:
        from .cloud.neon import NeonAdapter
        from .cloud.supabase import SupabaseAdapter
        from .cloud.vercel import VercelAdapter

        return {"supabase": SupabaseAdapter, "vercel": VercelAdapter, "neon": NeonAdapter}
    except ImportError:
        return {}


logger = logging.getLogger(__name__)


class ResourceFactory:
    """Factory for creating resource adapters from configuration.

    Simplifies resource creation with automatic adapter selection.
    """

    @staticmethod
    def create(name: str, config: dict[str, Any]) -> ResourceAdapter:
        """Create a resource adapter from configuration.

        Args:
            name: Resource name
            config: Configuration dictionary with 'type' field

        Returns:
            Appropriate ResourceAdapter instance

        Raises:
            ValueError: If config is invalid

        Example:
            >>> resource = ResourceFactory.create("postgres", {
            ...     "type": "docker",
            ...     "image": "postgres:16",
            ...     "ports": {5432: 5432},
            ...     "environment": {"POSTGRES_PASSWORD": "secret"}
            ... })
        """
        resource_type = config.get("type")

        if not resource_type:
            raise ValueError("Resource config must include 'type' field")

        if resource_type == "docker":
            return DockerAdapter(name, config)
        if resource_type in ("systemd", "launchd", "daemon"):
            return SystemDaemonAdapter(name, config)
        if resource_type == "command":
            return CommandAdapter(name, config)
        if resource_type == "api":
            return APIAdapter(name, config)
        if resource_type in ("supabase", "vercel", "neon"):
            # Use specialized cloud adapters if available
            cloud_adapters = _get_cloud_adapters()
            adapter_class = cloud_adapters.get(resource_type)
            if adapter_class:
                return adapter_class(name, config)
            logger.warning(
                f"Cloud adapter for {resource_type} not available, falling back to API adapter",
            )
            return APIAdapter(name, config)
        raise ValueError(f"Unknown resource type: {resource_type}")

    @staticmethod
    def create_many(configs: dict[str, dict[str, Any]]) -> dict[str, ResourceAdapter]:
        """Create multiple resources from a config dictionary.

        Args:
            configs: Dict mapping resource names to their configurations

        Returns:
            Dict of ResourceAdapter instances

        Example:
            >>> resources = ResourceFactory.create_many({
            ...     "postgres": {"type": "docker", "image": "postgres:16", ...},
            ...     "redis": {"type": "docker", "image": "redis:7", ...}
            ... })
        """
        return {name: ResourceFactory.create(name, config) for name, config in configs.items()}


def resource_from_dict(name: str, config: dict[str, Any]) -> ResourceAdapter:
    """Convenience function to create resource from dict.

    Args:
        name: Resource name
        config: Resource configuration

    Returns:
        ResourceAdapter instance

    Example:
        >>> pg = resource_from_dict("db", {
        ...     "type": "docker",
        ...     "image": "postgres:16",
        ...     "ports": {5432: 5432},
        ...     "environment": {"POSTGRES_PASSWORD": "pass"},
        ...     "health_check": {"type": "tcp", "port": 5432}
        ... })
    """
    return ResourceFactory.create(name, config)
