"""
Core architecture detection functionality.
"""

from __future__ import annotations

import ast
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pheno.logging.core.logger import get_logger

from .models import (
    ArchitectureMetrics,
    ArchitecturePattern,
    ArchitectureReport,
    ArchitectureType,
    DependencyGraph,
    DesignPattern,
    DesignPatternType,
    LayerStructure,
    LayerType,
    PatternMatch,
)

if TYPE_CHECKING:
    from pathlib import Path

logger = get_logger("pheno.analytics.architecture.detector")


@dataclass(slots=True)
class ArchitectureDetectorConfig:
    """
    Configuration for architecture detection.
    """

    skip_directories: list[str] = None
    skip_files: list[str] = None
    min_confidence: float = 0.3
    max_depth: int = 10
    include_hidden: bool = False
    analyze_dependencies: bool = True
    detect_cycles: bool = True

    def __post_init__(self):
        if self.skip_directories is None:
            self.skip_directories = [
                ".git",
                "__pycache__",
                "node_modules",
                ".venv",
                "venv",
                "dist",
                "build",
                ".pytest_cache",
                ".mypy_cache",
                ".tox",
                "htmlcov",
                "coverage",
                ".coverage",
                "site-packages",
            ]
        if self.skip_files is None:
            self.skip_files = ["*.pyc", "*.pyo", "*.pyd", "*.so", "*.dll"]


