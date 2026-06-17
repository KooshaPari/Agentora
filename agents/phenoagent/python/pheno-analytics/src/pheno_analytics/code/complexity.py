from __future__ import annotations

import asyncio
import fnmatch
from pathlib import Path
from statistics import mean
from typing import TYPE_CHECKING

from pheno.analytics.code.models import (
    ComplexityMetrics,
    ComplexityReport,
    FunctionComplexity,
)
from pheno.analytics.exceptions import AnalyticsDependencyError
from pheno.logging.core.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from pheno.utilities.cache.base import CacheProtocol

logger = get_logger("pheno.analytics.complexity")

try:
    from radon.complexity import cc_visit  # type: ignore
    from radon.raw import analyze as raw_analyze  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    cc_visit = None
    raw_analyze = None


INCLUDE_GLOBS_DEFAULT = ("*.py",)


async def analyze_complexity(
    path: Path,
    *,
    include: Sequence[str] | None = None,
    exclude: Sequence[str] | None = None,
    thresholds: Mapping[str, float] | None = None,
    cache: CacheProtocol | None = None,
) -> list[ComplexityReport]:
    """Run cyclomatic complexity analysis using radon.

    Args:
        path: Directory or file to analyze.
        include: Glob patterns to include (defaults to ``*.py``).
        exclude: Glob patterns to exclude.
        thresholds: Optional mapping of symbol name -> threshold for warnings.
        cache: Optional cache to reuse previous results.

    Returns:
        List of ``ComplexityReport`` entries ordered by module name.
    """
    if cc_visit is None:
        raise AnalyticsDependencyError("radon", extra="analytics")

    target_path = path if path.is_dir() else path.parent
    include = include or INCLUDE_GLOBS_DEFAULT
    exclude = exclude or ()

    cache_key = None
    if cache is not None:
        cache_key = (
            "complexity",
            str(path.resolve()),
            tuple(sorted(include)),
            tuple(sorted(exclude)),
        )
        cached = await cache.get(cache_key)
        if cached is not None:
            logger.debug("cache_hit", path=str(path), component="complexity")
            return cached

    files = _collect_files(path, include, exclude)
    logger.debug("analyze_complexity_start", file_count=len(files), component="complexity")

    reports: list[ComplexityReport] = []
    for file_path in files:
        reports.append(
            await asyncio.to_thread(
                _analyze_file,
                file_path=file_path,
                root=target_path,
                thresholds=thresholds or {},
            ),
        )

    reports.sort(key=lambda r: r.module)
    logger.debug("analyze_complexity_complete", file_count=len(reports), component="complexity")

    if cache is not None and cache_key is not None:
        await cache.set(cache_key, reports)

    return reports


def _collect_files(path: Path, include: Sequence[str], exclude: Sequence[str]) -> list[Path]:
    if path.is_file():
        return [path]

    collected: list[Path] = []
    for candidate in path.rglob("*"):
        if not candidate.is_file():
            continue
        if not any(fnmatch.fnmatch(candidate.name, pattern) for pattern in include):
            continue
        if any(fnmatch.fnmatch(candidate.name, pattern) for pattern in exclude):
            continue
        collected.append(candidate)
    return collected


