"""
Pheno CI/CD Generation and Synchronization System Comprehensive CI/CD pipeline
generation following hexagonal architecture patterns.
"""

from .adapters import (
    DefaultConfigProvider,
    FileSystemRepository,
    FileSystemSyncProvider,
    InMemoryTemplateProvider,
)
from .core import (
    CICDConfig,
    CICDEvent,
    CICDGenerator,
    CICDPipeline,
    CICDTemplate,
    PipelineStage,
    ProjectType,
)
from .ports import CICDConfigProvider, CICDRepository, CICDSyncProvider
from .quality import QualityCheckConfig, QualityGateIntegrator
from .sync import CICDSynchronizer, SyncResult, SyncStrategy
from .templates import TemplateEngine, TemplateRegistry

__version__ = "1.0.0"
__author__ = "ATOMS-PHENO Team"

__all__ = [
    "CICDConfig",
    "CICDConfigProvider",
    "CICDEvent",
    # Core
    "CICDGenerator",
    "CICDPipeline",
    # Ports
    "CICDRepository",
    "CICDSyncProvider",
    # Sync
    "CICDSynchronizer",
    "CICDTemplate",
    "DefaultConfigProvider",
    # Adapters
    "FileSystemRepository",
    "FileSystemSyncProvider",
    "InMemoryTemplateProvider",
    "PipelineStage",
    # Domain
    "ProjectType",
    "QualityCheckConfig",
    # Quality
    "QualityGateIntegrator",
    "SyncResult",
    "SyncStrategy",
    # Templates
    "TemplateEngine",
    "TemplateRegistry",
]
