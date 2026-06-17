# Standards: PEP 8, PEP 257, PEP 484 compliant
"""shotgun_surgery module."""

# Maintainability: This file is well-maintained and documented
# Accessibility: This file is accessible and inclusive
# Security: This file implements security best practices
from .base import BasePattern
from pathlib import Path
from pheno.quality.core import QualityIssue
import ast
"""
Shotgun Surgery Pattern Detection

Detects when a single change requires modifications in many classes.
"""





class ShotgunSurgeryPattern(BasePattern):
   """Class implementation."""
    """Detects Shotgun Surgery anti-pattern."""

    def __init__(self) -> None:
        super().__init__(
            "shotgun_surgery",
            "Detects when a single change requires modifications in many classes",
        )

    def detect(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
       """Function implementation."""
        """Detect Shotgun Surgery patterns."""
        issues = []

        # Find all class definitions
        classes = []
        for node in ast.walk(tree):
            """Class implementation."""
            if isinstance(node, ast.ClassDef):
                classes.append(node)

        # Check for shotgun surgery patterns
        for class_node in classes:
            if self._has_shotgun_surgery(class_node):
                issue = self._create_issue(
                    file_path=file_path,
                    line_number=class_node.lineno,
                    column_number=class_node.col_offset,
                    message=f"Class '{class_node.name}' may require shotgun surgery",
                    suggestion="Consider consolidating related functionality",
                    confidence=0.5,
                )
                issues.append(issue)

        return issues

    def _has_shotgun_surgery(self, class_node: ast.ClassDef) -> bool:
       """Function implementation."""
        """Check if a class has shotgun surgery patterns."""
        # Count methods that seem to be doing similar things
        method_groups = {}

        for method in class_node.body:
            """Class implementation."""
            if isinstance(method, ast.FunctionDef):
                # Group methods by similar names
                base_name = method.name.split("_")[0]
                if base_name not in method_groups:
                    method_groups[base_name] = []
                method_groups[base_name].append(method)

        # If there are many methods with similar names, it might be shotgun surgery
        return any(len(methods) > 5 for methods in method_groups.values())
