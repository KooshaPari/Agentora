"""
Architecture detection models and data structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


class ArchitectureType(Enum):
    """
    Types of architectural patterns.
    """

    HEXAGONAL = "hexagonal"
    CLEAN = "clean"
    LAYERED = "layered"
    MICROSERVICES = "microservices"
    MONOLITHIC = "monolithic"
    MVC = "mvc"
    MVVM = "mvvm"
    EVENT_DRIVEN = "event_driven"
    CQRS = "cqrs"
    SAGA = "saga"


class DesignPatternType(Enum):
    """
    Types of design patterns.
    """

    CREATIONAL = "creational"
    STRUCTURAL = "structural"
    BEHAVIORAL = "behavioral"
    ARCHITECTURAL = "architectural"


class LayerType(Enum):
    """
    Types of architectural layers.
    """

    PRESENTATION = "presentation"
    APPLICATION = "application"
    DOMAIN = "domain"
    INFRASTRUCTURE = "infrastructure"
    PORTS = "ports"
    ADAPTERS = "adapters"


class SeverityLevel(Enum):
    """
    Severity levels for issues.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(slots=True)
class PatternMatch:
    """
    Represents a pattern match found in the codebase.
    """

    pattern_name: str
    pattern_type: str
    file_path: Path
    line_number: int
    column: int
    confidence: float
    description: str
    suggestion: str | None = None
    severity: SeverityLevel = SeverityLevel.MEDIUM
    tags: set[str] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ArchitecturePattern:
    """
    Represents an architectural pattern definition.
    """

    name: str
    pattern_type: ArchitectureType
    description: str
    indicators: list[str]
    required_layers: list[LayerType]
    optional_layers: list[LayerType] = field(default_factory=list)
    confidence_threshold: float = 0.3
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DesignPattern:
    """
    Represents a design pattern definition.
    """

    name: str
    pattern_type: DesignPatternType
    description: str
    indicators: list[str]
    confidence_threshold: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LayerStructure:
    """
    Represents the layer structure of a codebase.
    """

    layers: dict[LayerType, list[str]]
    dependencies: dict[LayerType, set[LayerType]]
    violations: list[tuple[LayerType, LayerType]] = field(default_factory=list)
    separation_score: float = 0.0


@dataclass(slots=True)
class DependencyGraph:
    """
    Represents the dependency graph of a codebase.
    """

    nodes: set[str]
    edges: dict[str, set[str]]
    cycles: list[list[str]] = field(default_factory=list)
    complexity_score: float = 0.0


@dataclass(slots=True)
class ArchitectureMetrics:
    """
    Architecture quality metrics.
    """

    layer_separation_score: float
    dependency_complexity: float
    pattern_coverage: float
    code_organization_score: float
    maintainability_index: float
    testability_score: float
    overall_score: float


@dataclass(slots=True)
class ArchitectureReport:
    """
    Comprehensive architecture analysis report.
    """

    # Detected patterns
    detected_patterns: list[ArchitectureType]
    design_patterns: list[DesignPatternType]
    confidence_scores: dict[str, float]

    # Structure analysis
    layer_structure: LayerStructure
    dependency_graph: DependencyGraph

    # Quality metrics
    metrics: ArchitectureMetrics

    # Pattern matches
    pattern_matches: list[PatternMatch]

    # Recommendations
    recommendations: list[str]

    # Metadata
    analysis_timestamp: datetime = field(default_factory=datetime.now)
    analyzed_files: int = 0
    total_lines: int = 0
    analysis_duration: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """
        Convert report to dictionary for serialization.
        """
        return {
            "detected_patterns": [p.value for p in self.detected_patterns],
            "design_patterns": [p.value for p in self.design_patterns],
            "confidence_scores": self.confidence_scores,
            "layer_structure": {
                "layers": {k.value: v for k, v in self.layer_structure.layers.items()},
                "dependencies": {
                    k.value: [dep.value for dep in v]
                    for k, v in self.layer_structure.dependencies.items()
                },
                "violations": [
                    (from_layer.value, to_layer.value)
                    for from_layer, to_layer in self.layer_structure.violations
                ],
                "separation_score": self.layer_structure.separation_score,
            },
            "dependency_graph": {
                "nodes": list(self.dependency_graph.nodes),
                "edges": {k: list(v) for k, v in self.dependency_graph.edges.items()},
                "cycles": self.dependency_graph.cycles,
                "complexity_score": self.dependency_graph.complexity_score,
            },
            "metrics": {
                "layer_separation_score": self.metrics.layer_separation_score,
                "dependency_complexity": self.metrics.dependency_complexity,
                "pattern_coverage": self.metrics.pattern_coverage,
                "code_organization_score": self.metrics.code_organization_score,
                "maintainability_index": self.metrics.maintainability_index,
                "testability_score": self.metrics.testability_score,
                "overall_score": self.metrics.overall_score,
            },
            "pattern_matches": [
                {
                    "pattern_name": match.pattern_name,
                    "pattern_type": match.pattern_type,
                    "file_path": str(match.file_path),
                    "line_number": match.line_number,
                    "column": match.column,
                    "confidence": match.confidence,
                    "description": match.description,
                    "suggestion": match.suggestion,
                    "severity": match.severity.value,
                    "tags": list(match.tags),
                    "metadata": match.metadata,
                }
                for match in self.pattern_matches
            ],
            "recommendations": self.recommendations,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
            "analyzed_files": self.analyzed_files,
            "total_lines": self.total_lines,
            "analysis_duration": self.analysis_duration,
        }
