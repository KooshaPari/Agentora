"""Pheno analytics toolkit.

Provides complexity, dependency, and AST analysis utilities that wrap third-party
libraries (radon, grimp, tree-sitter) behind async-friendly helpers with consistent
telemetry integration.
"""

from .ast.adapter import get_adapter as get_ast_adapter
from .ast.parser import (
    CodeEntity,
    JavaScriptParser,
    PythonASTParser,
    get_parser_for_file,
)
from .code.architecture import ArchitectureDetector, ArchitectureDetectorConfig
from .code.complexity import analyze_complexity, analyze_project_complexity
from .code.dependencies import analyze_dependencies, analyze_project_dependencies
from .code.models import (
    ArchitectureReport,
    CodeAnalyticsReport,
    ComplexityMetrics,
    ComplexityReport,
    DependencyEdge,
    DependencyGraph,
    DependencyInfo,
    FunctionComplexity,
)
from .code.service import CodeAnalyticsOptions, analyze_codebase
from .exceptions import AnalyticsDependencyError

__all__ = [
    "AnalyticsDependencyError",
    "ArchitectureDetector",
    "ArchitectureDetectorConfig",
    "ArchitectureReport",
    "CodeAnalyticsOptions",
    "CodeAnalyticsReport",
    "CodeEntity",
    "ComplexityMetrics",
    "ComplexityReport",
    "DependencyEdge",
    "DependencyGraph",
    "DependencyInfo",
    "FunctionComplexity",
    "JavaScriptParser",
    "PythonASTParser",
    "analyze_codebase",
    "analyze_complexity",
    "analyze_dependencies",
    "analyze_project_complexity",
    "analyze_project_dependencies",
    "get_ast_adapter",
    "get_parser_for_file",
]
