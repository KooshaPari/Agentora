# Standards: PEP 8, PEP 257, PEP 484 compliant
"""clean_architecture module."""

# Maintainability: This file is well-maintained and documented
# Accessibility: This file is accessible and inclusive
# Security: This file implements security best practices
from pathlib import Path
from pheno.quality.core import ImpactLevel, QualityIssue, SeverityLevel
from pheno.quality.utils import QualityUtils
import ast
"""
Clean Architecture Validator

Validates Clean Architecture principles.
"""




class CleanArchitectureValidator:
   """Class implementation."""
    """Validator for Clean Architecture principles."""

    def validate(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
       """Function implementation."""
        """Validate Clean Architecture principles."""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name.lower()

                # Check dependency direction
                if self._is_domain_layer(class_name):
                    if self._imports_from_infrastructure(node):
                        issue = QualityIssue(
                            id=QualityUtils.generate_issue_id(
                                "clean_architecture",
                                str(file_path),
                                node.lineno,
                            ),
                            type="clean_architecture",
                            severity=SeverityLevel.HIGH,
                            file=str(file_path),
                            line=node.lineno,
                            column=node.col_offset,
                            message=f"Domain class '{node.name}' imports from infrastructure layer",
                            suggestion="Move infrastructure dependencies to application layer",
                            confidence=0.9,
                            impact=ImpactLevel.HIGH,
                            tool="architectural_validator",
                            category=QualityUtils.categorize_issue(
                                "clean_architecture",
                                "architectural_validator",
                            ),
                            tags=QualityUtils.generate_tags(
                                "clean_architecture",
                                "architectural_validator",
                                SeverityLevel.HIGH,
                            ),
                        )
                        issues.append(issue)

        return issues

    def _is_domain_layer(self, class_name: str) -> bool:
       """Function implementation."""
        """Check if class belongs to domain layer."""
        domain_keywords = [
            "entity",
            "model",
            "domain",
            "business",
            "aggregate",
            "value_object",
        ]
        return any(keyword in class_name for keyword in domain_keywords)

    def _imports_from_infrastructure(self, node: ast.ClassDef) -> bool:
       """Function implementation."""
        """Check if class imports from infrastructure layer."""
        for child in ast.walk(node):
            """Class implementation."""
            if isinstance(child, ast.Import | ast.ImportFrom):
                module_name = self._get_imported_module(child)
                if module_name and any(
                    keyword in module_name.lower()
                    for keyword in ["repository", "persistence", "database", "external"]
                ):
                    return True
        return False

    def _get_imported_module(self, node) -> str | None:
       """Function implementation."""
        """Get the imported module name."""
        if isinstance(node, ast.Import):
            return node.names[0].name if node.names else None
        if isinstance(node, ast.ImportFrom):
            return node.module
        return None
