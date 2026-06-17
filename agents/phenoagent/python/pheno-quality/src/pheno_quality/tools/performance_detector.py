"""
Performance anti-pattern detection tool implementation.
"""

import ast
from pathlib import Path
from typing import Any

from ..core import (
    ImpactLevel,
    QualityAnalyzer,
    QualityConfig,
    QualityIssue,
    SeverityLevel,
)
from ..plugins import QualityPlugin
from ..utils import QualityUtils


class PerformanceDetector(QualityAnalyzer):
    """
    Performance anti-pattern detection tool.
    """

    def __init__(self, name: str = "performance_detector", config: QualityConfig | None = None):
        super().__init__(name, config)
        self.patterns = {
            "n_plus_one_query": self._detect_n_plus_one_queries,
            "memory_leak": self._detect_memory_leaks,
            "blocking_calls": self._detect_blocking_calls,
            "inefficient_loops": self._detect_inefficient_loops,
            "excessive_io": self._detect_excessive_io,
        }

    def analyze_file(self, file_path: Path) -> list[QualityIssue]:
        """
        Analyze a single file for performance issues.
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            file_issues = []

            for detector_func in self.patterns.values():
                issues = detector_func(tree, file_path)
                file_issues.extend(issues)

            self.issues.extend(file_issues)
            return file_issues

        except Exception as e:
            error_issue = QualityIssue(
                id=QualityUtils.generate_issue_id("parse_error", str(file_path), 0),
                type="parse_error",
                severity=SeverityLevel.HIGH,
                file=str(file_path),
                line=0,
                column=0,
                message=f"Failed to parse file: {e!s}",
                suggestion="Check file syntax and encoding",
                confidence=1.0,
                impact=ImpactLevel.HIGH,
                tool=self.name,
                category="Parsing",
                tags=["error", "parsing"],
            )
            self.issues.append(error_issue)
            return [error_issue]

    def analyze_directory(self, directory_path: Path) -> list[QualityIssue]:
        """
        Analyze a directory for performance issues.
        """
        all_issues = []

        for file_path in directory_path.rglob("*.py"):
            if self._should_analyze_file(file_path):
                file_issues = self.analyze_file(file_path)
                all_issues.extend(file_issues)

        return all_issues

    def _should_analyze_file(self, file_path: Path) -> bool:
        """
        Check if file should be analyzed.
        """
        exclude_patterns = self.config.filters.get("exclude_patterns", [])
        return not QualityUtils.should_exclude_file(str(file_path), exclude_patterns)

    def _detect_n_plus_one_queries(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Detect N+1 query problems.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                if self._loop_contains_database_queries(node):
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "n_plus_one_query", str(file_path), node.lineno,
                        ),
                        type="n_plus_one_query",
                        severity=SeverityLevel.HIGH,
                        file=str(file_path),
                        line=node.lineno,
                        column=node.col_offset,
                        message="Potential N+1 query problem detected in loop",
                        suggestion="Use eager loading or batch queries to reduce database calls",
                        confidence=0.8,
                        impact=ImpactLevel.HIGH,
                        tool=self.name,
                        category=QualityUtils.categorize_issue("n_plus_one_query", self.name),
                        tags=QualityUtils.generate_tags(
                            "n_plus_one_query", self.name, SeverityLevel.HIGH,
                        ),
                    )
                    issues.append(issue)

        return issues

    def _detect_memory_leaks(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Detect potential memory leaks.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if self._function_creates_large_objects(node):
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "memory_leak", str(file_path), node.lineno,
                        ),
                        type="memory_leak",
                        severity=SeverityLevel.MEDIUM,
                        file=str(file_path),
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Function '{node.name}' may create memory leaks",
                        suggestion="Ensure proper cleanup of large objects and use context managers",
                        confidence=0.6,
                        impact=ImpactLevel.MEDIUM,
                        tool=self.name,
                        category=QualityUtils.categorize_issue("memory_leak", self.name),
                        tags=QualityUtils.generate_tags(
                            "memory_leak", self.name, SeverityLevel.MEDIUM,
                        ),
                    )
                    issues.append(issue)

        return issues

    def _detect_blocking_calls(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Detect blocking I/O calls.
        """
        issues = []

        blocking_functions = ["open", "read", "write", "input", "print", "sleep", "time.sleep"]

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in blocking_functions:
                        issue = QualityIssue(
                            id=QualityUtils.generate_issue_id(
                                "blocking_calls", str(file_path), node.lineno,
                            ),
                            type="blocking_calls",
                            severity=SeverityLevel.MEDIUM,
                            file=str(file_path),
                            line=node.lineno,
                            column=node.col_offset,
                            message=f"Blocking call '{node.func.id}' detected",
                            suggestion="Consider using async/await or threading for non-blocking operations",
                            confidence=0.8,
                            impact=ImpactLevel.MEDIUM,
                            tool=self.name,
                            category=QualityUtils.categorize_issue("blocking_calls", self.name),
                            tags=QualityUtils.generate_tags(
                                "blocking_calls", self.name, SeverityLevel.MEDIUM,
                            ),
                        )
                        issues.append(issue)

        return issues

    def _detect_inefficient_loops(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Detect inefficient loop patterns.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                nested_depth = self._get_nested_loop_depth(node)
                if nested_depth > 3:
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "inefficient_loops", str(file_path), node.lineno,
                        ),
                        type="inefficient_loops",
                        severity=SeverityLevel.HIGH,
                        file=str(file_path),
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Nested loops detected (depth: {nested_depth})",
                        suggestion="Consider using vectorized operations or breaking into smaller functions",
                        confidence=0.9,
                        impact=ImpactLevel.HIGH,
                        tool=self.name,
                        category=QualityUtils.categorize_issue("inefficient_loops", self.name),
                        tags=QualityUtils.generate_tags(
                            "inefficient_loops", self.name, SeverityLevel.HIGH,
                        ),
                    )
                    issues.append(issue)

        return issues

    def _detect_excessive_io(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Detect excessive I/O operations.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                io_count = self._count_io_operations(node)
                if io_count > 5:
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "excessive_io", str(file_path), node.lineno,
                        ),
                        type="excessive_io",
                        severity=SeverityLevel.MEDIUM,
                        file=str(file_path),
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Function '{node.name}' has {io_count} I/O operations",
                        suggestion="Batch I/O operations or use buffering to reduce system calls",
                        confidence=0.7,
                        impact=ImpactLevel.MEDIUM,
                        tool=self.name,
                        category=QualityUtils.categorize_issue("excessive_io", self.name),
                        tags=QualityUtils.generate_tags(
                            "excessive_io", self.name, SeverityLevel.MEDIUM,
                        ),
                    )
                    issues.append(issue)

        return issues

    # Helper methods
    def _loop_contains_database_queries(self, node: ast.For) -> bool:
        """
        Check if loop contains database queries.
        """
        db_keywords = ["query", "execute", "fetch", "select", "insert", "update", "delete"]

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_str = self._get_call_string(child)
                if any(keyword in call_str.lower() for keyword in db_keywords):
                    return True
        return False

    def _function_creates_large_objects(self, node: ast.FunctionDef) -> bool:
        """
        Check if function creates large objects.
        """
        large_object_patterns = ["[]", "{}", "set()", "list(", "dict(", "tuple("]

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_str = self._get_call_string(child)
                if any(pattern in call_str for pattern in large_object_patterns):
                    if self._is_in_loop(child):
                        return True
        return False

    def _get_nested_loop_depth(self, node: ast.For) -> int:
        """
        Get the depth of nested loops.
        """
        depth = 1
        for child in ast.walk(node):
            if isinstance(child, ast.For) and child != node:
                depth += 1
        return depth

    def _count_io_operations(self, node: ast.FunctionDef) -> int:
        """
        Count I/O operations in function.
        """
        io_operations = ["open", "read", "write", "close", "input", "print"]
        count = 0

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_str = self._get_call_string(child)
                if any(op in call_str.lower() for op in io_operations):
                    count += 1

        return count

    def _get_call_string(self, node: ast.Call) -> str:
        """
        Get string representation of a function call.
        """
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            return f"{self._get_attr_string(node.func.value)}.{node.func.attr}"
        return "unknown"

    def _get_attr_string(self, node) -> str:
        """
        Get string representation of an attribute.
        """
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{self._get_attr_string(node.value)}.{node.attr}"
        return "unknown"

    def _is_in_loop(self, node) -> bool:
        """
        Check if node is inside a loop.
        """
        current = node
        while hasattr(current, "parent"):
            current = current.parent
            if isinstance(current, (ast.For, ast.While)):
                return True
        return False


class PerformanceDetectorPlugin(QualityPlugin):
    """
    Plugin for performance detection tool.
    """

    @property
    def name(self) -> str:
        return "performance_detector"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Performance anti-pattern detection for memory leaks, blocking calls, and inefficient algorithms"

    @property
    def supported_extensions(self) -> list[str]:
        return [".py"]

    def create_analyzer(self, config: QualityConfig | None = None) -> QualityAnalyzer:
        return PerformanceDetector(config=config)

    def get_default_config(self) -> dict[str, Any]:
        return {
            "enabled_tools": ["performance_detector"],
            "thresholds": {
                "max_loop_iterations": 1000,
                "max_nested_loops": 3,
                "max_io_operations": 5,
            },
            "filters": {"exclude_patterns": ["__pycache__", "*.pyc", ".git", "node_modules"]},
        }
