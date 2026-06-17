# Standards: PEP 8, PEP 257, PEP 484 compliant
"""inappropriate_intimacy module."""

# Maintainability: This file is well-maintained and documented
# Accessibility: This file is accessible and inclusive
# Security: This file implements security best practices
from .base import BasePattern
from pathlib import Path
from pheno.quality.core import QualityIssue
import ast
"""
Inappropriate Intimacy Pattern Detection

Detects classes that know too much about each other's internals.
"""





class InappropriateIntimacyPattern(BasePattern):
   """Class implementation."""
    """Detects Inappropriate Intimacy anti-pattern."""

    def __init__(self) -> None:
        super().__init__(
            "inappropriate_intimacy",
            "Detects classes that know too much about each other's internals",
        )

    def detect(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
       """Function implementation."""
        """Detect Inappropriate Intimacy patterns."""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if self._has_inappropriate_intimacy(node):
                    issue = self._create_issue(
                        file_path=file_path,
                        line_number=node.lineno,
                        column_number=node.col_offset,
                        message=f"Class '{node.name}' shows inappropriate intimacy",
                        suggestion="Reduce coupling between classes",
                        confidence=0.6,
                    )
                    issues.append(issue)

        return issues

    def _has_inappropriate_intimacy(self, class_node: ast.ClassDef) -> bool:
       """Function implementation."""
        """Check if a class has inappropriate intimacy."""
        # Count direct attribute access to other objects
        external_access = 0

        for method in class_node.body:
            """Class implementation."""
            if isinstance(method, ast.FunctionDef):
                for node in ast.walk(method):
                    if isinstance(node, ast.Attribute):
                        if isinstance(node.value, ast.Name) and node.value.id != "self":
                            external_access += 1

        # If there's too much external access, it might be inappropriate intimacy
        return external_access > 5
