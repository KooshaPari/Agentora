from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class FunctionComplexity:
    """
    Complexity metrics for a single function.
    """

    name: str
    complexity: float
    line: int
    col: int = 0


@dataclass(frozen=True, slots=True)
class ComplexityReport:
    """
    Aggregated complexity metrics for a single module or file.
    """

    module: str
    filepath: Path
    average_cc: float
    scores: dict[str, float]
    # Enhanced fields matching Morph
    total_lines: int = 0
    code_lines: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    maintainability_index: float = 0.0
    comment_ratio: float = 0.0
    high_complexity_functions: list[FunctionComplexity] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ComplexityMetrics:
    """
    Complete project-level complexity metrics (Morph-compatible).
    """

    total_lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int
    cyclomatic_complexity: float
    high_complexity_functions: list[dict[str, any]]
    maintainability_index: float
    comment_ratio: float


@dataclass(frozen=True, slots=True)
class DependencyEdge:
    """
    Represents a directed dependency edge.
    """

    importer: str
    imported: str
    line_no: int | None = None


@dataclass(frozen=True, slots=True)
class DependencyGraph:
    """
    Collection of dependency edges and cycles for a module.
    """

    module: str
    edges: list[DependencyEdge]
    cycles: list[tuple[str, ...]]
    metrics: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DependencyInfo:
    """
    Complete project-level dependency information (Morph-compatible).
    """

    external_packages: set[str]
    internal_modules: dict[str, list[str]]
    imports_by_file: dict[str, list[str]]
    dependency_graph: dict[str, set[str]]
    circular_dependencies: list[list[str]]
    unused_imports: list[tuple[str, str, int]] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ArchitectureReport:
    """
    Architecture analysis results for a project.
    """

    detected_patterns: tuple[str, ...]
    confidence_scores: dict[str, float]
    directory_structure: dict[str, list[str]]
    layer_separation: bool
    design_patterns: tuple[str, ...]
    recommendations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CodeAnalyticsReport:
    """
    Unified analytics report combining complexity, dependencies, and architecture.
    """

    root_path: Path
    complexity: ComplexityMetrics
    dependencies: DependencyInfo
    architecture: ArchitectureReport
    insights: tuple[str, ...]
    recommendations: tuple[str, ...]
