"""Pheno Analytics Architecture Module.

This module provides comprehensive architecture detection and pattern analysis capabilities.
It consolidates generic patterns that can be used across all projects in the Pheno ecosystem.

Key Features:
- Generic pattern detection framework
- Extensible pattern library
- Architecture pattern validation
- Design pattern detection
- Code quality analysis
- Custom pattern registration
"""

from .detector import ArchitectureDetector, ArchitectureDetectorConfig
from .extensions import CustomPatternDetector, PatternExtension
from .models import (
    ArchitectureMetrics,
    ArchitecturePattern,
    ArchitectureReport,
    DependencyGraph,
    DesignPattern,
    LayerStructure,
    PatternMatch,
)
from .patterns import DesignPatternDetector, PatternDetector, PatternRegistry
from .validator import ArchitectureValidator, ArchitectureValidatorConfig

__all__ = [
    # Core detectors
    "ArchitectureDetector",
    "ArchitectureDetectorConfig",
    "ArchitectureMetrics",
    "ArchitecturePattern",
    # Models
    "ArchitectureReport",
    "ArchitectureValidator",
    "ArchitectureValidatorConfig",
    "CustomPatternDetector",
    "DependencyGraph",
    "DesignPattern",
    "DesignPatternDetector",
    "LayerStructure",
    "PatternDetector",
    "PatternExtension",
    "PatternMatch",
    # Pattern management
    "PatternRegistry",
]

__version__ = "1.0.0"
