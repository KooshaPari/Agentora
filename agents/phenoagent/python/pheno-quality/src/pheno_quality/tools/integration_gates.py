"""
Integration quality gates tool implementation.
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


class IntegrationGates(QualityAnalyzer):
    """
    Integration quality gates tool.
    """

    def __init__(self, name: str = "integration_gates", config: QualityConfig | None = None):
        super().__init__(name, config)
        self.patterns = {
            "api_contracts": self._validate_api_contracts,
            "error_handling": self._validate_error_handling,
            "logging_validation": self._validate_logging,
            "security_validation": self._validate_security,
            "monitoring_integration": self._validate_monitoring,
        }

    def analyze_file(self, file_path: Path) -> list[QualityIssue]:
        """
        Analyze a single file for integration quality issues.
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            file_issues = []

            for validator_func in self.patterns.values():
                issues = validator_func(tree, file_path)
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
        Analyze a directory for integration quality issues.
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

    def _validate_api_contracts(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Validate API contracts.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name.lower()

                if any(
                    keyword in class_name for keyword in ["api", "endpoint", "controller", "route"]
                ):
                    if not self._has_error_handling(node):
                        issue = QualityIssue(
                            id=QualityUtils.generate_issue_id(
                                "api_contracts", str(file_path), node.lineno,
                            ),
                            type="api_contracts",
                            severity=SeverityLevel.HIGH,
                            file=str(file_path),
                            line=node.lineno,
                            column=node.col_offset,
                            message=f"API endpoint '{node.name}' lacks proper error handling",
                            suggestion="Implement comprehensive error handling with proper HTTP status codes",
                            confidence=0.9,
                            impact=ImpactLevel.HIGH,
                            tool=self.name,
                            category=QualityUtils.categorize_issue("api_contracts", self.name),
                            tags=QualityUtils.generate_tags(
                                "api_contracts", self.name, SeverityLevel.HIGH,
                            ),
                        )
                        issues.append(issue)

        return issues

    def _validate_error_handling(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Validate error handling patterns.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if not self._has_proper_exception_handling(node):
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "error_handling", str(file_path), node.lineno,
                        ),
                        type="error_handling",
                        severity=SeverityLevel.HIGH,
                        file=str(file_path),
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Function '{node.name}' lacks proper exception handling",
                        suggestion="Add try-catch blocks and proper exception handling",
                        confidence=0.8,
                        impact=ImpactLevel.HIGH,
                        tool=self.name,
                        category=QualityUtils.categorize_issue("error_handling", self.name),
                        tags=QualityUtils.generate_tags(
                            "error_handling", self.name, SeverityLevel.HIGH,
                        ),
                    )
                    issues.append(issue)

        return issues

    def _validate_logging(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Validate logging implementation.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if not self._has_proper_logging(node):
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "logging_validation", str(file_path), node.lineno,
                        ),
                        type="logging_validation",
                        severity=SeverityLevel.MEDIUM,
                        file=str(file_path),
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Function '{node.name}' lacks proper logging",
                        suggestion="Add structured logging for monitoring and debugging",
                        confidence=0.6,
                        impact=ImpactLevel.MEDIUM,
                        tool=self.name,
                        category=QualityUtils.categorize_issue("logging_validation", self.name),
                        tags=QualityUtils.generate_tags(
                            "logging_validation", self.name, SeverityLevel.MEDIUM,
                        ),
                    )
                    issues.append(issue)

        return issues

    def _validate_security(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Validate security patterns.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if self._has_sql_injection_risk(node):
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "security_validation", str(file_path), node.lineno,
                        ),
                        type="security_validation",
                        severity=SeverityLevel.HIGH,
                        file=str(file_path),
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Function '{node.name}' has SQL injection risk",
                        suggestion="Use parameterized queries to prevent SQL injection",
                        confidence=0.9,
                        impact=ImpactLevel.HIGH,
                        tool=self.name,
                        category=QualityUtils.categorize_issue("security_validation", self.name),
                        tags=QualityUtils.generate_tags(
                            "security_validation", self.name, SeverityLevel.HIGH,
                        ),
                    )
                    issues.append(issue)

        return issues

    def _validate_monitoring(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Validate monitoring integration.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if not self._has_metrics_collection(node):
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "monitoring_integration", str(file_path), node.lineno,
                        ),
                        type="monitoring_integration",
                        severity=SeverityLevel.MEDIUM,
                        file=str(file_path),
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Function '{node.name}' lacks metrics collection",
                        suggestion="Add metrics collection for monitoring and alerting",
                        confidence=0.6,
                        impact=ImpactLevel.MEDIUM,
                        tool=self.name,
                        category=QualityUtils.categorize_issue("monitoring_integration", self.name),
                        tags=QualityUtils.generate_tags(
                            "monitoring_integration", self.name, SeverityLevel.MEDIUM,
                        ),
                    )
                    issues.append(issue)

        return issues

    # Helper methods
    def _has_error_handling(self, node: ast.ClassDef) -> bool:
        """
        Check if class has error handling.
        """
        return any(isinstance(child, ast.Try) for child in ast.walk(node))

    def _has_proper_exception_handling(self, node: ast.FunctionDef) -> bool:
        """
        Check if function has proper exception handling.
        """
        return any(isinstance(child, ast.Try) for child in ast.walk(node))

    def _has_proper_logging(self, node: ast.FunctionDef) -> bool:
        """
        Check if function has proper logging.
        """
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute):
                    if child.func.attr.lower() in ["info", "debug", "warning", "error"]:
                        return True
        return False

    def _has_sql_injection_risk(self, node: ast.FunctionDef) -> bool:
        """
        Check if function has SQL injection risk.
        """
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute):
                    if child.func.attr.lower() in ["execute", "query"]:
                        for arg in child.args:
                            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Mod):
                                return True
        return False

    def _has_metrics_collection(self, node: ast.FunctionDef) -> bool:
        """
        Check if function has metrics collection.
        """
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute):
                    if child.func.attr.lower() in ["counter", "gauge", "histogram", "timer"]:
                        return True
        return False


class IntegrationGatesPlugin(QualityPlugin):
    """
    Plugin for integration quality gates tool.
    """

    @property
    def name(self) -> str:
        return "integration_gates"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Integration quality gates for API contracts, error handling, and monitoring"

    @property
    def supported_extensions(self) -> list[str]:
        return [".py"]

    def create_analyzer(self, config: QualityConfig | None = None) -> QualityAnalyzer:
        return IntegrationGates(config=config)

    def get_default_config(self) -> dict[str, Any]:
        return {
            "enabled_tools": ["integration_gates"],
            "thresholds": {"max_integration_issues": 20},
            "filters": {"exclude_patterns": ["__pycache__", "*.pyc", ".git", "node_modules"]},
        }
