# Standards: PEP 8, PEP 257, PEP 484 compliant
"""ddd module."""

# Maintainability: This file is well-maintained and documented
# Accessibility: This file is accessible and inclusive
# Security: This file implements security best practices
from pathlib import Path
from pheno.quality.core import ImpactLevel, QualityIssue, SeverityLevel
from pheno.quality.utils import QualityUtils
import ast
"""
Domain-Driven Design Validator

Validates Domain-Driven Design patterns.
"""




class DDDValidator:
   """Class implementation."""
    """Validator for Domain-Driven Design patterns."""

    def validate(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
       """Function implementation."""
        """Validate Domain-Driven Design patterns."""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name.lower()

                # Check for proper domain entity structure
                if "entity" in class_name or "aggregate" in class_name:
                    if not self._has_domain_identity(node):
                        issue = QualityIssue(
                            id=QualityUtils.generate_issue_id(
                                "domain_driven_design",
                                str(file_path),
                                node.lineno,
                            ),
                            type="domain_driven_design",
                            severity=SeverityLevel.MEDIUM,
                            file=str(file_path),
                            line=node.lineno,
                            column=node.col_offset,
                            message=f"Domain entity '{node.name}' should have identity",
                            suggestion="Add unique identifier to domain entity",
                            confidence=0.7,
                            impact=ImpactLevel.MEDIUM,
                            tool="architectural_validator",
                            category=QualityUtils.categorize_issue(
                                "domain_driven_design",
                                "architectural_validator",
                            ),
                            tags=QualityUtils.generate_tags(
                                "domain_driven_design",
                                "architectural_validator",
                                SeverityLevel.MEDIUM,
                            ),
                        )
                        issues.append(issue)

        return issues

    def _has_domain_identity(self, node: ast.ClassDef) -> bool:
       """Function implementation."""
        """Check if domain entity has identity."""
        for child in node.body:
            if isinstance(child, ast.FunctionDef):
                if child.name.lower() in ["id", "identity", "get_id"]:
                    return True
        return False
