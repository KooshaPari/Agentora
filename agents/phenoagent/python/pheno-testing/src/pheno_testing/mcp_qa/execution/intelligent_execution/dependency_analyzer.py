"""Analyzes and respects test dependencies."""

import logging
from collections import defaultdict
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


class DependencyAnalyzer:
    """Analyzes and respects test dependencies."""

    def __init__(self):
        self.dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_graph: Dict[str, Set[str]] = defaultdict(set)

    def add_dependency(self, test_id: str, depends_on: str) -> None:
        """Add a dependency: test_id depends on depends_on."""
        self.dependency_graph[test_id].add(depends_on)
        self.reverse_graph[depends_on].add(test_id)

    def add_dependencies(self, test_id: str, depends_on: List[str]) -> None:
        """Add multiple dependencies for a test."""
        for dep in depends_on:
            self.add_dependency(test_id, dep)

    def get_dependencies(self, test_id: str) -> Set[str]:
        """Get all tests that this test depends on."""
        return self.dependency_graph.get(test_id, set())

    def get_dependents(self, test_id: str) -> Set[str]:
        """Get all tests that depend on this test."""
        return self.reverse_graph.get(test_id, set())

    def topological_sort(self, test_ids: List[str]) -> List[List[str]]:
        """Sort tests respecting dependencies.

        Returns levels where each level can run in parallel.
        """
        in_degree = {test_id: 0 for test_id in test_ids}
        for test_id in test_ids:
            for dep in self.dependency_graph.get(test_id, set()):
                if dep in in_degree:
                    in_degree[test_id] += 1

        levels = []
        current_level = [t for t in test_ids if in_degree[t] == 0]

        while current_level:
            levels.append(current_level)
            next_level = []

            for test_id in current_level:
                for dependent in self.reverse_graph.get(test_id, set()):
                    if dependent in in_degree:
                        in_degree[dependent] -= 1
                        if in_degree[dependent] == 0:
                            next_level.append(dependent)

            current_level = next_level

        scheduled = sum(len(level) for level in levels)
        if scheduled < len(test_ids):
            logger.warning(
                f"Dependency cycle detected: {scheduled}/{len(test_ids)} tests scheduled"
            )

        logger.info(f"Created {len(levels)} dependency levels")
        return levels

    def detect_cycles(self) -> List[List[str]]:
        """Detect dependency cycles in the graph."""
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self.dependency_graph.get(node, set()):
                if neighbor not in visited:
                    dfs(neighbor, path.copy())
                elif neighbor in rec_stack:
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])

            rec_stack.remove(node)

        for node in self.dependency_graph:
            if node not in visited:
                dfs(node, [])

        return cycles
