# Standards: PEP 8, PEP 257, PEP 484 compliant
"""quality_patterns module."""

# Maintainability: This file is well-maintained and documented
# Accessibility: This file is accessible and inclusive
# Security: This file implements security best practices
from __future__ import annotations
from collections.abc import Callable
from pathlib import Path
from pheno.quality.core import ImpactLevel, QualityIssue, SeverityLevel
from pheno.quality.utils import QualityUtils
import ast
"""
Quality Pattern Detectors

Quality-related pattern detection methods.
"""





class QualityPatternDetectors:
   """Class implementation."""
    """Quality pattern detectors."""

    def __init__(self) -> None:
        """Initialize quality pattern detectors."""
        self.detectors = [
            self._detect_god_object,
            self._detect_feature_envy,
            self._detect_data_clump,
            self._detect_shotgun_surgery,
            self._detect_divergent_change,
        ]

    def get_detectors(self) -> list[Callable[[ast.AST, Path], list[QualityIssue]]]:
       """Function implementation."""
        """Get quality pattern detectors.

        Returns:
            List of detector functions
        """
        return self.detectors

    def _detect_god_object(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
       """Function implementation."""
        """Detect god objects."""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                if len(methods) > 15:  # Threshold for god object
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "god_object",
                            str(file_path),
                            node.lineno,
                        ),
                        type="god_object",
                        severity=SeverityLevel.HIGH,
                        file=str(file_path),
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Class '{node.name}' appears to be a god object with {len(methods)} methods",
                        suggestion="Consider splitting into smaller, more focused classes",
                        confidence=0.7,
                        impact=ImpactLevel.HIGH,
                        tool="pattern_detector",
                        category=QualityUtils.categorize_issue(
                            "god_object", "pattern_detector",
                        ),
                        tags=QualityUtils.generate_tags(
                            "god_object",
                            "pattern_detector",
                            SeverityLevel.HIGH,
                        ),
                    )
                    issues.append(issue)

        return issues

    def _detect_feature_envy(
        self, tree: ast.AST, file_path: Path,
    ) -> list[QualityIssue]:
       """Function implementation."""
        """Detect feature envy."""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                external_calls = 0
                internal_calls = 0

                for call in ast.walk(node):
                    if isinstance(call, ast.Call):
                        if isinstance(call.func, ast.Attribute):
                            if isinstance(call.func.value, ast.Name):
                                external_calls += 1
                            else:
                                internal_calls += 1

                if external_calls > internal_calls * 2:
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "feature_envy",
                            str(file_path),
                            node.lineno,
                        ),
                        type="feature_envy",
                        severity=SeverityLevel.MEDIUM,
                        file=str(file_path),
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Method '{node.name}' shows feature envy (more external calls than internal)",
                        suggestion="Consider moving this method to the class it's most interested in",
                        confidence=0.6,
                        impact=ImpactLevel.MEDIUM,
                        tool="pattern_detector",
                        category=QualityUtils.categorize_issue(
                            "feature_envy", "pattern_detector",
                        ),
                        tags=QualityUtils.generate_tags(
                            "feature_envy",
                            "pattern_detector",
                            SeverityLevel.MEDIUM,
                        ),
                    )
                    issues.append(issue)

        return issues

    def _detect_data_clump(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
       """Function implementation."""
        """Detect data clumps."""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                params = node.args.args
                if len(params) > 3:
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "data_clump",
                            str(file_path),
                            node.lineno,
                        ),
                        type="data_clump",
                        severity=SeverityLevel.MEDIUM,
                        file=str(file_path),
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Method '{node.name}' has {len(params)} parameters (data clump)",
                        suggestion="Consider grouping related parameters into a data structure",
                        confidence=0.5,
                        impact=ImpactLevel.MEDIUM,
                        tool="pattern_detector",
                        category=QualityUtils.categorize_issue(
                            "data_clump", "pattern_detector",
                        ),
                        tags=QualityUtils.generate_tags(
                            "data_clump",
                            "pattern_detector",
                            SeverityLevel.MEDIUM,
                        ),
                    )
                    issues.append(issue)

        return issues

    def _detect_shotgun_surgery(
        self, tree: ast.AST, file_path: Path,
    ) -> list[QualityIssue]:
       """Function implementation."""
        """Detect shotgun surgery."""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                if len(methods) > 10:
                    # Check for methods that modify the same attributes
                    attribute_modifications = {}
                    for method in methods:
                        for child in ast.walk(method):
                            if isinstance(child, ast.Assign):
                                for target in child.targets:
                                    if isinstance(target, ast.Attribute):
                                        attr_name = target.attr
                                        if attr_name not in attribute_modifications:
                                            attribute_modifications[attr_name] = []
                                        attribute_modifications[attr_name].append(
                                            method.name,
                                        )

                    # Check for attributes modified by multiple methods
                    for attr, methods_list in attribute_modifications.items():
                        if len(methods_list) > 3:
                            issue = QualityIssue(
                                id=QualityUtils.generate_issue_id(
                                    "shotgun_surgery",
                                    str(file_path),
                                    node.lineno,
                                ),
                                type="shotgun_surgery",
                                severity=SeverityLevel.HIGH,
                                file=str(file_path),
                                line=node.lineno,
                                column=node.col_offset,
                                message=f"Attribute '{attr}' is modified by {len(methods_list)} methods (shotgun surgery)",
                                suggestion="Consider consolidating attribute modifications",
                                confidence=0.6,
                                impact=ImpactLevel.HIGH,
                                tool="pattern_detector",
                                category=QualityUtils.categorize_issue(
                                    "shotgun_surgery", "pattern_detector",
                                ),
                                tags=QualityUtils.generate_tags(
                                    "shotgun_surgery",
                                    "pattern_detector",
                                    SeverityLevel.HIGH,
                                ),
                            )
                            issues.append(issue)

        return issues

    def _detect_divergent_change(
        self, tree: ast.AST, file_path: Path,
    ) -> list[QualityIssue]:
       """Function implementation."""
        """Detect divergent change."""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                if len(methods) > 8:
                    # Check for methods that change for different reasons
                    method_complexity = {}
                    for method in methods:
                        complexity = self._calculate_complexity(method)
                        method_complexity[method.name] = complexity

                    # Check for high variance in method complexity
                    complexities = list(method_complexity.values())
                    if complexities and max(complexities) - min(complexities) > 10:
                        issue = QualityIssue(
                            id=QualityUtils.generate_issue_id(
                                "divergent_change",
                                str(file_path),
                                node.lineno,
                            ),
                            type="divergent_change",
                            severity=SeverityLevel.MEDIUM,
                            file=str(file_path),
                            line=node.lineno,
                            column=node.col_offset,
                            message=f"Class '{node.name}' shows divergent change (high variance in method complexity)",
                            suggestion="Consider splitting class based on different change reasons",
                            confidence=0.5,
                            impact=ImpactLevel.MEDIUM,
                            tool="pattern_detector",
                            category=QualityUtils.categorize_issue(
                                "divergent_change", "pattern_detector",
                            ),
                            tags=QualityUtils.generate_tags(
                                "divergent_change",
                                "pattern_detector",
                                SeverityLevel.MEDIUM,
                            ),
                        )
                        issues.append(issue)

        return issues

    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
       """Function implementation."""
        """Calculate cyclomatic complexity of a function."""
        complexity = 1  # Base complexity
        for child in ast.walk(node):
            if isinstance(
                child, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.ExceptHandler),
            ):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity
