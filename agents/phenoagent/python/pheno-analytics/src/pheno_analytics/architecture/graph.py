"""
Dependency graph analysis and cycle detection.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import ArchitectureDetectorConfig
    from .models import DependencyGraph


def build_dependency_graph(
    root_path: Path,
    config: ArchitectureDetectorConfig,
    should_analyze_file: callable,
) -> DependencyGraph:
    """
    Build dependency graph from imports.
    """
    from .models import DependencyGraph

    nodes: set[str] = set()
    edges: dict[str, set[str]] = {}

    for file_path in root_path.rglob("*.py"):
        if should_analyze_file(file_path, config):
            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()

                tree = ast.parse(content)
                module_name = str(file_path.relative_to(root_path).with_suffix(""))
                nodes.add(module_name)

                if module_name not in edges:
                    edges[module_name] = set()

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

            except Exception:
                pass

    cycles = detect_cycles(nodes, edges) if config.detect_cycles else []
    complexity_score = calculate_complexity_score(nodes, edges)

    return DependencyGraph(
        nodes=nodes,
        edges=edges,
        cycles=cycles,
        complexity_score=complexity_score,
    )


def detect_cycles(nodes: set[str], edges: dict[str, set[str]]) -> list[list[str]]:
    """
    Detect cycles in the dependency graph using DFS.
    """
    cycles: list[list[str]] = []
    visited = set()
    rec_stack = set()

    def dfs(node: str, path: list[str]) -> None:
        if node in rec_stack:
            cycle_start = path.index(node)
            cycles.append([*path[cycle_start:], node])
            return

        if node in visited:
            return

        visited.add(node)
        rec_stack.add(node)

        for neighbor in edges.get(node, set()):
            if neighbor in nodes:
                dfs(neighbor, [*path, node])

        rec_stack.remove(node)

    for node in nodes:
        if node not in visited:
            dfs(node, [])

    return cycles


def calculate_complexity_score(nodes: set[str], edges: dict[str, set[str]]) -> float:
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
