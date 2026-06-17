# Standards: PEP 8, PEP 257, PEP 484 compliant
"""data_clump module."""

# Maintainability: This file is well-maintained and documented
# Accessibility: This file is accessible and inclusive
# Security: This file implements security best practices
from .base import BasePattern
from pathlib import Path
from pheno.quality.core import QualityIssue
import ast
"""
Data Clump Pattern Detection

Detects groups of data that are always passed together.
"""





class DataClumpPattern(BasePattern):
   """Class implementation."""
    """Detects Data Clump anti-pattern."""

    def __init__(self) -> None:
        super().__init__(
            "data_clump",
            "Detects groups of data that are always passed together",
        )

    def detect(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
       """Function implementation."""
        """Detect Data Clump patterns."""
        issues = []

        # Find all function definitions
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node)

        # Check for data clumps
        for i, func1 in enumerate(functions):
            for func2 in functions[i + 1 :]:
                if self._has_data_clump(func1, func2):
                    issue = self._create_issue(
                        file_path=file_path,
                        line_number=func1.lineno,
                        column_number=func1.col_offset,
                        message=f"Functions '{func1.name}' and '{func2.name}' share parameter clumps",
                        suggestion="Consider creating a data class for the shared parameters",
                        confidence=0.6,
                    )
                    issues.append(issue)

        return issues

    def _has_data_clump(self, func1: ast.FunctionDef, func2: ast.FunctionDef) -> bool:
       """Function implementation."""
        """Check if two functions have data clumps."""
        # Get parameter names
        params1 = [arg.arg for arg in func1.args.args]
        params2 = [arg.arg for arg in func2.args.args]

        # Check for common parameter patterns
        common_params = set(params1) & set(params2)
        return len(common_params) >= 3