def _analyze_file(
    *,
    file_path: Path,
    root: Path,
    thresholds: Mapping[str, float],
) -> ComplexityReport:
    with file_path.open("r", encoding="utf-8") as fp:
        source = fp.read()

    blocks = cc_visit(source)
    scores: dict[str, float] = {}
    high_complexity_funcs: list[FunctionComplexity] = []

    for block in blocks:
        name = getattr(block, "name", repr(block))
        complexity = float(getattr(block, "complexity", 0.0))
        lineno = getattr(block, "lineno", 0)
        col_offset = getattr(block, "col_offset", 0)

        scores[name] = complexity

        # Track high complexity functions (threshold > 10)
        if complexity > 10:
            high_complexity_funcs.append(
                FunctionComplexity(name=name, complexity=complexity, line=lineno, col=col_offset),
            )

        threshold = thresholds.get(name)
        if threshold is not None and complexity > threshold:
            logger.warning(
                "complexity_threshold_exceeded",
                symbol=name,
                complexity=complexity,
                threshold=threshold,
                filepath=str(file_path),
            )

    # Get raw metrics (LOC, comments, etc.)
    total_lines = 0
    code_lines = 0
    comment_lines = 0
    blank_lines = 0

    if raw_analyze is not None:
        try:
            raw_metrics = raw_analyze(source)
            total_lines = raw_metrics.loc
            code_lines = raw_metrics.lloc
            comment_lines = raw_metrics.comments
            blank_lines = raw_metrics.blank
        except Exception:
            # Fallback to simple counting
            lines = source.split("\n")
            total_lines = len(lines)
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    blank_lines += 1
                elif stripped.startswith("#"):
                    comment_lines += 1
                else:
                    code_lines += 1

    average_cc = mean(scores.values()) if scores else 0.0
    comment_ratio = comment_lines / code_lines if code_lines > 0 else 0.0

    # Calculate maintainability index (simplified)
    maintainability = _calculate_maintainability(code_lines, average_cc, comment_ratio)

    module = _module_name(file_path, root)
    return ComplexityReport(
        module=module,
        filepath=file_path,
        average_cc=average_cc,
        scores=scores,
        total_lines=total_lines,
        code_lines=code_lines,
        comment_lines=comment_lines,
        blank_lines=blank_lines,
        maintainability_index=maintainability,
        comment_ratio=comment_ratio,
        high_complexity_functions=high_complexity_funcs,
    )


def _calculate_maintainability(
    code_lines: int, avg_complexity: float, comment_ratio: float,
) -> float:
    """Calculate maintainability index (simplified version).

    Based on Microsoft's maintainability index formula (simplified):
    MI = max(0, (171 - 5.2 * ln(V) - 0.23 * G - 16.2 * ln(LOC)) * 100 / 171)

    Where:
    - V = Halstead Volume (approximated)
    - G = Cyclomatic Complexity
    - LOC = Lines of Code

    Simplified version for quick calculation.
    """
    import math

    if code_lines == 0:
        return 100.0

    # Simplified calculation
    loc_penalty = 16.2 * math.log(max(1, code_lines))
    complexity_penalty = 0.23 * avg_complexity
    comment_bonus = comment_ratio * 10  # Bonus for comments

    mi = max(0, min(100, 171 - loc_penalty - complexity_penalty + comment_bonus))
    return round(mi, 2)


def _module_name(path: Path, root: Path) -> str:
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path.name
    else:
        rel = rel.with_suffix("")
    parts = list(rel.parts) if isinstance(rel, Path) else rel.split("/")
    return ".".join(part for part in parts if part != "__init__")


async def analyze_project_complexity(
    root_path: Path,
    *,
    file_patterns: Sequence[str] | None = None,
    cache: CacheProtocol | None = None,
) -> ComplexityMetrics:
    """Analyze complexity for entire project (Morph-compatible API).

    Args:
        root_path: Root directory of project
        file_patterns: File patterns to analyze (default: ["*.py"])
        cache: Optional cache to reuse previous results

    Returns:
        ComplexityMetrics with complete analysis
    """
    if cc_visit is None:
        raise AnalyticsDependencyError("radon", extra="analytics")

    file_patterns = file_patterns or ["*.py"]

    # Get all reports
    reports = await analyze_complexity(root_path, include=file_patterns, cache=cache)

    # Aggregate metrics
    total_lines = sum(r.total_lines for r in reports)
    code_lines = sum(r.code_lines for r in reports)
    comment_lines = sum(r.comment_lines for r in reports)
    blank_lines = sum(r.blank_lines for r in reports)

    # Calculate average complexity
    all_complexities = []
    high_complexity_funcs = []

    for report in reports:
        all_complexities.extend(report.scores.values())
        high_complexity_funcs.extend(
            [
                {
                    "name": f.name,
                    "complexity": f.complexity,
                    "line": f.line,
                    "file": str(report.filepath),
                }
                for f in report.high_complexity_functions
            ],
        )

    avg_complexity = mean(all_complexities) if all_complexities else 0.0
    comment_ratio = comment_lines / code_lines if code_lines > 0 else 0.0
    maintainability = _calculate_maintainability(code_lines, avg_complexity, comment_ratio)

    return ComplexityMetrics(
        total_lines=total_lines,
        code_lines=code_lines,
        comment_lines=comment_lines,
        blank_lines=blank_lines,
        cyclomatic_complexity=avg_complexity,
        high_complexity_functions=high_complexity_funcs,
        maintainability_index=maintainability,
        comment_ratio=comment_ratio,
    )
