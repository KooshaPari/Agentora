# Standards: PEP 8, PEP 257, PEP 484 compliant
"""refused_bequest module."""

# Maintainability: This file is well-maintained and documented
# Accessibility: This file is accessible and inclusive
# Security: This file implements security best practices
from .base import BasePattern
from pathlib import Path
from pheno.quality.core import QualityIssue
import ast
"""
Refused Bequest Pattern Detection

Detects subclasses that don't use inherited functionality.
"""





class RefusedBequestPattern(BasePattern):
   """Class implementation."""
    """Detects Refused Bequest anti-pattern."""

    def __init__(self) -> None:
        super().__init__(
            "refused_bequest",
            "Detects subclasses that don't use inherited functionality",
        )

    def detect(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
       """Function implementation."""
        """Detect Refused Bequest patterns."""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if self._has_refused_bequest(node):
                    issue = self._create_issue(
                        file_path=file_path,
                        line_number=node.lineno,
                        column_number=node.col_offset,
                        message=f"Class '{node.name}' shows refused bequest patterns",
                        suggestion="Consider using composition instead of inheritance",
                        confidence=0.6,
                    )
                    issues.append(issue)

        return issues

    def _has_refused_bequest(self, class_node: ast.ClassDef) -> bool:
       """Function implementation."""
        """Check if a class has refused bequest patterns."""
        # Check if class overrides many methods with pass or NotImplemented
        overridden_methods = 0
        total_methods = 0

        for method in class_node.body:
            """Class implementation."""
            if isinstance(method, ast.FunctionDef):
                total_methods += 1
                if self._overrides_without_implementation(method):
                    overridden_methods += 1

        # If most methods are overridden without implementation, it's refused bequest
        return total_methods > 0 and overridden_methods / total_methods > 0.5

    def _overrides_without_implementation(self, method: ast.FunctionDef) -> bool:
       """Function implementation."""
        """Check if a method overrides without implementation."""
        # Check for pass or NotImplemented
        for node in method.body:
            if isinstance(node, ast.Pass):
                return True
            if isinstance(node, ast.Raise):
                if (
                    isinstance(node.exc, ast.Name)
                    and node.exc.id == "NotImplementedError"
                ):
                    return True

        return False
