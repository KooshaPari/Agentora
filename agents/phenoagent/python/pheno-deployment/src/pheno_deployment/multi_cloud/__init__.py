"""
Multi-cloud deployment module - hexagonal architecture for cloud deployments.

This module provides multi-cloud deployment capabilities
following hexagonal architecture principles.

Domain concepts (this module):
- CloudDeployment: Multi-cloud deployment abstraction
- CloudProvider: Individual cloud provider abstraction
- DeploymentStrategy: Multi-cloud strategy
- FailoverConfig: Failover and redundancy configuration

Ports (pheno.ports.multi_cloud):
- CloudProviderPort: Interface for cloud provider implementations
- DeploymentOrchestrator: Interface for multi-cloud orchestration
- FailoverManager: Interface for failover handling

Adapters (multi-cloud-deploy implementations):
- AwsProvider, AzureProvider, GcpProvider → CloudProviderPort implementations
"""

from .multi_cloud_manager import MultiCloudManager
from .types import (
    CloudDeployment,
    CloudProvider,
    CloudRegion,
    DeploymentStrategy,
    FailoverConfig,
)

__all__ = [
    # Domain types
    "CloudDeployment",
    "CloudProvider",
    "CloudRegion",
    "DeploymentStrategy",
    "FailoverConfig",
    # Manager
    "MultiCloudManager",
]
