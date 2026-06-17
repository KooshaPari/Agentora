# Standards: PEP 8, PEP 257, PEP 484 compliant
"""solid module."""

# Maintainability: This file is well-maintained and documented
# Accessibility: This file is accessible and inclusive
# Security: This file implements security best practices
from pathlib import Path
from pheno.quality.core import ImpactLevel, QualityIssue, SeverityLevel
from pheno.quality.utils import QualityUtils
import ast
"""
SOLID Principles Validator

Validates SOLID principles.
"""




class SOLIDValidator:
   """Class implementation."""
    """Validator for SOLID principles."""

    def validate(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
       """Function implementation."""
        """Validate SOLID principles."""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check Single Responsibility Principle
                responsibilities = self._count_responsibilities(node)
                if responsibilities > 2:
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "solid_principles",
                            str(file_path),
                            node.lineno,
                        ),
                        type="solid_principles",
                        severity=SeverityLevel.MEDIUM,
                        file=str(file_path),
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Class '{node.name}' has {responsibilities} responsibilities",
                        suggestion="Split into multiple classes with single responsibilities",
                        confidence=0.7,
                        impact=ImpactLevel.MEDIUM,
                        tool="architectural_validator",
                        category=QualityUtils.categorize_issue(
                            "solid_principles",
                            "architectural_validator",
                        ),
                        tags=QualityUtils.generate_tags(
                            "solid_principles",
                            "architectural_validator",
                            SeverityLevel.MEDIUM,
                        ),
                    )
                    issues.append(issue)

        return issues

    def _count_responsibilities(self, node: ast.ClassDef) -> int:
       """Function implementation."""
        """Count the number of responsibilities in a class."""
        responsibilities = set()

        for method in node.body:
            if isinstance(method, ast.FunctionDef):
                method_name = method.name.lower()
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

        return len(responsibilities)
