"""
Security pattern scanning tool implementation.
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


class SecurityScanner(QualityAnalyzer):
    """
    Security pattern scanning tool.
    """

    def __init__(self, name: str = "security_scanner", config: QualityConfig | None = None):
        super().__init__(name, config)
        self.patterns = {
            "sql_injection": self._detect_sql_injection,
            "xss_vulnerability": self._detect_xss_vulnerability,
            "insecure_deserialization": self._detect_insecure_deserialization,
            "authentication_bypass": self._detect_authentication_bypass,
            "authorization_flaw": self._detect_authorization_flaw,
        }

    def analyze_file(self, file_path: Path) -> list[QualityIssue]:
        """
        Analyze a single file for security issues.
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
        Analyze a directory for security issues.
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

    def _detect_sql_injection(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Detect SQL injection vulnerabilities.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr.lower() in ["execute", "query"]:
                        if self._has_string_formatting(node):
                            issue = QualityIssue(
                                id=QualityUtils.generate_issue_id(
                                    "sql_injection", str(file_path), node.lineno,
                                ),
                                type="sql_injection",
                                severity=SeverityLevel.CRITICAL,
                                file=str(file_path),
                                line=node.lineno,
                                column=node.col_offset,
                                message="Potential SQL injection vulnerability detected",
                                suggestion="Use parameterized queries to prevent SQL injection",
                                confidence=0.9,
                                impact=ImpactLevel.CRITICAL,
                                tool=self.name,
                                category=QualityUtils.categorize_issue("sql_injection", self.name),
                                tags=QualityUtils.generate_tags(
                                    "sql_injection", self.name, SeverityLevel.CRITICAL,
                                ),
                            )
                            issues.append(issue)

        return issues

    def _detect_xss_vulnerability(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Detect XSS vulnerabilities.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr.lower() in ["render", "template", "html"]:
                        if self._has_user_input(node):
                            issue = QualityIssue(
                                id=QualityUtils.generate_issue_id(
                                    "xss_vulnerability", str(file_path), node.lineno,
                                ),
                                type="xss_vulnerability",
                                severity=SeverityLevel.HIGH,
                                file=str(file_path),
                                line=node.lineno,
                                column=node.col_offset,
                                message="Potential XSS vulnerability detected",
                                suggestion="Sanitize user input to prevent XSS attacks",
                                confidence=0.8,
                                impact=ImpactLevel.HIGH,
                                tool=self.name,
                                category=QualityUtils.categorize_issue(
                                    "xss_vulnerability", self.name,
                                ),
                                tags=QualityUtils.generate_tags(
                                    "xss_vulnerability", self.name, SeverityLevel.HIGH,
                                ),
                            )
                            issues.append(issue)

        return issues

    def _detect_insecure_deserialization(
        self, tree: ast.AST, file_path: Path,
    ) -> list[QualityIssue]:
        """
        Detect insecure deserialization.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id.lower() in ["pickle", "marshal", "eval"]:
                        issue = QualityIssue(
                            id=QualityUtils.generate_issue_id(
                                "insecure_deserialization", str(file_path), node.lineno,
                            ),
                            type="insecure_deserialization",
                            severity=SeverityLevel.HIGH,
                            file=str(file_path),
                            line=node.lineno,
                            column=node.col_offset,
                            message="Insecure deserialization detected",
                            suggestion="Use safe deserialization methods and validate input",
                            confidence=0.8,
                            impact=ImpactLevel.HIGH,
                            tool=self.name,
                            category=QualityUtils.categorize_issue(
                                "insecure_deserialization", self.name,
                            ),
                            tags=QualityUtils.generate_tags(
                                "insecure_deserialization", self.name, SeverityLevel.HIGH,
                            ),
                        )
                        issues.append(issue)

        return issues

    def _detect_authentication_bypass(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Detect authentication bypass vulnerabilities.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if "auth" in node.name.lower() or "login" in node.name.lower():
                    if not self._has_proper_authentication(node):
                        issue = QualityIssue(
                            id=QualityUtils.generate_issue_id(
                                "authentication_bypass", str(file_path), node.lineno,
                            ),
                            type="authentication_bypass",
                            severity=SeverityLevel.HIGH,
                            file=str(file_path),
                            line=node.lineno,
                            column=node.col_offset,
                            message=f"Function '{node.name}' may have authentication bypass vulnerability",
                            suggestion="Implement proper authentication checks and validation",
                            confidence=0.7,
                            impact=ImpactLevel.HIGH,
                            tool=self.name,
                            category=QualityUtils.categorize_issue(
                                "authentication_bypass", self.name,
                            ),
                            tags=QualityUtils.generate_tags(
                                "authentication_bypass", self.name, SeverityLevel.HIGH,
                            ),
                        )
                        issues.append(issue)

        return issues

    def _detect_authorization_flaw(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Detect authorization flaws.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if "admin" in node.name.lower() or "privilege" in node.name.lower():
                    if not self._has_proper_authorization(node):
                        issue = QualityIssue(
                            id=QualityUtils.generate_issue_id(
                                "authorization_flaw", str(file_path), node.lineno,
                            ),
                            type="authorization_flaw",
                            severity=SeverityLevel.HIGH,
                            file=str(file_path),
                            line=node.lineno,
                            column=node.col_offset,
                            message=f"Function '{node.name}' may have authorization flaw",
                            suggestion="Implement proper authorization checks and role validation",
                            confidence=0.7,
                            impact=ImpactLevel.HIGH,
                            tool=self.name,
                            category=QualityUtils.categorize_issue("authorization_flaw", self.name),
                            tags=QualityUtils.generate_tags(
                                "authorization_flaw", self.name, SeverityLevel.HIGH,
                            ),
                        )
                        issues.append(issue)

        return issues

    # Helper methods
    def _has_string_formatting(self, node: ast.Call) -> bool:
        """
        Check if call has string formatting.
        """
        for arg in node.args:
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Mod):
                return True
        return False

    def _has_user_input(self, node: ast.Call) -> bool:
        """
        Check if call uses user input.
        """
        return any(isinstance(arg, ast.Name) for arg in node.args)

    def _has_proper_authentication(self, node: ast.FunctionDef) -> bool:
        """
        Check if function has proper authentication.
        """
        # Look for authentication-related patterns
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_str = self._get_call_string(child)
                if any(
                    keyword in call_str.lower()
                    for keyword in ["verify", "validate", "check", "authenticate"]
                ):
                    return True
        return False

    def _has_proper_authorization(self, node: ast.FunctionDef) -> bool:
        """
        Check if function has proper authorization.
        """
        # Look for authorization-related patterns
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_str = self._get_call_string(child)
                if any(
                    keyword in call_str.lower()
                    for keyword in ["authorize", "permission", "role", "access"]
                ):
                    return True
        return False

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


class SecurityScannerPlugin(QualityPlugin):
    """
    Plugin for security scanning tool.
    """

    @property
    def name(self) -> str:
        return "security_scanner"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Security vulnerability detection for OWASP Top 10 patterns"

    @property
    def supported_extensions(self) -> list[str]:
        return [".py"]

    def create_analyzer(self, config: QualityConfig | None = None) -> QualityAnalyzer:
        return SecurityScanner(config=config)

    def get_default_config(self) -> dict[str, Any]:
        return {
            "enabled_tools": ["security_scanner"],
            "thresholds": {"max_security_issues": 10},
            "filters": {"exclude_patterns": ["__pycache__", "*.pyc", ".git", "node_modules"]},
        }
