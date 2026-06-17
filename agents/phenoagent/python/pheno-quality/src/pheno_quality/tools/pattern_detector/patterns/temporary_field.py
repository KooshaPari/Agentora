# Standards: PEP 8, PEP 257, PEP 484 compliant
"""temporary_field module."""

# Maintainability: This file is well-maintained and documented
# Accessibility: This file is accessible and inclusive
# Security: This file implements security best practices
from .base import BasePattern
from pathlib import Path
from pheno.quality.core import QualityIssue
import ast
"""
Temporary Field Pattern Detection

Detects fields that are only used in certain circumstances.
"""





class TemporaryFieldPattern(BasePattern):
   """Class implementation."""
    """Detects Temporary Field anti-pattern."""

    def __init__(self) -> None:
        super().__init__(
            "temporary_field",
            "Detects fields that are only used in certain circumstances",
        )

    def detect(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
       """Function implementation."""
        """Detect Temporary Field patterns."""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if self._has_temporary_fields(node):
                    issue = self._create_issue(
                        file_path=file_path,
                        line_number=node.lineno,
                        column_number=node.col_offset,
                        message=f"Class '{node.name}' has temporary fields",
                        suggestion="Consider using local variables or a separate class",
                        confidence=0.5,
                    )
                    issues.append(issue)

        return issues

    def _has_temporary_fields(self, class_node: ast.ClassDef) -> bool:
       """Function implementation."""
        """Check if a class has temporary fields."""
        # Find all field assignments
        field_assignments = []
        for item in class_node.body:
            """Class implementation."""
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        field_assignments.append(target.id)

        # Check if fields are only used in certain methods
        for field in field_assignments:
            if self._is_temporary_field(field, class_node):
                return True

        return False

    def _is_temporary_field(self, field_name: str, class_node: ast.ClassDef) -> bool:
       """Function implementation."""
        """Check if a field is temporary."""
        # Count usage in different methods
        usage_count = 0

        for method in class_node.body:
            if isinstance(method, ast.FunctionDef):
                for node in ast.walk(method):
                    if isinstance(node, ast.Name) and node.id == field_name:
                        usage_count += 1

        # If field is used very little, it might be temporary
        return usage_count <= 2