class ArchitectureDetector:
    """
    Advanced architecture pattern detector with extensible pattern library.
    """

    def __init__(self, config: ArchitectureDetectorConfig | None = None):
        self.config = config or ArchitectureDetectorConfig()
        self._pattern_registry: dict[str, ArchitecturePattern] = {}
        self._design_pattern_registry: dict[str, DesignPattern] = {}
        self._custom_detectors: list[Any] = []

        # Initialize built-in patterns
        self._initialize_builtin_patterns()

    def _initialize_builtin_patterns(self) -> None:
        """
        Initialize built-in architectural patterns.
        """

        # Architectural patterns
        patterns = [
            ArchitecturePattern(
                name="hexagonal",
                pattern_type=ArchitectureType.HEXAGONAL,
                description="Hexagonal Architecture (Ports and Adapters)",
                indicators=["domain", "adapters", "ports", "infrastructure", "application"],
                required_layers=[LayerType.DOMAIN, LayerType.PORTS, LayerType.ADAPTERS],
                optional_layers=[LayerType.APPLICATION, LayerType.INFRASTRUCTURE],
                confidence_threshold=0.4,
            ),
            ArchitecturePattern(
                name="clean",
                pattern_type=ArchitectureType.CLEAN,
                description="Clean Architecture",
                indicators=[
                    "domain",
                    "application",
                    "infrastructure",
                    "presentation",
                    "entities",
                    "use_cases",
                ],
                required_layers=[LayerType.DOMAIN, LayerType.APPLICATION, LayerType.INFRASTRUCTURE],
                optional_layers=[LayerType.PRESENTATION],
                confidence_threshold=0.3,
            ),
            ArchitecturePattern(
                name="layered",
                pattern_type=ArchitectureType.LAYERED,
                description="Layered Architecture",
                indicators=[
                    "presentation",
                    "business",
                    "data",
                    "persistence",
                    "service",
                    "controller",
                ],
                required_layers=[
                    LayerType.PRESENTATION,
                    LayerType.APPLICATION,
                    LayerType.INFRASTRUCTURE,
                ],
                confidence_threshold=0.3,
            ),
            ArchitecturePattern(
                name="microservices",
                pattern_type=ArchitectureType.MICROSERVICES,
                description="Microservices Architecture",
                indicators=["services", "api", "gateway", "service", "microservice"],
                required_layers=[LayerType.APPLICATION],
                optional_layers=[LayerType.INFRASTRUCTURE, LayerType.PRESENTATION],
                confidence_threshold=0.4,
            ),
            ArchitecturePattern(
                name="mvc",
                pattern_type=ArchitectureType.MVC,
                description="Model-View-Controller",
                indicators=["models", "views", "controllers", "mvc"],
                required_layers=[LayerType.PRESENTATION],
                confidence_threshold=0.5,
            ),
            ArchitecturePattern(
                name="mvvm",
                pattern_type=ArchitectureType.MVVM,
                description="Model-View-ViewModel",
                indicators=["models", "views", "viewmodels", "mvvm"],
                required_layers=[LayerType.PRESENTATION],
                confidence_threshold=0.5,
            ),
        ]

        for pattern in patterns:
            self._pattern_registry[pattern.name] = pattern

        # Design patterns
        design_patterns = [
            DesignPattern(
                name="factory",
                pattern_type=DesignPatternType.CREATIONAL,
                description="Factory Pattern",
                indicators=["factory", "builder", "creator", "manufacturer"],
                confidence_threshold=0.6,
            ),
            DesignPattern(
                name="singleton",
                pattern_type=DesignPatternType.CREATIONAL,
                description="Singleton Pattern",
                indicators=["singleton", "instance", "get_instance"],
                confidence_threshold=0.7,
            ),
            DesignPattern(
                name="adapter",
                pattern_type=DesignPatternType.STRUCTURAL,
                description="Adapter Pattern",
                indicators=["adapter", "wrapper", "translator"],
                confidence_threshold=0.6,
            ),
            DesignPattern(
                name="decorator",
                pattern_type=DesignPatternType.STRUCTURAL,
                description="Decorator Pattern",
                indicators=["decorator", "wrapper", "enhancer"],
                confidence_threshold=0.6,
            ),
            DesignPattern(
                name="observer",
                pattern_type=DesignPatternType.BEHAVIORAL,
                description="Observer Pattern",
                indicators=["observer", "listener", "subscriber", "notifier"],
                confidence_threshold=0.6,
            ),
            DesignPattern(
                name="strategy",
                pattern_type=DesignPatternType.BEHAVIORAL,
                description="Strategy Pattern",
                indicators=["strategy", "algorithm", "policy"],
                confidence_threshold=0.6,
            ),
            DesignPattern(
                name="repository",
                pattern_type=DesignPatternType.ARCHITECTURAL,
                description="Repository Pattern",
                indicators=["repository", "repo", "data_access"],
                confidence_threshold=0.7,
            ),
            DesignPattern(
                name="service",
                pattern_type=DesignPatternType.ARCHITECTURAL,
                description="Service Pattern",
                indicators=["service", "manager", "handler"],
                confidence_threshold=0.5,
            ),
            DesignPattern(
                name="controller",
                pattern_type=DesignPatternType.ARCHITECTURAL,
                description="Controller Pattern",
                indicators=["controller", "handler", "endpoint"],
                confidence_threshold=0.6,
            ),
            DesignPattern(
                name="middleware",
                pattern_type=DesignPatternType.ARCHITECTURAL,
                description="Middleware Pattern",
                indicators=["middleware", "interceptor", "filter"],
                confidence_threshold=0.6,
            ),
        ]

        for pattern in design_patterns:
            self._design_pattern_registry[pattern.name] = pattern

    def detect(self, root_path: Path) -> ArchitectureReport:
        """
        Analyze project directory structure to infer architecture patterns.
        """
        start_time = time.time()

        logger.info(f"Starting architecture analysis for {root_path}")

        # Scan directory structure
        structure = self._scan_directories(root_path)

        # Detect architectural patterns
        arch_patterns, arch_confidence = self._detect_architectural_patterns(structure)

        # Detect design patterns
        design_patterns, design_confidence = self._detect_design_patterns(root_path)

        # Analyze layer structure
        layer_structure = self._analyze_layer_structure(structure)

        # Build dependency graph
        dependency_graph = (
            self._build_dependency_graph(root_path)
            if self.config.analyze_dependencies
            else DependencyGraph(set(), {})
        )

        # Calculate metrics
        metrics = self._calculate_metrics(layer_structure, dependency_graph, arch_patterns)

        # Generate pattern matches
        pattern_matches = self._generate_pattern_matches(root_path, arch_patterns, design_patterns)

        # Generate recommendations
        recommendations = self._generate_recommendations(arch_patterns, layer_structure, metrics)

        # Count analyzed files and lines
        analyzed_files, total_lines = self._count_files_and_lines(root_path)

        analysis_duration = time.time() - start_time

        logger.info(f"Architecture analysis completed in {analysis_duration:.2f}s")

        return ArchitectureReport(
            detected_patterns=arch_patterns,
            design_patterns=design_patterns,
            confidence_scores={**arch_confidence, **design_confidence},
            layer_structure=layer_structure,
            dependency_graph=dependency_graph,
            metrics=metrics,
            pattern_matches=pattern_matches,
            recommendations=recommendations,
            analyzed_files=analyzed_files,
            total_lines=total_lines,
            analysis_duration=analysis_duration,
        )

    def _scan_directories(self, root: Path) -> dict[str, list[str]]:
        """
        Scan directory structure for analysis.
        """
        structure: dict[str, list[str]] = {}
        skip_tokens = set(self.config.skip_directories)

        for item in root.rglob("*"):
            if not item.is_dir():
                continue

            # Skip hidden directories unless explicitly included
            if not self.config.include_hidden and item.name.startswith("."):
                continue

            # Skip configured directories
            if any(token in item.parts for token in skip_tokens):
                continue

            # Limit depth
            depth = len(item.relative_to(root).parts)
            if depth > self.config.max_depth:
                continue

            dir_name = item.name.lower()
            parent = item.parent.name.lower() if item.parent != root else "root"

            structure.setdefault(parent, []).append(dir_name)

        return structure

    def _detect_architectural_patterns(
        self, structure: dict[str, list[str]],
    ) -> tuple[list[ArchitectureType], dict[str, float]]:
        """
        Detect architectural patterns based on directory structure.
        """
        all_dirs = {name for names in structure.values() for name in names}
        detected: list[ArchitectureType] = []
        confidence: dict[str, float] = {}

        for pattern_name, pattern in self._pattern_registry.items():
            matches = sum(
                1
                for indicator in pattern.indicators
                if any(indicator in directory for directory in all_dirs)
            )

            if not pattern.indicators:
                continue

            score = matches / len(pattern.indicators)
            if score >= pattern.confidence_threshold:
                detected.append(pattern.pattern_type)
                confidence[pattern_name] = score

        # If no patterns detected, assume monolithic
        if not detected:
            detected = [ArchitectureType.MONOLITHIC]
            confidence["monolithic"] = 0.8

        return detected, confidence

    def _detect_design_patterns(
        self, root_path: Path,
    ) -> tuple[list[DesignPatternType], dict[str, float]]:
        """
        Detect design patterns in the codebase.
        """
        detected_types: set[DesignPatternType] = set()
        confidence: dict[str, float] = {}

        for file_path in root_path.rglob("*.py"):
            if self._should_analyze_file(file_path):
                try:
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()

                    tree = ast.parse(content)
                    file_patterns = self._analyze_file_for_patterns(tree, file_path)

                    for pattern_name, pattern_confidence in file_patterns.items():
                        if pattern_name in self._design_pattern_registry:
                            pattern = self._design_pattern_registry[pattern_name]
                            if pattern_confidence >= pattern.confidence_threshold:
                                detected_types.add(pattern.pattern_type)
                                confidence[pattern_name] = max(
                                    confidence.get(pattern_name, 0), pattern_confidence,
                                )

                except Exception as e:
                    logger.warning(f"Failed to analyze file {file_path}: {e}")

        return list(detected_types), confidence

    def _analyze_file_for_patterns(self, tree: ast.AST, file_path: Path) -> dict[str, float]:
        """
        Analyze a single file for design patterns.
        """
        patterns: dict[str, float] = {}

        # Collect all names (classes, functions, variables)
        names: set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                names.add(node.name.lower())
            elif isinstance(node, ast.Name):
                names.add(node.id.lower())

        # Check against design patterns
        for pattern_name, pattern in self._design_pattern_registry.items():
            matches = sum(
                1 for indicator in pattern.indicators if any(indicator in name for name in names)
            )

            if matches > 0:
                confidence = min(1.0, matches / len(pattern.indicators))
                patterns[pattern_name] = confidence

        return patterns

    def _analyze_layer_structure(self, structure: dict[str, list[str]]) -> LayerStructure:
        """
        Analyze the layer structure of the codebase.
        """
        layers: dict[LayerType, list[str]] = {layer: [] for layer in LayerType}
        dependencies: dict[LayerType, set[LayerType]] = {layer: set() for layer in LayerType}
        violations: list[tuple[LayerType, LayerType]] = []

        # Map directories to layers
        all_dirs = {name for names in structure.values() for name in names}

        layer_keywords = {
            LayerType.PRESENTATION: [
                "presentation",
                "ui",
                "view",
                "controller",
                "api",
                "endpoint",
                "route",
            ],
            LayerType.APPLICATION: [
                "application",
                "service",
                "use_case",
                "handler",
                "command",
                "query",
            ],
            LayerType.DOMAIN: [
                "domain",
                "entity",
                "model",
                "business",
                "aggregate",
                "value_object",
            ],
            LayerType.INFRASTRUCTURE: [
                "infrastructure",
                "repository",
                "persistence",
                "database",
                "external",
            ],
            LayerType.PORTS: ["ports", "interface", "contract"],
            LayerType.ADAPTERS: ["adapters", "adapter", "implementation"],
        }

        for directory in all_dirs:
            for layer_type, keywords in layer_keywords.items():
                if any(keyword in directory for keyword in keywords):
                    layers[layer_type].append(directory)
                    break

        # Calculate separation score
        total_dirs = sum(len(dirs) for dirs in layers.values())
        separated_dirs = sum(1 for dirs in layers.values() if dirs)
        separation_score = separated_dirs / max(1, len(LayerType)) if total_dirs > 0 else 0.0

        return LayerStructure(
            layers=layers,
            dependencies=dependencies,
            violations=violations,
            separation_score=separation_score,
        )

    def _build_dependency_graph(self, root_path: Path) -> DependencyGraph:
        """
        Build dependency graph from imports.
        """
        nodes: set[str] = set()
        edges: dict[str, set[str]] = {}

        for file_path in root_path.rglob("*.py"):
            if self._should_analyze_file(file_path):
                try:
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()

                    tree = ast.parse(content)
                    module_name = str(file_path.relative_to(root_path).with_suffix(""))
                    nodes.add(module_name)

                    if module_name not in edges:
                        edges[module_name] = set()

                    # Find imports
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                imported_module = alias.name
                                nodes.add(imported_module)
                                edges[module_name].add(imported_module)
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                imported_module = node.module
                                nodes.add(imported_module)
                                edges[module_name].add(imported_module)

                except Exception as e:
                    logger.warning(f"Failed to analyze dependencies in {file_path}: {e}")

        # Detect cycles
        cycles = self._detect_cycles(nodes, edges) if self.config.detect_cycles else []

        # Calculate complexity score
        complexity_score = self._calculate_complexity_score(nodes, edges)

        return DependencyGraph(
            nodes=nodes, edges=edges, cycles=cycles, complexity_score=complexity_score,
        )

    def _detect_cycles(self, nodes: set[str], edges: dict[str, set[str]]) -> list[list[str]]:
        """
        Detect cycles in the dependency graph.
        """
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: list[str]) -> None:
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                cycles.append([*path[cycle_start:], node])
                return

            if node in visited:
                return

            visited.add(node)
            rec_stack.add(node)

            for neighbor in edges.get(node, set()):
                if neighbor in nodes:  # Only consider nodes in our graph
                    dfs(neighbor, [*path, node])

            rec_stack.remove(node)

        for node in nodes:
            if node not in visited:
                dfs(node, [])

        return cycles

    def _calculate_complexity_score(self, nodes: set[str], edges: dict[str, set[str]]) -> float:
        """
        Calculate complexity score for the dependency graph.
        """
        if not nodes:
            return 0.0

        total_edges = sum(len(neighbors) for neighbors in edges.values())
        max_possible_edges = len(nodes) * (len(nodes) - 1)

        if max_possible_edges == 0:
            return 0.0

        return total_edges / max_possible_edges

    def _calculate_metrics(
        self,
        layer_structure: LayerStructure,
        dependency_graph: DependencyGraph,
        arch_patterns: list[ArchitectureType],
    ) -> ArchitectureMetrics:
        """
        Calculate architecture quality metrics.
        """

        # Layer separation score
        layer_separation_score = layer_structure.separation_score

        # Dependency complexity
        dependency_complexity = dependency_graph.complexity_score

        # Pattern coverage
        pattern_coverage = len(arch_patterns) / len(ArchitectureType)

        # Code organization score (based on layer separation and pattern detection)
        code_organization_score = (layer_separation_score + pattern_coverage) / 2

        # Maintainability index (inversely related to complexity)
        maintainability_index = max(0, 1 - dependency_complexity)

        # Testability score (based on layer separation and low coupling)
        testability_score = (layer_separation_score + (1 - dependency_complexity)) / 2

        # Overall score (weighted average)
        overall_score = (
            layer_separation_score * 0.25
            + (1 - dependency_complexity) * 0.25
            + pattern_coverage * 0.2
            + maintainability_index * 0.15
            + testability_score * 0.15
        )

        return ArchitectureMetrics(
            layer_separation_score=layer_separation_score,
            dependency_complexity=dependency_complexity,
            pattern_coverage=pattern_coverage,
            code_organization_score=code_organization_score,
            maintainability_index=maintainability_index,
            testability_score=testability_score,
            overall_score=overall_score,
        )

    def _generate_pattern_matches(
        self,
        root_path: Path,
        arch_patterns: list[ArchitectureType],
        design_patterns: list[DesignPatternType],
    ) -> list[PatternMatch]:
        """
        Generate detailed pattern matches.
        """
        matches = []

        # This is a simplified implementation
        # In a real implementation, you would scan files more thoroughly
        for file_path in root_path.rglob("*.py"):
            if self._should_analyze_file(file_path):
                try:
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()

                    ast.parse(content)

                    # Look for architectural patterns
                    for pattern_type in arch_patterns:
                        if self._file_matches_pattern(file_path, pattern_type):
                            matches.append(
                                PatternMatch(
                                    pattern_name=pattern_type.value,
                                    pattern_type="architectural",
                                    file_path=file_path,
                                    line_number=1,
                                    column=0,
                                    confidence=0.8,
                                    description=f"File matches {pattern_type.value} architecture pattern",
                                    suggestion=f"Consider organizing code according to {pattern_type.value} principles",
                                ),
                            )

                except Exception as e:
                    logger.warning(f"Failed to generate pattern matches for {file_path}: {e}")

        return matches

    def _file_matches_pattern(self, file_path: Path, pattern_type: ArchitectureType) -> bool:
        """
        Check if a file matches a specific architectural pattern.
        """
        path_str = str(file_path).lower()

        pattern_indicators = {
            ArchitectureType.HEXAGONAL: ["domain", "ports", "adapters"],
            ArchitectureType.CLEAN: ["domain", "application", "entities", "use_cases"],
            ArchitectureType.LAYERED: ["presentation", "business", "data"],
            ArchitectureType.MICROSERVICES: ["service", "api", "gateway"],
            ArchitectureType.MVC: ["models", "views", "controllers"],
            ArchitectureType.MVVM: ["models", "views", "viewmodels"],
        }

        indicators = pattern_indicators.get(pattern_type, [])
        return any(indicator in path_str for indicator in indicators)

    def _generate_recommendations(
        self,
        arch_patterns: list[ArchitectureType],
        layer_structure: LayerStructure,
        metrics: ArchitectureMetrics,
    ) -> list[str]:
        """
        Generate architecture improvement recommendations.
        """
        recommendations = []

        # Pattern-specific recommendations
        if ArchitectureType.MONOLITHIC in arch_patterns:
            recommendations.append(
                "Consider adopting a layered architecture (e.g., Clean Architecture or Hexagonal) "
                "to improve maintainability and testability.",
            )

        # Layer separation recommendations
        if layer_structure.separation_score < 0.5:
            recommendations.append(
                "Improve layer separation by grouping code into distinct layers "
                "(e.g., domain, application, infrastructure).",
            )

        # Dependency complexity recommendations
        if metrics.dependency_complexity > 0.7:
            recommendations.append(
                "Reduce dependency complexity by applying dependency inversion principle "
                "and using interfaces/abstractions.",
            )

        # Maintainability recommendations
        if metrics.maintainability_index < 0.5:
            recommendations.append(
                "Improve maintainability by reducing coupling and increasing cohesion "
                "through better architectural patterns.",
            )

        # Testability recommendations
        if metrics.testability_score < 0.5:
            recommendations.append(
                "Improve testability by implementing dependency injection "
                "and separating business logic from infrastructure concerns.",
            )

        if not recommendations:
            recommendations.append(
                "Architecture appears well-organized with clear separation of concerns.",
            )

        return recommendations

    def _count_files_and_lines(self, root_path: Path) -> tuple[int, int]:
        """
        Count analyzed files and total lines of code.
        """
        file_count = 0
        line_count = 0

        for file_path in root_path.rglob("*.py"):
            if self._should_analyze_file(file_path):
                file_count += 1
                try:
                    with open(file_path, encoding="utf-8") as f:
                        line_count += len(f.readlines())
                except Exception:
                    pass

        return file_count, line_count

    def _should_analyze_file(self, file_path: Path) -> bool:
        """
        Check if a file should be analyzed.
        """
        # Skip hidden files unless explicitly included
        if not self.config.include_hidden and file_path.name.startswith("."):
            return False

        # Skip files in excluded directories
        for skip_dir in self.config.skip_directories:
            if skip_dir in file_path.parts:
                return False

        # Skip files with excluded extensions
        for skip_pattern in self.config.skip_files:
            if file_path.match(skip_pattern):
                return False

        return True

    def register_pattern(self, pattern: ArchitecturePattern) -> None:
        """
        Register a custom architectural pattern.
        """
        self._pattern_registry[pattern.name] = pattern
        logger.info(f"Registered custom architectural pattern: {pattern.name}")

    def register_design_pattern(self, pattern: DesignPattern) -> None:
        """
        Register a custom design pattern.
        """
        self._design_pattern_registry[pattern.name] = pattern
        logger.info(f"Registered custom design pattern: {pattern.name}")

    def add_custom_detector(self, detector: Any) -> None:
        """
        Add a custom pattern detector.
        """
        self._custom_detectors.append(detector)
        logger.info(f"Added custom detector: {type(detector).__name__}")
