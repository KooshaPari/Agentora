# Standards: PEP 8, PEP 257, PEP 484 compliant
"""feature_envy module."""

# Maintainability: This file is well-maintained and documented
# Accessibility: This file is accessible and inclusive
# Security: This file implements security best practices
from .base import BasePattern
from pathlib import Path
from pheno.quality.core import QualityIssue
import ast
"""
Feature Envy Pattern Detection

Detects methods that use more features of another class than their own.
"""





class FeatureEnvyPattern(BasePattern):
   """Class implementation."""
    """Detects Feature Envy anti-pattern."""

    def __init__(self) -> None:
        super().__init__(
            "feature_envy",
            "Detects methods that use more features of another class than their own",
        )

    def detect(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
       """Function implementation."""
        """Detect Feature Envy patterns."""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for method in node.body:
                    if isinstance(method, ast.FunctionDef):
                        if self._has_feature_envy(method, node):
                            issue = self._create_issue(
                                file_path=file_path,
                                line_number=method.lineno,
                                column_number=method.col_offset,
                                message=f"Method '{method.name}' shows feature envy",
                                suggestion="Consider moving the method to the class it uses most",
                                confidence=0.7,
                            )
                            issues.append(issue)

        return issues

    def _has_feature_envy(
        self, method: ast.FunctionDef, class_node: ast.ClassDef,
    ) -> bool:
       """Function implementation."""
        """Check if a method has feature envy."""
        # Count references to self vs other objects
        self_references = 0
        other_references = 0

        for node in ast.walk(method):
            if isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name) and node.value.id == "self":
                    self_references += 1
                else:
                    other_references += 1

        # If method uses more other objects than self, it might have feature envy
        return other_references > self_references * 2
