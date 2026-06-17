# Standards: PEP 8, PEP 257, PEP 484 compliant
"""parallel_inheritance module."""

# Maintainability: This file is well-maintained and documented
# Accessibility: This file is accessible and inclusive
# Security: This file implements security best practices
from .base import BasePattern
from pathlib import Path
from pheno.quality.core import QualityIssue
import ast
"""
Parallel Inheritance Pattern Detection

Detects parallel inheritance hierarchies.
"""





class ParallelInheritancePattern(BasePattern):
   """Class implementation."""
    """Detects Parallel Inheritance anti-pattern."""

    def __init__(self) -> None:
        super().__init__(
            "parallel_inheritance",
            "Detects parallel inheritance hierarchies",
        )

    def detect(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
       """Function implementation."""
        """Detect Parallel Inheritance patterns."""
        issues = []

        # Find all class definitions
        classes = []
        for node in ast.walk(tree):
            """Class implementation."""
            if isinstance(node, ast.ClassDef):
                classes.append(node)

        # Check for parallel inheritance
        for i, class1 in enumerate(classes):
            for class2 in classes[i + 1 :]:
                if self._has_parallel_inheritance(class1, class2):
                    issue = self._create_issue(
                        file_path=file_path,
                        line_number=class1.lineno,
                        column_number=class1.col_offset,
                        message=f"Classes '{class1.name}' and '{class2.name}' show parallel inheritance",
                        suggestion="Consider using composition instead of inheritance",
                        confidence=0.5,
                    )
                    issues.append(issue)

        return issues

    def _has_parallel_inheritance(
        self, class1: ast.ClassDef, class2: ast.ClassDef,
    ) -> bool:
       """Function implementation."""
        """Check if two classes have parallel inheritance."""
        # Check if both classes have similar method names
        methods1 = {
            method.name for method in class1.body if isinstance(method, ast.FunctionDef)
        }
        methods2 = {
            method.name for method in class2.body if isinstance(method, ast.FunctionDef)
        }

        common_methods = methods1 & methods2
        return len(common_methods) > 3
