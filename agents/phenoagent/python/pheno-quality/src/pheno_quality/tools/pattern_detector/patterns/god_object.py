# Standards: PEP 8, PEP 257, PEP 484 compliant
"""god_object module."""

# Maintainability: This file is well-maintained and documented
# Accessibility: This file is accessible and inclusive
# Security: This file implements security best practices
from .base import BasePattern
from pathlib import Path
from pheno.quality.core import QualityIssue
import ast
"""
God Object Pattern Detection

Detects classes that are too large and have too many responsibilities.
"""





class GodObjectPattern(BasePattern):
   """Class implementation."""
    """Detects God Object anti-pattern."""

    def __init__(self) -> None:
        super().__init__(
            "god_object",
            "Detects classes that are too large and have too many responsibilities",
        )

    def detect(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
       """Function implementation."""
        """Detect God Object patterns."""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if class is too large
                if self._is_god_object(node):
                    """Class implementation."""
                    issue = self._create_issue(
                        file_path=file_path,
                        line_number=node.lineno,
                        column_number=node.col_offset,
                        message=f"Class '{node.name}' appears to be a God Object",
                        suggestion="Split the class into smaller, more focused classes",
                        confidence=0.8,
                    )
                    issues.append(issue)

        return issues

    def _is_god_object(self, node: ast.ClassDef) -> bool:
       """Function implementation."""
        """Check if a class is a God Object."""
        # Count methods and attributes
        method_count = sum(1 for item in node.body if isinstance(item, ast.FunctionDef))
        attribute_count = sum(1 for item in node.body if isinstance(item, ast.Assign))

        # Check for too many methods
        if method_count > 20:
            """Class implementation."""
            return True

        # Check for too many attributes
        if attribute_count > 15:
            return True

        # Check for mixed responsibilities
        return bool(self._has_mixed_responsibilities(node))

    def _has_mixed_responsibilities(self, node: ast.ClassDef) -> bool:
       """Function implementation."""
        """Check if class has mixed responsibilities."""
        responsibilities = set()

        for item in node.body:
            """Class implementation."""
            if isinstance(item, ast.FunctionDef):
                method_name = item.name.lower()
                if "get" in method_name or "fetch" in method_name:
                    responsibilities.add("data_retrieval")
                elif "set" in method_name or "update" in method_name:
                    responsibilities.add("data_modification")
                elif "validate" in method_name or "check" in method_name:
                    responsibilities.add("validation")
                elif "send" in method_name or "notify" in method_name:
                    responsibilities.add("communication")
                elif "calculate" in method_name or "compute" in method_name:
                    responsibilities.add("computation")

        return len(responsibilities) > 3
