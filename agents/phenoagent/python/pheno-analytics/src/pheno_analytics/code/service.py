from __future__ import annotations

import asyncio
from dataclasses import dataclass
from time import perf_counter
from typing import TYPE_CHECKING

from pheno.analytics.code.architecture import (
    ArchitectureDetector,
    ArchitectureDetectorConfig,
)
from pheno.analytics.code.complexity import analyze_project_complexity
from pheno.analytics.code.dependencies import analyze_project_dependencies
from pheno.analytics.code.models import (
    ArchitectureReport,
    CodeAnalyticsReport,
    ComplexityMetrics,
    DependencyInfo,
)
from pheno.logging.core.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from pheno.utilities.cache.base import CacheProtocol

logger = get_logger("pheno.analytics.code.service")


@dataclass(slots=True)
class CodeAnalyticsOptions:
    """
    Options controlling code analytics execution.
    """

    include_patterns: Sequence[str] | None = None
    exclude_patterns: Sequence[str] | None = None
    analyze_dependencies: bool = True
    analyze_complexity: bool = True
    analyze_architecture: bool = True
    architecture_skip: Sequence[str] | None = None


async def analyze_codebase(
    root_path: Path,
    *,
    options: CodeAnalyticsOptions | None = None,
    cache: CacheProtocol | None = None,
) -> CodeAnalyticsReport:
    """Run code analytics (complexity, dependencies, architecture) for a project.

    Args:
        root_path: Project directory to analyze.
        options: Optional execution options to enable/disable analyzers.
        cache: Optional cache shared between analyzers.

    Returns:
        ``CodeAnalyticsReport`` combining all analysis outputs.
    """
    root_path = root_path.resolve()
    opts = options or CodeAnalyticsOptions()

    start = perf_counter()

    complexity_task: asyncio.Task[ComplexityMetrics] | None = None
    dependencies_task: asyncio.Task[DependencyInfo] | None = None
    architecture_report: ArchitectureReport | None = None

    include_patterns = opts.include_patterns or ("*.py",)
    tuple(opts.exclude_patterns or ())

    if opts.analyze_complexity:
        complexity_task = asyncio.create_task(
            analyze_project_complexity(
                root_path,
                file_patterns=include_patterns,
                cache=cache,
            ),
        )

    if opts.analyze_dependencies:
        dependencies_task = asyncio.create_task(
            analyze_project_dependencies(
                root_path,
                file_patterns=include_patterns,
            ),
        )

    if opts.analyze_architecture:
        detector = ArchitectureDetector(
            config=ArchitectureDetectorConfig(skip_directories=opts.architecture_skip or ()),
        )
        architecture_report = await asyncio.to_thread(detector.detect, root_path)
    else:
        architecture_report = ArchitectureReport(
            detected_patterns=("disabled",),
            confidence_scores={},
            directory_structure={},
            layer_separation=False,
            design_patterns=(),
            recommendations=("Architecture analysis disabled",),
        )

    complexity_metrics = (
        await complexity_task if complexity_task is not None else _empty_complexity_metrics()
    )
    dependency_info = (
        await dependencies_task if dependencies_task is not None else _empty_dependency_info()
    )

    insights = _generate_insights(complexity_metrics, dependency_info, architecture_report)
    recommendations = tuple(architecture_report.recommendations)

    duration_ms = (perf_counter() - start) * 1000
    logger.debug(
        "code_analytics_complete",
        root=str(root_path),
        complexity=opts.analyze_complexity,
        dependencies=opts.analyze_dependencies,
        architecture=opts.analyze_architecture,
        duration_ms=round(duration_ms, 2),
    )

    return CodeAnalyticsReport(
        root_path=root_path,
        complexity=complexity_metrics,
        dependencies=dependency_info,
        architecture=architecture_report,
        insights=insights,
        recommendations=recommendations,
    )


def _generate_insights(
    complexity: ComplexityMetrics,
    dependencies: DependencyInfo,
    architecture: ArchitectureReport,
) -> tuple[str, ...]:
    insights: list[str] = []

    # Complexity-based insights
    avg_complexity = complexity.cyclomatic_complexity
    if avg_complexity <= 5:
        insights.append("Average cyclomatic complexity is low; codebase is easy to understand.")
    elif avg_complexity <= 10:
        insights.append("Average complexity is moderate; monitor high-complexity hotspots.")
    else:
        insights.append(
            "High average cyclomatic complexity detected; consider refactoring complex functions.",
        )

    if complexity.high_complexity_functions:
        insights.append(
            f"{len(complexity.high_complexity_functions)} functions exceed the recommended complexity threshold.",
        )

    if complexity.comment_ratio < 0.1:
        insights.append("Comment ratio is low; add more documentation to complex modules.")

    # Dependency-based insights
    if dependencies.circular_dependencies:
        insights.append(
            f"Circular dependencies detected ({len(dependencies.circular_dependencies)} cycles); "
            "consider breaking them to improve maintainability.",
        )
    else:
        insights.append("No circular dependencies detected.")

    if dependencies.external_packages:
        insights.append(
            f"Project depends on {len(dependencies.external_packages)} external packages "
            f"({', '.join(sorted(dependencies.external_packages)[:5])}"
            f"{'...' if len(dependencies.external_packages) > 5 else ''}).",
        )

    # Architecture insights
    patterns = architecture.detected_patterns
    if patterns and "monolithic" not in patterns:
        insights.append(f"Detected architecture patterns: {', '.join(patterns)}.")
    else:
        insights.append("Project appears monolithic; consider introducing layered boundaries.")

    if architecture.layer_separation:
        insights.append("Directory structure suggests clear separation between application layers.")

    if architecture.design_patterns:
        insights.append(
            f"Detected design pattern indicators: {', '.join(sorted(architecture.design_patterns))}.",
        )

    return tuple(dict.fromkeys(insights))  # Preserve order, remove duplicates


def _empty_complexity_metrics() -> ComplexityMetrics:
    return ComplexityMetrics(
        total_lines=0,
        code_lines=0,
        comment_lines=0,
        blank_lines=0,
        cyclomatic_complexity=0.0,
        high_complexity_functions=[],
        maintainability_index=100.0,
        comment_ratio=0.0,
    )


def _empty_dependency_info() -> DependencyInfo:
    return DependencyInfo(
        external_packages=set(),
        internal_modules={},
        imports_by_file={},
        dependency_graph={},
        circular_dependencies=[],
        unused_imports=[],
    )
