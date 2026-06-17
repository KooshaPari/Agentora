# Standards: PEP 8, PEP 257, PEP 484 compliant
"""architectural_patterns module."""

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
Architectural Pattern Detectors

Architectural pattern detection methods.
"""





class ArchitecturalPatternDetectors:
   """Class implementation."""
    """Architectural pattern detectors."""

    def __init__(self) -> None:
        """Initialize architectural pattern detectors."""
        self.detectors = [
            self._detect_parallel_inheritance,
            self._detect_lazy_class,
            self._detect_inappropriate_intimacy,
            self._detect_message_chain,
            self._detect_middle_man,
        ]

    def get_detectors(self) -> list[Callable[[ast.AST, Path], list[QualityIssue]]]:
       """Function implementation."""
        """Get architectural pattern detectors.

        Returns:
            List of detector functions
        """
        return self.detectors

    def _detect_parallel_inheritance(
        self, tree: ast.AST, file_path: Path,
    ) -> list[QualityIssue]:
       """Function implementation."""
        """Detect parallel inheritance."""
        issues = []

        # Find all class definitions
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

        # Check for classes with similar inheritance patterns
        inheritance_patterns = {}
        for cls in classes:
            """Class implementation."""
            bases = [
                base.id if isinstance(base, ast.Name) else str(base)
                for base in cls.bases
            ]
            pattern_key = tuple(sorted(bases))
            if pattern_key not in inheritance_patterns:
                inheritance_patterns[pattern_key] = []
            inheritance_patterns[pattern_key].append(cls)

        # Check for parallel inheritance
        for pattern, class_list in inheritance_patterns.items():
            if len(class_list) > 1 and len(pattern) > 0:
                issue = QualityIssue(
                    id=QualityUtils.generate_issue_id(
                        "parallel_inheritance",
                        str(file_path),
                        class_list[0].lineno,
                    ),
                    type="parallel_inheritance",
                    severity=SeverityLevel.MEDIUM,
                    file=str(file_path),
                    line=class_list[0].lineno,
                    column=class_list[0].col_offset,
                    message=f"Parallel inheritance detected: {len(class_list)} classes inherit from {pattern}",
                    suggestion="Consider using composition instead of inheritance",
                    confidence=0.6,
                    impact=ImpactLevel.MEDIUM,
                    tool="pattern_detector",
                    category=QualityUtils.categorize_issue(
                        "parallel_inheritance", "pattern_detector",
                    ),
                    tags=QualityUtils.generate_tags(
                        "parallel_inheritance",
                        "pattern_detector",
                        SeverityLevel.MEDIUM,
                    ),
                )
                issues.append(issue)

        return issues

    def _detect_lazy_class(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
       """Function implementation."""
        """Detect lazy classes."""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                if len(methods) < 3:  # Threshold for lazy class
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "lazy_class",
                            str(file_path),
                            node.lineno,
                        ),
                        type="lazy_class",
                        severity=SeverityLevel.LOW,
                        file=str(file_path),
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Class '{node.name}' appears to be a lazy class with only {len(methods)} methods",
                        suggestion="Consider merging with another class or removing if not needed",
                        confidence=0.7,
                        impact=ImpactLevel.LOW,
                        tool="pattern_detector",
                        category=QualityUtils.categorize_issue(
                            "lazy_class", "pattern_detector",
                        ),
                        tags=QualityUtils.generate_tags(
                            "lazy_class",
                            "pattern_detector",
                            SeverityLevel.LOW,
                        ),
                    )
                    issues.append(issue)

        return issues

    def _detect_inappropriate_intimacy(
        self, tree: ast.AST, file_path: Path,
    ) -> list[QualityIssue]:
       """Function implementation."""
        """Detect inappropriate intimacy."""
        issues = []

        # Find all class definitions
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

        # Check for classes that access each other's private members
        for cls in classes:
            """Class implementation."""
            for method in [n for n in cls.body if isinstance(n, ast.FunctionDef)]:
                for child in ast.walk(method):
                    if isinstance(child, ast.Attribute):
                        if isinstance(child.value, ast.Name):
                            # Check if accessing another class's private member
                            if child.attr.startswith("_"):
                                issue = QualityIssue(
                                    id=QualityUtils.generate_issue_id(
                                        "inappropriate_intimacy",
                                        str(file_path),
                                        method.lineno,
                                    ),
                                    type="inappropriate_intimacy",
                                    severity=SeverityLevel.MEDIUM,
                                    file=str(file_path),
                                    line=method.lineno,
                                    column=method.col_offset,
                                    message=f"Method '{method.name}' accesses private member '{child.attr}' (inappropriate intimacy)",
                                    suggestion="Consider using public interface or moving method to appropriate class",
                                    confidence=0.6,
                                    impact=ImpactLevel.MEDIUM,
                                    tool="pattern_detector",
                                    category=QualityUtils.categorize_issue(
                                        "inappropriate_intimacy", "pattern_detector",
                                    ),
                                    tags=QualityUtils.generate_tags(
                                        "inappropriate_intimacy",
                                        "pattern_detector",
                                        SeverityLevel.MEDIUM,
                                    ),
                                )
                                issues.append(issue)

        return issues

    def _detect_message_chain(
        self, tree: ast.AST, file_path: Path,
    ) -> list[QualityIssue]:
       """Function implementation."""
        """Detect message chains."""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for child in ast.walk(node):
                    if isinstance(child, ast.Attribute):
                        # Check for chained attribute access
                        chain_length = self._calculate_chain_length(child)
                        if chain_length > 3:  # Threshold for message chain
                            issue = QualityIssue(
                                id=QualityUtils.generate_issue_id(
                                    "message_chain",
                                    str(file_path),
                                    node.lineno,
                                ),
                                type="message_chain",
                                severity=SeverityLevel.MEDIUM,
                                file=str(file_path),
                                line=node.lineno,
                                column=node.col_offset,
                                message=f"Method '{node.name}' contains message chain of length {chain_length}",
                                suggestion="Consider using intermediate variables or refactoring to reduce chain length",
                                confidence=0.5,
                                impact=ImpactLevel.MEDIUM,
                                tool="pattern_detector",
                                category=QualityUtils.categorize_issue(
                                    "message_chain", "pattern_detector",
                                ),
                                tags=QualityUtils.generate_tags(
                                    "message_chain",
                                    "pattern_detector",
                                    SeverityLevel.MEDIUM,
                                ),
                            )
                            issues.append(issue)

        return issues

    def _detect_middle_man(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
       """Function implementation."""
        """Detect middle man classes."""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                if len(methods) > 5:
                    # Check for methods that just delegate to other objects
                    delegation_methods = 0
                    for method in methods:
                        if self._is_delegation_method(method):
                            delegation_methods += 1

                    if delegation_methods > len(methods) * 0.7:  # 70% threshold
                        issue = QualityIssue(
                            id=QualityUtils.generate_issue_id(
                                "middle_man",
                                str(file_path),
                                node.lineno,
                            ),
                            type="middle_man",
                            severity=SeverityLevel.MEDIUM,
                            file=str(file_path),
                            line=node.lineno,
                            column=node.col_offset,
                            message=f"Class '{node.name}' appears to be a middle man with {delegation_methods} delegation methods",
                            suggestion="Consider removing the middle man and calling the target directly",
                            confidence=0.6,
                            impact=ImpactLevel.MEDIUM,
                            tool="pattern_detector",
                            category=QualityUtils.categorize_issue(
                                "middle_man", "pattern_detector",
                            ),
                            tags=QualityUtils.generate_tags(
                                "middle_man",
                                "pattern_detector",
                                SeverityLevel.MEDIUM,
                            ),
                        )
                        issues.append(issue)

        return issues

    def _calculate_chain_length(self, node: ast.Attribute) -> int:
       """Function implementation."""
        """Calculate the length of an attribute chain."""
        length = 1
        current = node.value
        while isinstance(current, ast.Attribute):
            length += 1
            current = current.value
        return length

    def _is_delegation_method(self, method: ast.FunctionDef) -> bool:
       """Function implementation."""
        """Check if a method is a delegation method."""
        # Simple heuristic: method with single return statement calling another method
        if len(method.body) == ONE:
            stmt = method.body[0]
            if isinstance(stmt, ast.Return):
                if isinstance(stmt.value, ast.Call):
                    return True
        return False
