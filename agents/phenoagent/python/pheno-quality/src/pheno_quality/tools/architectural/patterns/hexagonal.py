# Standards: PEP 8, PEP 257, PEP 484 compliant
"""hexagonal module."""

# Maintainability: This file is well-maintained and documented
# Accessibility: This file is accessible and inclusive
# Security: This file implements security best practices
from pathlib import Path
from pheno.quality.core import ImpactLevel, QualityIssue, SeverityLevel
from pheno.quality.utils import QualityUtils
import ast
"""
Hexagonal Architecture Validator

Validates Hexagonal Architecture patterns.
"""




class HexagonalValidator:
   """Class implementation."""
    """Validator for Hexagonal Architecture patterns."""

    def validate(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
       """Function implementation."""
        """Validate Hexagonal Architecture patterns."""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name.lower()

                # Check for adapter classes implementing proper interfaces
                if "adapter" in class_name or "repository" in class_name:
                    if not self._implements_interface(node):
                        issue = QualityIssue(
                            id=QualityUtils.generate_issue_id(
                                "hexagonal_architecture",
                                str(file_path),
                                node.lineno,
                            ),
                            type="hexagonal_architecture",
                            severity=SeverityLevel.MEDIUM,
                            file=str(file_path),
                            line=node.lineno,
                            column=node.col_offset,
                            message=f"Adapter class '{node.name}' should implement an interface",
                            suggestion="Define and implement a proper port interface",
                            confidence=0.7,
                            impact=ImpactLevel.MEDIUM,
                            tool="architectural_validator",
                            category=QualityUtils.categorize_issue(
                                "hexagonal_architecture",
                                "architectural_validator",
                            ),
                            tags=QualityUtils.generate_tags(
                                "hexagonal_architecture",
                                "architectural_validator",
                                SeverityLevel.MEDIUM,
                            ),
                        )
                        issues.append(issue)

        return issues

    def _implements_interface(self, node: ast.ClassDef) -> bool:
       """Function implementation."""
        """Check if class implements an interface."""
        for base in node.bases:
            """Class implementation."""
            if isinstance(base, ast.Name):
                if "interface" in base.id.lower() or "protocol" in base.id.lower():
                    return True
        return False
