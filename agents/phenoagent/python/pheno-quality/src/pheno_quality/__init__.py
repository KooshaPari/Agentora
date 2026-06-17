"""
Pheno Quality Analysis Metaframework Comprehensive code quality analysis and anti-
pattern detection framework.
"""

# Configuration presets
from .config import (
    ATOMS_MCP_CONFIG,
    DEFAULT_CONFIG,
    LENIENT_CONFIG,
    PHENO_SDK_CONFIG,
    STRICT_CONFIG,
    ZEN_MCP_CONFIG,
)
from .core import QualityAnalyzer, QualityConfig, QualityIssue, QualityReport
from .exporters import HTMLExporter, JSONExporter, MarkdownExporter, QualityExporter
from .importers import JSONImporter, QualityImporter
from .plugins import PluginRegistry, QualityPlugin
from .registry import QualityToolRegistry
from .tools.architectural_validator import ArchitecturalValidator
from .tools.atlas_health import AtlasHealthAnalyzer
from .tools.code_smell_detector import CodeSmellDetector
from .tools.integration_gates import IntegrationGates

# Quality analysis tools
from .tools.pattern_detector import PatternDetector
from .tools.performance_detector import PerformanceDetector
from .tools.security_scanner import SecurityScanner
from .utils import ImpactLevel, QualityUtils, SeverityLevel

__version__ = "1.0.0"
__author__ = "ATOMS-PHENO Team"

__all__ = [
    "ATOMS_MCP_CONFIG",
    # Config presets
    "DEFAULT_CONFIG",
    "LENIENT_CONFIG",
    "PHENO_SDK_CONFIG",
    "STRICT_CONFIG",
    "ZEN_MCP_CONFIG",
    "ArchitecturalValidator",
    "AtlasHealthAnalyzer",
    "CodeSmellDetector",
    "HTMLExporter",
    "ImpactLevel",
    "IntegrationGates",
    "JSONExporter",
    "JSONImporter",
    "MarkdownExporter",
    # Tools
    "PatternDetector",
    "PerformanceDetector",
    "PluginRegistry",
    # Core classes
    "QualityAnalyzer",
    "QualityConfig",
    # Export/Import
    "QualityExporter",
    "QualityImporter",
    "QualityIssue",
    # Plugin system
    "QualityPlugin",
    "QualityReport",
    # Registry
    "QualityToolRegistry",
    # Utils
    "QualityUtils",
    "SecurityScanner",
    "SeverityLevel",
]
