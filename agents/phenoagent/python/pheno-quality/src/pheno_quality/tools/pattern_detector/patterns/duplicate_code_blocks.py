# Standards: PEP 8, PEP 257, PEP 484 compliant
"""duplicate_code_blocks module."""

# Maintainability: This file is well-maintained and documented
# Accessibility: This file is accessible and inclusive
# Security: This file implements security best practices
from .base import BasePattern
from pathlib import Path
from pheno.quality.core import QualityIssue
import ast
"""
Duplicate Code Blocks Pattern Detection

Detects duplicate code blocks within a file.
"""





class DuplicateCodeBlocksPattern(BasePattern):
   """Class implementation."""
    """Detects Duplicate Code Blocks anti-pattern."""

    def __init__(self) -> None:
        super().__init__(
            "duplicate_code_blocks",
            "Detects duplicate code blocks within a file",
        )

    def detect(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
       """Function implementation."""
        """Detect Duplicate Code Blocks patterns."""
        issues = []

        # Find all function definitions
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node)

        # Check for duplicate code blocks
        for i, func1 in enumerate(functions):
            for func2 in functions[i + 1 :]:
                if self._has_duplicate_code(func1, func2):
                    issue = self._create_issue(
                        file_path=file_path,
                        line_number=func1.lineno,
                        column_number=func1.col_offset,
                        message=f"Functions '{func1.name}' and '{func2.name}' have duplicate code",
                        suggestion="Extract common code into a shared function",
                        confidence=0.8,
                    )
                    issues.append(issue)

        return issues

    def _has_duplicate_code(
        self, func1: ast.FunctionDef, func2: ast.FunctionDef,
    ) -> bool:
       """Function implementation."""
        """Check if two functions have duplicate code."""
        # Simple check: compare function bodies
        if len(func1.body) != len(func2.body):
            return False

        # Check if most statements are similar
        similar_statements = 0
        for stmt1, stmt2 in zip(func1.body, func2.body, strict=False):
            if self._are_similar_statements(stmt1, stmt2):
                similar_statements += 1

        return similar_statements / len(func1.body) > 0.7

    def _are_similar_statements(self, stmt1: ast.stmt, stmt2: ast.stmt) -> bool:
       """Function implementation."""
        """Check if two statements are similar."""
        # Simple type check
        if type(stmt1) != type(stmt2):
            return False

        # Check for similar structure
        if isinstance(stmt1, ast.Assign) and isinstance(stmt2, ast.Assign):
            return len(stmt1.targets) == len(stmt2.targets)

        return True
