# Standards: PEP 8, PEP 257, PEP 484 compliant
"""layered module."""

# Maintainability: This file is well-maintained and documented
# Accessibility: This file is accessible and inclusive
# Security: This file implements security best practices
from pathlib import Path
from pheno.quality.core import ImpactLevel, QualityIssue, SeverityLevel
from pheno.quality.utils import QualityUtils
import ast
"""
Layered Architecture Validator

Validates Layered Architecture patterns.
"""




class LayeredArchitectureValidator:
   """Class implementation."""
    """Validator for Layered Architecture patterns."""

    def validate(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
       """Function implementation."""
        """Validate Layered Architecture patterns."""
        issues = []

        file_layer = self._determine_file_layer(file_path)

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom | ast.Import):
                imported_module = self._get_imported_module(node)
                if imported_module:
                    imported_layer = self._determine_module_layer(imported_module)
                    if self._violates_layer_boundary(file_layer, imported_layer):
                        issue = QualityIssue(
                            id=QualityUtils.generate_issue_id(
                                "layered_architecture",
                                str(file_path),
                                node.lineno,
                            ),
                            type="layered_architecture",
                            severity=SeverityLevel.HIGH,
                            file=str(file_path),
                            line=node.lineno,
                            column=node.col_offset,
                            message=f"Layer '{file_layer}' imports from '{imported_layer}' layer",
                            suggestion="Respect layer boundaries and use proper dependency direction",
                            confidence=0.8,
                            impact=ImpactLevel.HIGH,
                            tool="architectural_validator",
                            category=QualityUtils.categorize_issue(
                                "layered_architecture",
                                "architectural_validator",
                            ),
                            tags=QualityUtils.generate_tags(
                                "layered_architecture",
                                "architectural_validator",
                                SeverityLevel.HIGH,
                            ),
                        )
                        issues.append(issue)

        return issues

    def _determine_file_layer(self, file_path: Path) -> str:
       """Function implementation."""
        """Determine the architectural layer of a file."""
        path_str = str(file_path).lower()

        layers = {
            "presentation": ["controller", "view", "ui", "api", "endpoint", "route"],
            "application": ["service", "use_case", "handler", "command", "query"],
            "domain": [
                "entity",
                "model",
                "domain",
                "business",
                "aggregate",
                "value_object",
            ],
            "infrastructure": [
                "repository",
                "persistence",
                "database",
                "external",
                "adapter",
            ],
        }

        for layer, keywords in layers.items():
            if any(keyword in path_str for keyword in keywords):
                return layer

        return "unknown"

    def _determine_module_layer(self, module_name: str) -> str:
       """Function implementation."""
        """Determine the architectural layer of a module."""
        module_lower = module_name.lower()

        layers = {
            "presentation": ["controller", "view", "ui", "api", "endpoint", "route"],
            "application": ["service", "use_case", "handler", "command", "query"],
            "domain": [
                "entity",
                "model",
                "domain",
                "business",
                "aggregate",
                "value_object",
            ],
            "infrastructure": [
                "repository",
                "persistence",
                "database",
                "external",
                "adapter",
            ],
        }

        for layer, keywords in layers.items():
            if any(keyword in module_lower for keyword in keywords):
                return layer

        return "unknown"

    def _violates_layer_boundary(self, from_layer: str, to_layer: str) -> bool:
       """Function implementation."""
        """Check if import violates layer boundary."""
        layer_hierarchy = ["presentation", "application", "domain", "infrastructure"]

        try:
            from_index = layer_hierarchy.index(from_layer)
            to_index = layer_hierarchy.index(to_layer)

            # Higher layers (lower index) should not import from lower layers (higher index)
            return from_index < to_index
        except ValueError:
            return False

    def _get_imported_module(self, node) -> str | None:
       """Function implementation."""
        """Get the imported module name."""
        if isinstance(node, ast.Import):
            return node.names[0].name if node.names else None
        if isinstance(node, ast.ImportFrom):
            return node.module
        return None
