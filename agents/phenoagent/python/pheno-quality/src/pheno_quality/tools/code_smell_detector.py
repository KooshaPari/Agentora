"""
Code smell detection tool implementation.
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


class CodeSmellDetector(QualityAnalyzer):
    """
    Code smell detection tool.
    """

    def __init__(self, name: str = "code_smell_detector", config: QualityConfig | None = None):
        super().__init__(name, config)
        self.patterns = {
            "long_method": self._detect_long_methods,
            "large_class": self._detect_large_classes,
            "duplicate_code": self._detect_duplicate_code,
            "dead_code": self._detect_dead_code,
            "magic_number": self._detect_magic_numbers,
            "high_complexity": self._detect_high_complexity,
        }

    def analyze_file(self, file_path: Path) -> list[QualityIssue]:
        """
        Analyze a single file for code smells.
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
        Analyze a directory for code smells.
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

    def _detect_long_methods(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Detect long methods.
        """
        issues = []
        threshold = self.config.thresholds.get("long_method_lines", 50)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if hasattr(node, "end_lineno") and node.end_lineno:
                    lines = node.end_lineno - node.lineno + 1
                    if lines > threshold:
                        issue = QualityIssue(
                            id=QualityUtils.generate_issue_id(
                                "long_method", str(file_path), node.lineno,
                            ),
                            type="long_method",
                            severity=SeverityLevel.HIGH,
                            file=str(file_path),
                            line=node.lineno,
                            column=node.col_offset,
                            message=f"Method '{node.name}' is {lines} lines long (threshold: {threshold})",
                            suggestion="Consider breaking this method into smaller, more focused methods",
                            confidence=0.9,
                            impact=ImpactLevel.HIGH,
                            tool=self.name,
                            category=QualityUtils.categorize_issue("long_method", self.name),
                            tags=QualityUtils.generate_tags(
                                "long_method", self.name, SeverityLevel.HIGH,
                            ),
                        )
                        issues.append(issue)

        return issues

    def _detect_large_classes(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Detect large classes.
        """
        issues = []
        threshold = self.config.thresholds.get("large_class_methods", 20)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                if len(methods) > threshold:
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "large_class", str(file_path), node.lineno,
                        ),
                        type="large_class",
                        severity=SeverityLevel.MEDIUM,
                        file=str(file_path),
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Class '{node.name}' has {len(methods)} methods (threshold: {threshold})",
                        suggestion="Consider splitting this class into smaller, more focused classes",
                        confidence=0.7,
                        impact=ImpactLevel.MEDIUM,
                        tool=self.name,
                        category=QualityUtils.categorize_issue("large_class", self.name),
                        tags=QualityUtils.generate_tags(
                            "large_class", self.name, SeverityLevel.MEDIUM,
                        ),
                    )
                    issues.append(issue)

        return issues

    def _detect_duplicate_code(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Detect duplicate code.
        """
        issues = []

        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

        for i, func1 in enumerate(functions):
            for func2 in functions[i + 1 :]:
                if self._functions_similar(func1, func2):
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "duplicate_code", str(file_path), func1.lineno,
                        ),
                        type="duplicate_code",
                        severity=SeverityLevel.MEDIUM,
                        file=str(file_path),
                        line=func1.lineno,
                        column=func1.col_offset,
                        message=f"Functions '{func1.name}' and '{func2.name}' may be duplicates",
                        suggestion="Consider extracting common code into a shared function",
                        confidence=0.6,
                        impact=ImpactLevel.MEDIUM,
                        tool=self.name,
                        category=QualityUtils.categorize_issue("duplicate_code", self.name),
                        tags=QualityUtils.generate_tags(
                            "duplicate_code", self.name, SeverityLevel.MEDIUM,
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
                    id=QualityUtils.generate_issue_id("dead_code", str(file_path), func.lineno),
                    type="dead_code",
                    severity=SeverityLevel.LOW,
                    file=str(file_path),
                    line=func.lineno,
                    column=func.col_offset,
                    message=f"Function '{func.name}' appears to be unused",
                    suggestion="Consider removing unused code or adding tests",
                    confidence=0.5,
                    impact=ImpactLevel.LOW,
                    tool=self.name,
                    category=QualityUtils.categorize_issue("dead_code", self.name),
                    tags=QualityUtils.generate_tags("dead_code", self.name, SeverityLevel.LOW),
                )
                issues.append(issue)

        return issues

    def _detect_magic_numbers(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Detect magic numbers.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                if isinstance(node.value, int) and node.value > 10:
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "magic_number", str(file_path), node.lineno,
                        ),
                        type="magic_number",
                        severity=SeverityLevel.LOW,
                        file=str(file_path),
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Magic number {node.value} found",
                        suggestion="Consider using a named constant",
                        confidence=0.6,
                        impact=ImpactLevel.LOW,
                        tool=self.name,
                        category=QualityUtils.categorize_issue("magic_number", self.name),
                        tags=QualityUtils.generate_tags(
                            "magic_number", self.name, SeverityLevel.LOW,
                        ),
                    )
                    issues.append(issue)

        return issues

    def _detect_high_complexity(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Detect high complexity methods.
        """
        issues = []
        threshold = self.config.thresholds.get("cyclomatic_complexity", 10)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                complexity = self._calculate_cyclomatic_complexity(node)
                if complexity > threshold:
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "high_complexity", str(file_path), node.lineno,
                        ),
                        type="high_complexity",
                        severity=SeverityLevel.HIGH,
                        file=str(file_path),
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Method '{node.name}' has complexity {complexity} (threshold: {threshold})",
                        suggestion="Consider refactoring to reduce complexity",
                        confidence=0.8,
                        impact=ImpactLevel.HIGH,
                        tool=self.name,
                        category=QualityUtils.categorize_issue("high_complexity", self.name),
                        tags=QualityUtils.generate_tags(
                            "high_complexity", self.name, SeverityLevel.HIGH,
                        ),
                    )
                    issues.append(issue)

        return issues

    # Helper methods
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


class CodeSmellDetectorPlugin(QualityPlugin):
    """
    Plugin for code smell detection tool.
    """

    @property
    def name(self) -> str:
        return "code_smell_detector"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Code smell detection for maintainability issues and refactoring opportunities"

    @property
    def supported_extensions(self) -> list[str]:
        return [".py"]

    def create_analyzer(self, config: QualityConfig | None = None) -> QualityAnalyzer:
        return CodeSmellDetector(config=config)

    def get_default_config(self) -> dict[str, Any]:
        return {
            "enabled_tools": ["code_smell_detector"],
            "thresholds": {
                "long_method_lines": 50,
                "large_class_methods": 20,
                "cyclomatic_complexity": 10,
            },
            "filters": {"exclude_patterns": ["__pycache__", "*.pyc", ".git", "node_modules"]},
        }
