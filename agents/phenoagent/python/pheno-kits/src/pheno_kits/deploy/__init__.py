"""
Deploy-Kit: Universal deployment abstraction for cloud platforms and local services.

This kit provides unified interfaces for deploying applications across:
- Vercel (serverless, edge functions)
- Fly.io (containers, global distribution)
- Local processes (development, testing)
- Docker (containerization)

Features:
- Platform-agnostic deployment abstractions
- Local service management with process isolation
- Health check patterns (HTTP, TCP, custom probes)
- Build hook generation
- Environment variable management
- NVMS (Node Version Manager Script) parsing
- Package vendoring utilities
- Deployment validation
- Platform detection and configuration
"""

# Health checks - using the correct paths
from pheno.observability.monitoring.health import HealthCheck, HealthChecker
from pheno.process.components.health_monitor import (
    HealthCheckResult,
    HTTPHealthCheck,
    PortHealthCheck,
)

# Configuration
from .config import DeployConfig, PackageDetector

# Deployment hooks
from .hooks import (
    DeploymentHook,
    HookRegistry,
    PostDeployHook,
    PreDeployHook,
)

# Local deployment management
from .local import LocalProcessConfig, LocalServiceManager, ReadyProbe

# NVMS (Node Version Manager Script)
from .nvms import NVMSParser
from .platforms.fly import FlyClient

# Cloud platform clients
from .platforms.vercel import VercelClient

# Startup utilities
from .startup import StartupConfig, StartupManager

# Utilities
from .utils import (
    BuildHookGenerator,
    DeploymentValidator,
    EnvironmentManager,
    PlatformDetector,
    PlatformInfo,
)

# Vendoring utilities
from .vendor import PackageInfo, PhenoVendor

__version__ = "0.1.0"
__kit_name__ = "deploy"

__all__ = [
    "BuildHookGenerator",
    # Configuration
    "DeployConfig",
    # Deployment hooks
    "DeploymentHook",
    "DeploymentValidator",
    "EnvironmentManager",
    "FlyClient",
    "HTTPHealthCheck",
    # Health checks
    "HealthCheck",
    "HealthCheckResult",
    "HealthChecker",
    "HookRegistry",
    # Local deployment
    "LocalProcessConfig",
    "LocalServiceManager",
    # NVMS
    "NVMSParser",
    "PackageDetector",
    "PackageInfo",
    # Vendoring
    "PhenoVendor",
    # Utilities
    "PlatformDetector",
    "PlatformInfo",
    "PortHealthCheck",
    "PostDeployHook",
    "PreDeployHook",
    "ReadyProbe",
    "StartupConfig",
    # Startup
    "StartupManager",
    # Platform clients
    "VercelClient",
]
