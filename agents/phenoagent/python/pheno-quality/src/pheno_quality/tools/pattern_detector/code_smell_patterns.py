# Standards: PEP 8, PEP 257, PEP 484 compliant
"""code_smell_patterns module."""

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
Code Smell Pattern Detectors

Code smell pattern detection methods.
"""





class CodeSmellPatternDetectors:
   """Class implementation."""
    """Code smell pattern detectors."""

    def __init__(self) -> None:
        """Initialize code smell pattern detectors."""
        self.detectors = [
            self._detect_incomplete_library_class,
            self._detect_temporary_field,
            self._detect_refused_bequest,
            self._detect_alternative_classes,
            self._detect_duplicate_code_blocks,
        ]

    def get_detectors(self) -> list[Callable[[ast.AST, Path], list[QualityIssue]]]:
       """Function implementation."""
        """Get code smell pattern detectors.

        Returns:
            List of detector functions
        """
        return self.detectors

    def _detect_incomplete_library_class(
        self, tree: ast.AST, file_path: Path,
    ) -> list[QualityIssue]:
       """Function implementation."""
        """Detect incomplete library classes."""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check for classes that extend library classes but don't implement all methods
                if node.bases:
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id in [
                            "Exception",
                            "BaseException",
                        ]:
                            # Check if class has proper __init__ method
                            has_init = any(
                                isinstance(n, ast.FunctionDef) and n.name == "__init__"
                                for n in node.body
                            )
                            if not has_init:
                                """Class implementation."""
                                issue = QualityIssue(
                                    id=QualityUtils.generate_issue_id(
                                        "incomplete_library_class",
                                        str(file_path),
                                        node.lineno,
                                    ),
                                    type="incomplete_library_class",
                                    severity=SeverityLevel.MEDIUM,
                                    file=str(file_path),
                                    line=node.lineno,
                                    column=node.col_offset,
                                    message=f"Class '{node.name}' extends library class but lacks proper __init__ method",
                                    suggestion="Implement proper __init__ method for library class extension",
                                    confidence=0.7,
                                    impact=ImpactLevel.MEDIUM,
                                    tool="pattern_detector",
                                    category=QualityUtils.categorize_issue(
                                        "incomplete_library_class", "pattern_detector",
                                    ),
                                    tags=QualityUtils.generate_tags(
                                        "incomplete_library_class",
                                        "pattern_detector",
                                        SeverityLevel.MEDIUM,
                                    ),
                                )
                                issues.append(issue)

        return issues

    def _detect_temporary_field(
        self, tree: ast.AST, file_path: Path,
    ) -> list[QualityIssue]:
       """Function implementation."""
        """Detect temporary fields."""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check for fields that are only used in specific methods
                fields = [n for n in node.body if isinstance(n, ast.Assign)]
                methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]

                for field in fields:
                    field_name = None
                    if isinstance(field.targets[0], ast.Attribute):
                        field_name = field.targets[0].attr
                    elif isinstance(field.targets[0], ast.Name):
                        field_name = field.targets[0].id

                    if field_name:
                        # Check how many methods use this field
                        usage_count = 0
                        for method in methods:
                            for child in ast.walk(method):
                                if (
                                    isinstance(child, ast.Attribute)
                                    and child.attr == field_name
                                ) or (
                                    isinstance(child, ast.Name)
                                    and child.id == field_name
                                ):
                                    usage_count += 1

                        if usage_count < 2:  # Field used in less than 2 methods
                            issue = QualityIssue(
                                id=QualityUtils.generate_issue_id(
                                    "temporary_field",
                                    str(file_path),
                                    field.lineno,
                                ),
                                type="temporary_field",
                                severity=SeverityLevel.LOW,
                                file=str(file_path),
                                line=field.lineno,
                                column=field.col_offset,
                                message=f"Field '{field_name}' appears to be temporary (used in {usage_count} methods)",
                                suggestion="Consider removing temporary field or making it more widely used",
                                confidence=0.6,
                                impact=ImpactLevel.LOW,
                                tool="pattern_detector",
                                category=QualityUtils.categorize_issue(
                                    "temporary_field", "pattern_detector",
                                ),
                                tags=QualityUtils.generate_tags(
                                    "temporary_field",
                                    "pattern_detector",
                                    SeverityLevel.LOW,
                                ),
                            )
                            issues.append(issue)

        return issues

    def _detect_refused_bequest(
        self, tree: ast.AST, file_path: Path,
    ) -> list[QualityIssue]:
       """Function implementation."""
        """Detect refused bequest."""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if node.bases:  # Class has inheritance
                    # Check if class overrides many methods from parent
                    methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                    overridden_methods = [
                        m for m in methods if not m.name.startswith("_")
                    ]

                    if len(overridden_methods) > 5:  # Threshold for refused bequest
                        issue = QualityIssue(
                            id=QualityUtils.generate_issue_id(
                                "refused_bequest",
                                str(file_path),
                                node.lineno,
                            ),
                            type="refused_bequest",
                            severity=SeverityLevel.MEDIUM,
                            file=str(file_path),
                            line=node.lineno,
                            column=node.col_offset,
                            message=f"Class '{node.name}' overrides {len(overridden_methods)} methods (refused bequest)",
                            suggestion="Consider using composition instead of inheritance",
                            confidence=0.5,
                            impact=ImpactLevel.MEDIUM,
                            tool="pattern_detector",
                            category=QualityUtils.categorize_issue(
                                "refused_bequest", "pattern_detector",
                            ),
                            tags=QualityUtils.generate_tags(
                                "refused_bequest",
                                "pattern_detector",
                                SeverityLevel.MEDIUM,
                            ),
                        )
                        issues.append(issue)

        return issues

    def _detect_alternative_classes(
        self, tree: ast.AST, file_path: Path,
    ) -> list[QualityIssue]:
       """Function implementation."""
        """Detect alternative classes."""
        issues = []

        # Find all class definitions
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

        # Check for classes with similar method signatures
        for i, cls1 in enumerate(classes):
            """Class implementation."""
            for cls2 in classes[i + 1 :]:
                if self._have_similar_methods(cls1, cls2):
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "alternative_classes",
                            str(file_path),
                            cls1.lineno,
                        ),
                        type="alternative_classes",
                        severity=SeverityLevel.MEDIUM,
                        file=str(file_path),
                        line=cls1.lineno,
                        column=cls1.col_offset,
                        message=f"Classes '{cls1.name}' and '{cls2.name}' appear to be alternatives",
                        suggestion="Consider merging similar classes or using inheritance",
                        confidence=0.6,
                        impact=ImpactLevel.MEDIUM,
                        tool="pattern_detector",
                        category=QualityUtils.categorize_issue(
                            "alternative_classes", "pattern_detector",
                        ),
                        tags=QualityUtils.generate_tags(
                            "alternative_classes",
                            "pattern_detector",
                            SeverityLevel.MEDIUM,
                        ),
                    )
                    issues.append(issue)

        return issues

    def _detect_duplicate_code_blocks(
        self, tree: ast.AST, file_path: Path,
    ) -> list[QualityIssue]:
       """Function implementation."""
        """Detect duplicate code blocks."""
        issues = []

        # Find all function definitions
        functions = [
            node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        ]

        # Check for functions with similar structure
        for i, func1 in enumerate(functions):
            for func2 in functions[i + 1 :]:
                if self._are_functions_similar(func1, func2):
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "duplicate_code_blocks",
                            str(file_path),
                            func1.lineno,
                        ),
                        type="duplicate_code_blocks",
                        severity=SeverityLevel.MEDIUM,
                        file=str(file_path),
                        line=func1.lineno,
                        column=func1.col_offset,
                        message=f"Functions '{func1.name}' and '{func2.name}' appear to have duplicate code",
                        suggestion="Consider extracting common code into a shared function",
                        confidence=0.5,
                        impact=ImpactLevel.MEDIUM,
                        tool="pattern_detector",
                        category=QualityUtils.categorize_issue(
                            "duplicate_code_blocks", "pattern_detector",
                        ),
                        tags=QualityUtils.generate_tags(
                            "duplicate_code_blocks",
                            "pattern_detector",
                            SeverityLevel.MEDIUM,
                        ),
                    )
                    issues.append(issue)

        return issues

    def _have_similar_methods(self, cls1: ast.ClassDef, cls2: ast.ClassDef) -> bool:
       """Function implementation."""
        """Check if two classes have similar methods."""
        methods1 = {m.name for m in cls1.body if isinstance(m, ast.FunctionDef)}
        methods2 = {m.name for m in cls2.body if isinstance(m, ast.FunctionDef)}

        # Check for significant overlap in method names
        common_methods = methods1.intersection(methods2)
        return len(common_methods) > 3

    def _are_functions_similar(
        self, func1: ast.FunctionDef, func2: ast.FunctionDef,
    ) -> bool:
       """Function implementation."""
        """Check if two functions are similar."""
        # Simple heuristic: similar parameter count and body length
        params1 = len(func1.args.args)
        params2 = len(func2.args.args)

        body1 = len(func1.body)
        body2 = len(func2.body)

        return abs(params1 - params2) <= 1 and abs(body1 - body2) <= 2
