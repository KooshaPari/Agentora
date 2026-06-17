from __future__ import annotations

import ast
import asyncio
from typing import TYPE_CHECKING

from pheno.analytics.code.models import DependencyEdge, DependencyGraph, DependencyInfo
from pheno.logging.core.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    from pheno.utilities.cache.base import CacheProtocol

logger = get_logger("pheno.analytics.dependencies")

try:  # pragma: no cover - optional dependency
    from grimp import PackageGraph  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    PackageGraph = None

try:  # pragma: no cover - optional dependency
    import networkx as nx  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    nx = None


async def analyze_dependencies(
    path: Path,
    *,
    package: str | None = None,
    include_internal: bool = True,
    cache: CacheProtocol | None = None,
) -> DependencyGraph:
    """Build a dependency graph using grimp when available, otherwise fall back to AST
    analysis.

    Args:
        path: Path to module/package root or single file.
        package: Optional explicit package name (defaults to directory name).
        include_internal: Whether to include intra-package dependencies.
        cache: Optional cache implementation.
    """
    target = path if path.is_dir() else path.parent
    package_name = package or target.name

    cache_key = None
    if cache is not None:
        cache_key = ("dependencies", str(path.resolve()), package_name, include_internal)
        cached = await cache.get(cache_key)
        if cached is not None:
            logger.debug("cache_hit", path=str(path), component="dependencies")
            return cached

    graph = await asyncio.to_thread(
        _build_graph,
        target,
        package_name,
        include_internal,
    )

    if cache is not None and cache_key is not None:
        await cache.set(cache_key, graph)

    return graph


