"""Resource adapter utilities.

Provides helper functions for working with resource adapters, including
factory functions for creating adapters from configuration dictionaries.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..adapters import ResourceAdapter, resource_from_dict as _resource_from_dict


def resource_from_dict(name: str, config: dict[str, Any]) -> ResourceAdapter:
    """Create a resource adapter from a configuration dictionary.

    This is a thin wrapper around the adapter factory function that provides
    a consistent interface for resource-specific adapter creation.

    Args:
        name: Friendly identifier for the resource.
        config: Adapter configuration payload. Must include a ``type`` field
            that identifies which adapter kind to instantiate.

    Returns:
        An instantiated :class:`ResourceAdapter` configured according to
        the provided ``config`` dictionary.
    """
    return _resource_from_dict(name, config)
