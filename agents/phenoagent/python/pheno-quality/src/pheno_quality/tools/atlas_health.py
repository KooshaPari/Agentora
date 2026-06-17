"""
Atlas health analysis tool implementation.
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


class AtlasHealthAnalyzer(QualityAnalyzer):
    """
    Atlas health analysis tool.
    """

    def __init__(self, name: str = "atlas_health", config: QualityConfig | None = None):
        super().__init__(name, config)
        self.patterns = {
            "coverage_analysis": self._analyze_coverage,
            "complexity_analysis": self._analyze_complexity,
            "duplication_analysis": self._analyze_duplication,
            "dead_code_detection": self._detect_dead_code,
            "security_analysis": self._analyze_security,
            "performance_analysis": self._analyze_performance,
            "documentation_analysis": self._analyze_documentation,
        }

    def analyze_file(self, file_path: Path) -> list[QualityIssue]:
        """
        Analyze a single file for atlas health.
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            file_issues = []

            for analyzer_func in self.patterns.values():
                issues = analyzer_func(tree, file_path)
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
        Analyze a directory for atlas health.
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

    def _analyze_coverage(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Analyze test coverage.
        """
        issues = []

        # Simple coverage analysis - look for test files
        if "test" in str(file_path).lower():
            # This is a test file, check if it has proper structure
            test_functions = [
                node
                for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
            ]

            if not test_functions:
                issue = QualityIssue(
                    id=QualityUtils.generate_issue_id("coverage_analysis", str(file_path), 0),
                    type="coverage_analysis",
                    severity=SeverityLevel.MEDIUM,
                    file=str(file_path),
                    line=0,
                    column=0,
                    message="Test file has no test functions",
                    suggestion="Add test functions that start with 'test_'",
                    confidence=0.8,
                    impact=ImpactLevel.MEDIUM,
                    tool=self.name,
                    category=QualityUtils.categorize_issue("coverage_analysis", self.name),
                    tags=QualityUtils.generate_tags(
                        "coverage_analysis", self.name, SeverityLevel.MEDIUM,
                    ),
                )
                issues.append(issue)

        return issues

    def _analyze_complexity(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Analyze code complexity.
        """
        issues = []
        threshold = self.config.thresholds.get("cyclomatic_complexity", 10)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                complexity = self._calculate_cyclomatic_complexity(node)
                if complexity > threshold:
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "complexity_analysis", str(file_path), node.lineno,
                        ),
                        type="complexity_analysis",
                        severity=SeverityLevel.HIGH,
                        file=str(file_path),
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Function '{node.name}' has complexity {complexity} (threshold: {threshold})",
                        suggestion="Consider refactoring to reduce complexity",
                        confidence=0.8,
                        impact=ImpactLevel.HIGH,
                        tool=self.name,
                        category=QualityUtils.categorize_issue("complexity_analysis", self.name),
                        tags=QualityUtils.generate_tags(
                            "complexity_analysis", self.name, SeverityLevel.HIGH,
                        ),
                    )
                    issues.append(issue)

        return issues

    def _analyze_duplication(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Analyze code duplication.
        """
        issues = []

        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

        for i, func1 in enumerate(functions):
            for func2 in functions[i + 1 :]:
                if self._functions_similar(func1, func2):
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "duplication_analysis", str(file_path), func1.lineno,
                        ),
                        type="duplication_analysis",
                        severity=SeverityLevel.MEDIUM,
                        file=str(file_path),
                        line=func1.lineno,
                        column=func1.col_offset,
                        message=f"Functions '{func1.name}' and '{func2.name}' may be duplicates",
                        suggestion="Consider extracting common code into a shared function",
                        confidence=0.6,
                        impact=ImpactLevel.MEDIUM,
                        tool=self.name,
                        category=QualityUtils.categorize_issue("duplication_analysis", self.name),
                        tags=QualityUtils.generate_tags(
                            "duplication_analysis", self.name, SeverityLevel.MEDIUM,
                        ),
                    )
                    issues.append(issue)

        return issues

    def _detect_dead_code(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Detect dead code.
        """
        issues = []

        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        {func.name for func in functions}

        calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.append(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.append(node.func.attr)

        for func in functions:
            if func.name not in calls and not func.name.startswith("_"):
                issue = QualityIssue(
                    id=QualityUtils.generate_issue_id(
                        "dead_code_detection", str(file_path), func.lineno,
                    ),
                    type="dead_code_detection",
                    severity=SeverityLevel.LOW,
                    file=str(file_path),
                    line=func.lineno,
                    column=func.col_offset,
                    message=f"Function '{func.name}' appears to be unused",
                    suggestion="Consider removing unused code or adding tests",
                    confidence=0.5,
                    impact=ImpactLevel.LOW,
                    tool=self.name,
                    category=QualityUtils.categorize_issue("dead_code_detection", self.name),
                    tags=QualityUtils.generate_tags(
                        "dead_code_detection", self.name, SeverityLevel.LOW,
                    ),
                )
                issues.append(issue)

        return issues

    def _analyze_security(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Analyze security issues.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id.lower() in ["eval", "exec", "compile"]:
                        issue = QualityIssue(
                            id=QualityUtils.generate_issue_id(
                                "security_analysis", str(file_path), node.lineno,
                            ),
                            type="security_analysis",
                            severity=SeverityLevel.HIGH,
                            file=str(file_path),
                            line=node.lineno,
                            column=node.col_offset,
                            message=f"Potentially dangerous function '{node.func.id}' used",
                            suggestion="Avoid using eval, exec, or compile with user input",
                            confidence=0.9,
                            impact=ImpactLevel.HIGH,
                            tool=self.name,
                            category=QualityUtils.categorize_issue("security_analysis", self.name),
                            tags=QualityUtils.generate_tags(
                                "security_analysis", self.name, SeverityLevel.HIGH,
                            ),
                        )
                        issues.append(issue)

        return issues

    def _analyze_performance(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Analyze performance issues.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                nested_depth = self._get_nested_loop_depth(node)
                if nested_depth > 3:
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "performance_analysis", str(file_path), node.lineno,
                        ),
                        type="performance_analysis",
                        severity=SeverityLevel.MEDIUM,
                        file=str(file_path),
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Nested loops detected (depth: {nested_depth})",
                        suggestion="Consider optimizing nested loops or using vectorized operations",
                        confidence=0.7,
                        impact=ImpactLevel.MEDIUM,
                        tool=self.name,
                        category=QualityUtils.categorize_issue("performance_analysis", self.name),
                        tags=QualityUtils.generate_tags(
                            "performance_analysis", self.name, SeverityLevel.MEDIUM,
                        ),
                    )
                    issues.append(issue)

        return issues

    def _analyze_documentation(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Analyze documentation coverage.
        """
        issues = []

        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

        for func in functions:
            if not func.docstring and not func.name.startswith("_"):
                issue = QualityIssue(
                    id=QualityUtils.generate_issue_id(
                        "documentation_analysis", str(file_path), func.lineno,
                    ),
                    type="documentation_analysis",
                    severity=SeverityLevel.LOW,
                    file=str(file_path),
                    line=func.lineno,
                    column=func.col_offset,
                    message=f"Function '{func.name}' lacks documentation",
                    suggestion="Add docstring to document function purpose and parameters",
                    confidence=0.8,
                    impact=ImpactLevel.LOW,
                    tool=self.name,
                    category=QualityUtils.categorize_issue("documentation_analysis", self.name),
                    tags=QualityUtils.generate_tags(
                        "documentation_analysis", self.name, SeverityLevel.LOW,
                    ),
                )
                issues.append(issue)

        return issues

    # Helper methods
    def _calculate_cyclomatic_complexity(self, node: ast.FunctionDef) -> int:
        """
        Calculate cyclomatic complexity of a function.
        """
        complexity = 1

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1

        return complexity

    def _functions_similar(self, func1: ast.FunctionDef, func2: ast.FunctionDef) -> bool:
        """
        Check if two functions are similar.
        """
        if len(func1.body) != len(func2.body):
            return False

        for stmt1, stmt2 in zip(func1.body, func2.body, strict=False):
            if type(stmt1) != type(stmt2):
                return False

        return True

    def _get_nested_loop_depth(self, node: ast.For) -> int:
        """
        Get the depth of nested loops.
        """
        depth = 1
        for child in ast.walk(node):
            if isinstance(child, ast.For) and child != node:
                depth += 1
        return depth


class AtlasHealthPlugin(QualityPlugin):
    """
    Plugin for atlas health analysis tool.
    """

    @property
    def name(self) -> str:
        return "atlas_health"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Atlas health analysis for coverage, complexity, duplication, and documentation"

    @property
    def supported_extensions(self) -> list[str]:
        return [".py"]

    def create_analyzer(self, config: QualityConfig | None = None) -> QualityAnalyzer:
        return AtlasHealthAnalyzer(config=config)

    def get_default_config(self) -> dict[str, Any]:
        return {
            "enabled_tools": ["atlas_health"],
            "thresholds": {"cyclomatic_complexity": 10, "max_nested_loops": 3},
            "filters": {"exclude_patterns": ["__pycache__", "*.pyc", ".git", "node_modules"]},
        }
