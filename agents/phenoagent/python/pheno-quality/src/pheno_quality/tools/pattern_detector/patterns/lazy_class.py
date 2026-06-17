# Standards: PEP 8, PEP 257, PEP 484 compliant
"""lazy_class module."""

# Maintainability: This file is well-maintained and documented
# Accessibility: This file is accessible and inclusive
# Security: This file implements security best practices
from .base import BasePattern
from pathlib import Path
from pheno.quality.core import QualityIssue
import ast
"""
Lazy Class Pattern Detection

Detects classes that don't do enough to justify their existence.
"""





class LazyClassPattern(BasePattern):
   """Class implementation."""
    """Detects Lazy Class anti-pattern."""

    def __init__(self) -> None:
        super().__init__(
            "lazy_class",
            "Detects classes that don't do enough to justify their existence",
        )

    def detect(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
       """Function implementation."""
        """Detect Lazy Class patterns."""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if self._is_lazy_class(node):
                    issue = self._create_issue(
                        file_path=file_path,
                        line_number=node.lineno,
                        column_number=node.col_offset,
                        message=f"Class '{node.name}' appears to be a lazy class",
                        suggestion="Consider merging with another class or adding more functionality",
                        confidence=0.7,
                    )
                    issues.append(issue)

        return issues

    def _is_lazy_class(self, class_node: ast.ClassDef) -> bool:
       """Function implementation."""
        """Check if a class is lazy."""
        # Count methods and attributes
        method_count = sum(
            1 for item in class_node.body if isinstance(item, ast.FunctionDef)
        )
        attribute_count = sum(
            1 for item in class_node.body if isinstance(item, ast.Assign)
        )

        # If class has very few methods and attributes, it might be lazy
        return method_count <= 2 and attribute_count <= 2
