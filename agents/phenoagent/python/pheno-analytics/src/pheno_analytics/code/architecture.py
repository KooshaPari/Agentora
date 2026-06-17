from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pheno.analytics.code.models import ArchitectureReport
from pheno.logging.core.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from pathlib import Path

logger = get_logger("pheno.analytics.architecture")


@dataclass(slots=True)
class ArchitectureDetectorConfig:
    """
    Configuration for architecture detection.
    """

    skip_directories: Sequence[str] = (
        ".git",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
        "dist",
        "build",
        ".pytest_cache",
        ".mypy_cache",
    )


class ArchitectureDetector:
    """
    Detect high-level architecture patterns using heuristics.
    """

    _PATTERNS: dict[str, Sequence[str]] = {
        "hexagonal": ("domain", "adapters", "ports", "infrastructure"),
        "clean": ("domain", "application", "infrastructure", "presentation"),
        "mvc": ("models", "views", "controllers"),
        "mvvm": ("models", "views", "viewmodels"),
        "layered": ("presentation", "business", "data", "persistence"),
        "microservices": ("services", "api", "gateway"),
    }

    _LAYER_INDICATORS: Sequence[str] = (
        "domain",
        "application",
        "infrastructure",
        "presentation",
        "models",
        "views",
        "controllers",
        "services",
        "repositories",
        "adapters",
        "ports",
        "core",
        "api",
    )

    _PATTERN_INDICATORS: dict[str, Sequence[str]] = {
        "factory": ("factory", "builder"),
        "singleton": ("singleton",),
        "adapter": ("adapter", "wrapper"),
        "decorator": ("decorator",),
        "observer": ("observer", "listener", "subscriber"),
        "strategy": ("strategy",),
        "repository": ("repository", "repo"),
        "service": ("service",),
        "controller": ("controller",),
        "middleware": ("middleware",),
        "proxy": ("proxy",),
        "facade": ("facade",),
    }

    def __init__(self, *, config: ArchitectureDetectorConfig | None = None) -> None:
        self._config = config or ArchitectureDetectorConfig()

    def detect(self, root_path: Path) -> ArchitectureReport:
        """
        Analyze project directory structure to infer architecture patterns.
        """

        structure = self._scan_directories(root_path)
        detected, confidence = self._identify_patterns(structure)

        if not detected:
            detected = ("monolithic",)
            confidence = {"monolithic": 0.8}

        layer_separation = self._has_layer_separation(structure)
        design_patterns = self._detect_design_patterns(root_path)
        recommendations = self._generate_recommendations(detected, structure, layer_separation)

        logger.debug(
            "architecture_detected",
            detected=detected,
            layer_separation=layer_separation,
            recommendation_count=len(recommendations),
        )

        return ArchitectureReport(
            detected_patterns=detected,
            confidence_scores={k: round(v, 2) for k, v in confidence.items()},
            directory_structure=structure,
            layer_separation=layer_separation,
            design_patterns=tuple(design_patterns),
            recommendations=tuple(recommendations),
        )

    def _scan_directories(self, root: Path) -> dict[str, list[str]]:
        structure: dict[str, list[str]] = {}
        skip_tokens = self._config.skip_directories

        for item in root.rglob("*"):
            if not item.is_dir():
                continue

            if any(token in item.parts for token in skip_tokens):
                continue

            dir_name = item.name.lower()
            parent = item.parent.name.lower() if item.parent != root else "root"

            structure.setdefault(parent, []).append(dir_name)

        return structure

    def _identify_patterns(
        self, structure: dict[str, list[str]],
    ) -> tuple[tuple[str, ...], dict[str, float]]:
        all_dirs = {name for names in structure.values() for name in map(str.lower, names)}
        detected: list[str] = []
        confidence: dict[str, float] = {}

        for pattern_name, keywords in self._PATTERNS.items():
            matches = sum(
                1 for keyword in keywords if any(keyword in directory for directory in all_dirs)
            )
            if not keywords:
                continue
            score = matches / len(keywords)
            if score > 0.3:
                detected.append(pattern_name)
                confidence[pattern_name] = score

        return tuple(detected), confidence

    def _has_layer_separation(self, structure: dict[str, list[str]]) -> bool:
        all_dirs = {name for names in structure.values() for name in map(str.lower, names)}
        matches = sum(1 for indicator in self._LAYER_INDICATORS if indicator in all_dirs)
        return matches >= 2

    def _detect_design_patterns(self, root: Path) -> list[str]:
        names: set[str] = set()

        for item in root.rglob("*.py"):
            names.add(item.stem.lower())

        for item in root.rglob("*"):
            if item.is_dir():
                names.add(item.name.lower())

        detected: list[str] = []
        for pattern, indicators in self._PATTERN_INDICATORS.items():
            if any(indicator in name for name in names for indicator in indicators):
                detected.append(pattern)

        return detected

    def _generate_recommendations(
        self,
        detected_patterns: Iterable[str],
        structure: dict[str, list[str]],
        layer_separated: bool,
    ) -> list[str]:
        recommendations: list[str] = []
        detected_set = set(detected_patterns)

        if "monolithic" in detected_set:
            recommendations.append(
                "Consider adopting a layered architecture (e.g., Clean Architecture or Hexagonal) "
                "to improve maintainability and testability.",
            )

        if not layer_separated:
            recommendations.append(
                "Improve layer separation by grouping code into distinct layers "
                "(e.g., domain, application, infrastructure).",
            )

        all_dirs = {name for names in structure.values() for name in map(str.lower, names)}

        if "tests" not in all_dirs and "test" not in all_dirs:
            recommendations.append(
                "Add a dedicated tests/ directory to consolidate automated tests.",
            )

        if "docs" not in all_dirs and "documentation" not in all_dirs:
            recommendations.append(
                "Provide a docs/ directory for architectural and onboarding documentation.",
            )

        if not recommendations:
            recommendations.append(
                "Architecture appears well-organized with clear separation of concerns.",
            )

        return recommendations
