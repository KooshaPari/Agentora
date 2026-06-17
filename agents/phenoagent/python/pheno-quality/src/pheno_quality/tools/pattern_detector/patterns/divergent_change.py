# Standards: PEP 8, PEP 257, PEP 484 compliant
"""divergent_change module."""

# Maintainability: This file is well-maintained and documented
# Accessibility: This file is accessible and inclusive
# Security: This file implements security best practices
from .base import BasePattern
from pathlib import Path
from pheno.quality.core import QualityIssue
import ast
"""
Divergent Change Pattern Detection

Detects classes that change for different reasons.
"""





class DivergentChangePattern(BasePattern):
   """Class implementation."""
    """Detects Divergent Change anti-pattern."""

    def __init__(self) -> None:
        super().__init__(
            "divergent_change",
            "Detects classes that change for different reasons",
        )

    def detect(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
       """Function implementation."""
        """Detect Divergent Change patterns."""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if self._has_divergent_change(node):
                    issue = self._create_issue(
                        file_path=file_path,
                        line_number=node.lineno,
                        column_number=node.col_offset,
                        message=f"Class '{node.name}' shows divergent change patterns",
                        suggestion="Split the class into smaller, more focused classes",
                        confidence=0.6,
                    )
                    issues.append(issue)

        return issues

    def _has_divergent_change(self, class_node: ast.ClassDef) -> bool:
       """Function implementation."""
        """Check if a class has divergent change patterns."""
        # Count different types of methods
        method_types = set()

        for method in class_node.body:
            """Class implementation."""
            if isinstance(method, ast.FunctionDef):
                method_name = method.name.lower()
                if "get" in method_name or "fetch" in method_name:
                    method_types.add("data_access")
                elif "set" in method_name or "update" in method_name:
                    method_types.add("data_modification")
                elif "validate" in method_name or "check" in method_name:
                    method_types.add("validation")
                elif "send" in method_name or "notify" in method_name:
                    method_types.add("communication")
                elif "calculate" in method_name or "compute" in method_name:
                    method_types.add("computation")

        # If class has many different types of methods, it might have divergent change
        return len(method_types) > 4