def _build_graph(target: Path, package_name: str, include_internal: bool) -> DependencyGraph:
    if PackageGraph is None:
        logger.debug("grimp_not_available", package=package_name)
        return _build_graph_via_ast(target, package_name, include_internal)

    graph = PackageGraph()
    try:
        graph.build(
            package_name=package_name,
            include_external_packages=not include_internal,
            include_tests=False,
            additional_module_paths=[str(target)],
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(
            "grimp_failed",
            package=package_name,
            error=str(exc),
        )
        return _build_graph_via_ast(target, package_name, include_internal)

    edges = [
        DependencyEdge(importer=importer, imported=imported, line_no=None)
        for importer, imported in sorted(graph.edges())
    ]
    cycles = [tuple(cycle) for cycle in graph.find_shortest_cycles()]

    metrics = _compute_graph_metrics(edges)
    return DependencyGraph(module=package_name, edges=edges, cycles=cycles, metrics=metrics)


def _build_graph_via_ast(
    target: Path, package_name: str, include_internal: bool,
) -> DependencyGraph:
    edges: list[DependencyEdge] = []
    adjacency: dict[str, set[str]] = {}

    for file_path in target.rglob("*.py"):
        module_name = _module_name(file_path, target)
        with file_path.open("r", encoding="utf-8") as fh:
            try:
                tree = ast.parse(fh.read(), filename=str(file_path))
            except SyntaxError:
                logger.debug("syntax_error_skipped", file=str(file_path))
                continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    _record_edge(
                        importer=module_name,
                        imported=alias.name,
                        line=node.lineno,
                        edges=edges,
                        adjacency=adjacency,
                        include_internal=include_internal,
                        package=package_name,
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module is None:
                    continue
                imported = node.module
                _record_edge(
                    importer=module_name,
                    imported=imported,
                    line=node.lineno,
                    edges=edges,
                    adjacency=adjacency,
                    include_internal=include_internal,
                    package=package_name,
                )

    cycles = _find_cycles(adjacency)
    metrics = _compute_graph_metrics(edges)
    return DependencyGraph(module=package_name, edges=edges, cycles=cycles, metrics=metrics)


def _compute_graph_metrics(edges: list[DependencyEdge]) -> dict[str, float]:
    if nx is None:  # pragma: no cover - optional dependency guard
        return {}

    graph = nx.DiGraph()
    for edge in edges:
        graph.add_edge(edge.importer, edge.imported)

    if graph.number_of_nodes() == 0:
        return {}

    density = nx.density(graph)
    in_degrees = graph.in_degree()
    out_degrees = graph.out_degree()

    metrics = {
        "nodes": float(graph.number_of_nodes()),
        "edges": float(graph.number_of_edges()),
        "density": float(density),
        "avg_in_degree": float(sum(d for _, d in in_degrees) / graph.number_of_nodes()),
        "avg_out_degree": float(sum(d for _, d in out_degrees) / graph.number_of_nodes()),
    }

    try:
        metrics["strongly_connected_components"] = float(
            nx.number_strongly_connected_components(graph),
        )
    except Exception:  # pragma: no cover
        pass

    return metrics


def _record_edge(
    *,
    importer: str,
    imported: str,
    line: int,
    edges: list[DependencyEdge],
    adjacency: dict[str, set[str]],
    include_internal: bool,
    package: str,
) -> None:
    if not include_internal and imported.startswith(f"{package}."):
        return
    adjacency.setdefault(importer, set()).add(imported)
    edges.append(DependencyEdge(importer=importer, imported=imported, line_no=line))


def _find_cycles(adjacency: Mapping[str, set[str]]) -> list[tuple[str, ...]]:
    visited: set[str] = set()
    stack: list[str] = []
    cycles: set[tuple[str, ...]] = set()

    def visit(node: str) -> None:
        if node in stack:
            cycle = tuple(stack[stack.index(node) :])
            cycles.add(cycle)
            return
        if node in visited:
            return
        visited.add(node)
        stack.append(node)
        for neighbour in adjacency.get(node, set()):
            visit(neighbour)
        stack.pop()

    for node in adjacency:
        visit(node)
    return sorted(cycles)


def _module_name(path: Path, root: Path) -> str:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return path.stem
    parts = list(rel.with_suffix("").parts)
    return ".".join(part for part in parts if part != "__init__")


async def analyze_project_dependencies(
    root_path: Path,
    *,
    file_patterns: Sequence[str] | None = None,
    cache: CacheProtocol | None = None,
) -> DependencyInfo:
    """Analyze dependencies for entire project (Morph-compatible API).

    Args:
        root_path: Root directory of project
        file_patterns: File patterns to analyze (default: ["*.py"])
        cache: Optional cache to reuse previous results

    Returns:
        DependencyInfo with complete dependency analysis
    """
    file_patterns = file_patterns or ["*.py"]

    external_packages: set[str] = set()
    internal_modules: dict[str, list[str]] = {}
    imports_by_file: dict[str, list[str]] = {}
    dependency_graph: dict[str, set[str]] = {}

    # Collect all Python files
    python_files = []
    for pattern in file_patterns:
        python_files.extend(root_path.rglob(pattern))

    # Analyze each file
    for file_path in python_files:
        if not file_path.is_file():
            continue

        file_str = str(file_path)

        try:
            imports = await asyncio.to_thread(_extract_imports, file_str)
            imports_by_file[file_str] = imports

            # Categorize imports
            for imp in imports:
                if _is_external_package(imp, root_path):
                    external_packages.add(imp.split(".")[0])
                else:
                    if file_str not in internal_modules:
                        internal_modules[file_str] = []
                    internal_modules[file_str].append(imp)

            # Build dependency graph
            deps = _resolve_dependencies(file_str, imports, root_path)
            if deps:
                dependency_graph[file_str] = set(deps)

        except Exception as e:
            logger.debug("dependency_analysis_failed", file=file_str, error=str(e))
            continue

    # Find circular dependencies
    circular_deps = _find_circular_dependencies(dependency_graph)

    return DependencyInfo(
        external_packages=external_packages,
        internal_modules=internal_modules,
        imports_by_file=imports_by_file,
        dependency_graph=dependency_graph,
        circular_dependencies=circular_deps,
        unused_imports=[],  # TODO: implement unused import detection
    )


def _extract_imports(file_path: str) -> list[str]:
    """
    Extract all import statements from a file.
    """
    imports = []

    try:
        with open(file_path, encoding="utf-8") as f:
            tree = ast.parse(f.read())

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
    except Exception:
        pass

    return imports


def _is_external_package(import_name: str, root_path: Path) -> bool:
    """
    Check if an import is an external package.
    """
    # Common standard library modules
    stdlib_modules = {
        "os",
        "sys",
        "ast",
        "json",
        "pathlib",
        "re",
        "typing",
        "dataclasses",
        "asyncio",
        "collections",
        "itertools",
        "functools",
        "operator",
        "datetime",
        "time",
        "math",
        "random",
        "hashlib",
        "uuid",
    }

    first_part = import_name.split(".", maxsplit=1)[0]

    # Check if it's a standard library module
    if first_part in stdlib_modules:
        return False

    # Check if it's a local module (exists in root_path)
    potential_path = root_path / first_part
    if potential_path.exists():
        return False

    # Otherwise, it's external
    return True


def _resolve_dependencies(file_path: str, imports: list[str], root_path: Path) -> list[str]:
    """
    Resolve imports to actual file paths.
    """
    resolved = []

    for imp in imports:
        if _is_external_package(imp, root_path):
            continue

        # Try to find the corresponding file
        parts = imp.split(".")
        potential_file = root_path / "/".join(parts[:-1]) / f"{parts[-1]}.py"

        if potential_file.exists():
            resolved.append(str(potential_file))
        else:
            # Try as a package
            potential_package = root_path / "/".join(parts) / "__init__.py"
            if potential_package.exists():
                resolved.append(str(potential_package))

    return resolved


def _find_circular_dependencies(dependency_graph: dict[str, set[str]]) -> list[list[str]]:
    """
    Find circular dependencies in the dependency graph.
    """
    cycles = []
    visited = set()
    rec_stack = set()

    def dfs(node: str, path: list[str]) -> None:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in dependency_graph.get(node, set()):
            if neighbor not in visited:
                dfs(neighbor, path.copy())
            elif neighbor in rec_stack:
                # Found a cycle
                cycle_start = path.index(neighbor)
                cycle = [*path[cycle_start:], neighbor]
                if cycle not in cycles:
                    cycles.append(cycle)

        rec_stack.remove(node)

    for node in dependency_graph:
        if node not in visited:
            dfs(node, [])

    return cycles
