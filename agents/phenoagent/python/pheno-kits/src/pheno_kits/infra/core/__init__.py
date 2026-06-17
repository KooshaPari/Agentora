"""Unified resource management primitives for the Pheno SDK.

This module consolidates the lightweight adapter-driven resource manager, the
batch orchestration capabilities that previously lived in
``pheno/infra/resource_coordinator.py`` and the reference-counting cache from
``pheno/infra/resource_reference_cache.py``.  The resulting ``ResourceManager``
exposes a single surface that delivers the features called out in the Phase 0
audit matrix:

* Adapter pattern with pluggable resource backends.
* Asynchronous lifecycle orchestration and health monitoring.
* Batch operations for multi-resource bring-up and teardown.
* Resource reference caching with compatibility heuristics.
* Multi-project isolation with optional shared/global resources.

All public methods include comprehensive docstrings so downstream teams can
rely on the consolidated behaviour without needing to inspect implementation
details.

Module Structure
----------------
- ``resources_models``: Enums and dataclasses (ResourceReuseStrategy, ResourceScope,
  ResourceDependency, ResourceReference)
- ``resources_manager``: Core ResourceManager with lifecycle, caching, and health monitoring
- ``resources_batch``: Batch operations and convenience helpers (request_resources,
  release_resources, manage_resources)
- ``resources_adapter``: Adapter factory utilities
"""

from .resources_adapter import resource_from_dict
from .resources_batch import ResourceManagerBatch, manage_resources
from .resources_models import (
    ResourceDependency,
    ResourceReference,
    ResourceReuseStrategy,
    ResourceScope,
)
from .resources_manager import ResourceManager

__all__ = [
    "ResourceDependency",
    "ResourceManager",
    "ResourceManagerBatch",
    "ResourceReference",
    "ResourceReuseStrategy",
    "ResourceScope",
    "manage_resources",
    "resource_from_dict",
]
