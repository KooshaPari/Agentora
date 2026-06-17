"""
Architecture validation and compliance checking.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pheno.logging.core.logger import get_logger

from .models import (
    LayerType,
    PatternMatch,
    SeverityLevel,
)

if TYPE_CHECKING:
    from pathlib import Path

logger = get_logger("pheno.analytics.architecture.validator")


@dataclass(slots=True)
class ArchitectureValidatorConfig:
    """
    Configuration for architecture validation.
    """

    # Validation rules
    enforce_layer_boundaries: bool = True
    enforce_dependency_direction: bool = True
    enforce_solid_principles: bool = True
    enforce_hexagonal_architecture: bool = False
    enforce_clean_architecture: bool = False

    # Thresholds
    max_responsibilities_per_class: int = 2
    max_parameters_per_method: int = 5
    max_methods_per_class: int = 20
    max_cyclomatic_complexity: int = 10

    # Layer hierarchy (higher index = lower layer)
    layer_hierarchy: list[LayerType] = None

    def __post_init__(self):
        if self.layer_hierarchy is None:
            self.layer_hierarchy = [
                LayerType.PRESENTATION,
                LayerType.APPLICATION,
                LayerType.DOMAIN,
                LayerType.INFRASTRUCTURE,
            ]


class ArchitectureValidator:
    """
    Validates architecture compliance and best practices.
    """

    def __init__(self, config: ArchitectureValidatorConfig | None = None):
        self.config = config or ArchitectureValidatorConfig()
        self._violations: list[PatternMatch] = []

    def validate_file(self, file_path: Path) -> list[PatternMatch]:
        """
        Validate a single file for architecture compliance.
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            violations = []

            # Run all validation checks
            if self.config.enforce_layer_boundaries:
                violations.extend(self._validate_layer_boundaries(tree, file_path))

            if self.config.enforce_dependency_direction:
                violations.extend(self._validate_dependency_direction(tree, file_path))

            if self.config.enforce_solid_principles:
                violations.extend(self._validate_solid_principles(tree, file_path))

            if self.config.enforce_hexagonal_architecture:
                violations.extend(self._validate_hexagonal_architecture(tree, file_path))

            if self.config.enforce_clean_architecture:
                violations.extend(self._validate_clean_architecture(tree, file_path))

            # Additional quality checks
            violations.extend(self._validate_code_quality(tree, file_path))

            self._violations.extend(violations)
            return violations

        except Exception as e:
            logger.exception(f"Failed to validate file {file_path}: {e}")
            return []

    def validate_directory(self, directory_path: Path) -> list[PatternMatch]:
        """
        Validate a directory for architecture compliance.
        """
        all_violations = []

        for file_path in directory_path.rglob("*.py"):
            if self._should_validate_file(file_path):
                file_violations = self.validate_file(file_path)
                all_violations.extend(file_violations)

        return all_violations

    def _should_validate_file(self, file_path: Path) -> bool:
        """
        Check if a file should be validated.
        """
        # Skip test files for now (can be made configurable)
        if "test" in str(file_path).lower():
            return False

        # Skip __init__.py files
        return file_path.name != "__init__.py"

    def _validate_layer_boundaries(self, tree: ast.AST, file_path: Path) -> list[PatternMatch]:
        """
        Validate that layer boundaries are respected.
        """
        violations = []
        file_layer = self._determine_file_layer(file_path)

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imported_module = self._get_imported_module(node)
                if imported_module:
                    imported_layer = self._determine_module_layer(imported_module)
                    if self._violates_layer_boundary(file_layer, imported_layer):
                        violations.append(
                            PatternMatch(
                                pattern_name="layer_boundary_violation",
                                pattern_type="architectural",
                                file_path=file_path,
                                line_number=node.lineno,
                                column=node.col_offset,
                                confidence=0.9,
                                description=f"Layer '{file_layer.value}' imports from '{imported_layer.value}' layer",
                                suggestion="Respect layer boundaries and use proper dependency direction",
                                severity=SeverityLevel.HIGH,
                                tags={"architecture", "layer", "boundary", "violation"},
                            ),
                        )

        return violations

    def _validate_dependency_direction(self, tree: ast.AST, file_path: Path) -> list[PatternMatch]:
        """
        Validate dependency direction follows architectural principles.
        """
        violations = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name.lower()

                # Check if domain class imports from infrastructure
                if self._is_domain_class(class_name):
                    if self._imports_from_infrastructure(node):
                        violations.append(
                            PatternMatch(
                                pattern_name="dependency_direction_violation",
                                pattern_type="architectural",
                                file_path=file_path,
                                line_number=node.lineno,
                                column=node.col_offset,
                                confidence=0.8,
                                description=f"Domain class '{node.name}' imports from infrastructure layer",
                                suggestion="Move infrastructure dependencies to application layer",
                                severity=SeverityLevel.HIGH,
                                tags={"architecture", "dependency", "direction", "violation"},
                            ),
                        )

        return violations

    def _validate_solid_principles(self, tree: ast.AST, file_path: Path) -> list[PatternMatch]:
        """
        Validate SOLID principles compliance.
        """
        violations = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Single Responsibility Principle
                responsibilities = self._count_responsibilities(node)
                if responsibilities > self.config.max_responsibilities_per_class:
                    violations.append(
                        PatternMatch(
                            pattern_name="single_responsibility_violation",
                            pattern_type="solid",
                            file_path=file_path,
                            line_number=node.lineno,
                            column=node.col_offset,
                            confidence=0.7,
                            description=f"Class '{node.name}' has {responsibilities} responsibilities",
                            suggestion="Split into multiple classes with single responsibilities",
                            severity=SeverityLevel.MEDIUM,
                            tags={"solid", "srp", "responsibility"},
                        ),
                    )

                # Open/Closed Principle - check for switch statements or if-else chains
                if self._violates_open_closed_principle(node):
                    violations.append(
                        PatternMatch(
                            pattern_name="open_closed_violation",
                            pattern_type="solid",
                            file_path=file_path,
                            line_number=node.lineno,
                            column=node.col_offset,
                            confidence=0.6,
                            description=f"Class '{node.name}' may violate Open/Closed principle",
                            suggestion="Use polymorphism or strategy pattern instead of conditionals",
                            severity=SeverityLevel.MEDIUM,
                            tags={"solid", "ocp", "open_closed"},
                        ),
                    )

            elif isinstance(node, ast.FunctionDef):
                # Interface Segregation - check for too many parameters
                param_count = len(node.args.args)
                if param_count > self.config.max_parameters_per_method:
                    violations.append(
                        PatternMatch(
                            pattern_name="interface_segregation_violation",
                            pattern_type="solid",
                            file_path=file_path,
                            line_number=node.lineno,
                            column=node.col_offset,
                            confidence=0.6,
                            description=f"Function '{node.name}' has {param_count} parameters",
                            suggestion="Consider using parameter objects or splitting the function",
                            severity=SeverityLevel.MEDIUM,
                            tags={"solid", "isp", "interface_segregation"},
                        ),
                    )

        return violations

    def _validate_hexagonal_architecture(
        self, tree: ast.AST, file_path: Path,
    ) -> list[PatternMatch]:
        """
        Validate Hexagonal Architecture patterns.
        """
        violations = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name.lower()

                # Check for adapter classes implementing proper interfaces
                if "adapter" in class_name or "repository" in class_name:
                    if not self._implements_interface(node):
                        violations.append(
                            PatternMatch(
                                pattern_name="hexagonal_architecture_violation",
                                pattern_type="architectural",
                                file_path=file_path,
                                line_number=node.lineno,
                                column=node.col_offset,
                                confidence=0.7,
                                description=f"Adapter class '{node.name}' should implement an interface",
                                suggestion="Define and implement a proper port interface",
                                severity=SeverityLevel.MEDIUM,
                                tags={"hexagonal", "adapter", "interface"},
                            ),
                        )

                # Check for port definitions
                if "port" in class_name or "interface" in class_name:
                    if not self._is_proper_port_definition(node):
                        violations.append(
                            PatternMatch(
                                pattern_name="hexagonal_port_violation",
                                pattern_type="architectural",
                                file_path=file_path,
                                line_number=node.lineno,
                                column=node.col_offset,
                                confidence=0.6,
                                description=f"Port class '{node.name}' should be abstract or interface",
                                suggestion="Use ABC or Protocol for port definitions",
                                severity=SeverityLevel.MEDIUM,
                                tags={"hexagonal", "port", "interface"},
                            ),
                        )

        return violations

    def _validate_clean_architecture(self, tree: ast.AST, file_path: Path) -> list[PatternMatch]:
        """
        Validate Clean Architecture principles.
        """
        violations = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name.lower()

                # Check dependency direction
                if self._is_domain_layer(class_name):
                    if self._imports_from_infrastructure(node):
                        violations.append(
                            PatternMatch(
                                pattern_name="clean_architecture_violation",
                                pattern_type="architectural",
                                file_path=file_path,
                                line_number=node.lineno,
                                column=node.col_offset,
                                confidence=0.9,
                                description=f"Domain class '{node.name}' imports from infrastructure layer",
                                suggestion="Move infrastructure dependencies to application layer",
                                severity=SeverityLevel.HIGH,
                                tags={"clean_architecture", "dependency", "direction"},
                            ),
                        )

                # Check for proper entity structure
                if "entity" in class_name or "aggregate" in class_name:
                    if not self._has_domain_identity(node):
                        violations.append(
                            PatternMatch(
                                pattern_name="clean_entity_violation",
                                pattern_type="architectural",
                                file_path=file_path,
                                line_number=node.lineno,
                                column=node.col_offset,
                                confidence=0.7,
                                description=f"Domain entity '{node.name}' should have identity",
                                suggestion="Add unique identifier to domain entity",
                                severity=SeverityLevel.MEDIUM,
                                tags={"clean_architecture", "entity", "identity"},
                            ),
                        )

        return violations

    def _validate_code_quality(self, tree: ast.AST, file_path: Path) -> list[PatternMatch]:
        """
        Validate general code quality metrics.
        """
        violations = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check class size
                method_count = len([n for n in node.body if isinstance(n, ast.FunctionDef)])
                if method_count > self.config.max_methods_per_class:
                    violations.append(
                        PatternMatch(
                            pattern_name="class_size_violation",
                            pattern_type="quality",
                            file_path=file_path,
                            line_number=node.lineno,
                            column=node.col_offset,
                            confidence=0.8,
                            description=f"Class '{node.name}' has {method_count} methods",
                            suggestion="Consider splitting into smaller classes",
                            severity=SeverityLevel.MEDIUM,
                            tags={"quality", "size", "class"},
                        ),
                    )

            elif isinstance(node, ast.FunctionDef):
                # Check cyclomatic complexity
                complexity = self._calculate_cyclomatic_complexity(node)
                if complexity > self.config.max_cyclomatic_complexity:
                    violations.append(
                        PatternMatch(
                            pattern_name="complexity_violation",
                            pattern_type="quality",
                            file_path=file_path,
                            line_number=node.lineno,
                            column=node.col_offset,
                            confidence=0.8,
                            description=f"Function '{node.name}' has high cyclomatic complexity ({complexity})",
                            suggestion="Simplify the function by extracting smaller functions",
                            severity=SeverityLevel.MEDIUM,
                            tags={"quality", "complexity", "function"},
                        ),
                    )

        return violations

    # Helper methods

    def _determine_file_layer(self, file_path: Path) -> LayerType:
        """
        Determine the architectural layer of a file.
        """
        path_str = str(file_path).lower()

        layer_keywords = {
            LayerType.PRESENTATION: ["controller", "view", "ui", "api", "endpoint", "route"],
            LayerType.APPLICATION: ["service", "use_case", "handler", "command", "query"],
            LayerType.DOMAIN: [
                "entity",
                "model",
                "domain",
                "business",
                "aggregate",
                "value_object",
            ],
            LayerType.INFRASTRUCTURE: [
                "repository",
                "persistence",
                "database",
                "external",
                "adapter",
            ],
            LayerType.PORTS: ["ports", "interface", "contract"],
            LayerType.ADAPTERS: ["adapters", "adapter", "implementation"],
        }

        for layer, keywords in layer_keywords.items():
            if any(keyword in path_str for keyword in keywords):
                return layer

        return LayerType.APPLICATION  # Default

    def _determine_module_layer(self, module_name: str) -> LayerType:
        """
        Determine the architectural layer of a module.
        """
        module_lower = module_name.lower()

        layer_keywords = {
            LayerType.PRESENTATION: ["controller", "view", "ui", "api", "endpoint", "route"],
            LayerType.APPLICATION: ["service", "use_case", "handler", "command", "query"],
            LayerType.DOMAIN: [
                "entity",
                "model",
                "domain",
                "business",
                "aggregate",
                "value_object",
            ],
            LayerType.INFRASTRUCTURE: [
                "repository",
                "persistence",
                "database",
                "external",
                "adapter",
            ],
            LayerType.PORTS: ["ports", "interface", "contract"],
            LayerType.ADAPTERS: ["adapters", "adapter", "implementation"],
        }

        for layer, keywords in layer_keywords.items():
            if any(keyword in module_lower for keyword in keywords):
                return layer

        return LayerType.APPLICATION  # Default

    def _violates_layer_boundary(self, from_layer: LayerType, to_layer: LayerType) -> bool:
        """
        Check if import violates layer boundary.
        """
        try:
            from_index = self.config.layer_hierarchy.index(from_layer)
            to_index = self.config.layer_hierarchy.index(to_layer)

            # Higher layers (lower index) should not import from lower layers (higher index)
            return from_index < to_index
        except ValueError:
            return False

    def _is_domain_class(self, class_name: str) -> bool:
        """
        Check if class belongs to domain layer.
        """
        domain_keywords = ["entity", "model", "domain", "business", "aggregate", "value_object"]
        return any(keyword in class_name for keyword in domain_keywords)

    def _is_domain_layer(self, class_name: str) -> bool:
        """
        Check if class belongs to domain layer.
        """
        return self._is_domain_class(class_name)

    def _imports_from_infrastructure(self, node: ast.ClassDef) -> bool:
        """
        Check if class imports from infrastructure layer.
        """
        for child in ast.walk(node):
            if isinstance(child, (ast.Import, ast.ImportFrom)):
                module_name = self._get_imported_module(child)
                if module_name and any(
                    keyword in module_name.lower()
                    for keyword in ["repository", "persistence", "database", "external"]
                ):
                    return True
        return False

    def _count_responsibilities(self, node: ast.ClassDef) -> int:
        """
        Count the number of responsibilities in a class.
        """
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
                elif "save" in method_name or "persist" in method_name:
                    responsibilities.add("persistence")
                elif "delete" in method_name or "remove" in method_name:
                    responsibilities.add("deletion")

        return len(responsibilities)

    def _violates_open_closed_principle(self, node: ast.ClassDef) -> bool:
        """
        Check if class violates Open/Closed principle.
        """
        for method in node.body:
            if isinstance(method, ast.FunctionDef):
                # Look for long if-else chains or switch-like patterns
                if self._has_long_conditional_chain(method):
                    return True
        return False

    def _has_long_conditional_chain(self, node: ast.FunctionDef) -> bool:
        """
        Check if function has long conditional chains.
        """
        conditional_count = 0

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.IfExp)):
                conditional_count += 1
                if conditional_count > 5:  # Threshold for long chains
                    return True

        return False

    def _implements_interface(self, node: ast.ClassDef) -> bool:
        """
        Check if class implements an interface.
        """
        for base in node.bases:
            if isinstance(base, ast.Name):
                if "interface" in base.id.lower() or "protocol" in base.id.lower():
                    return True
        return False

    def _is_proper_port_definition(self, node: ast.ClassDef) -> bool:
        """
        Check if class is a proper port definition.
        """
        # Check if it's abstract or has abstract methods
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "abstractmethod":
                return True

        # Check if it inherits from ABC
        for base in node.bases:
            if isinstance(base, ast.Name) and "ABC" in base.id:
                return True

        return False

    def _has_domain_identity(self, node: ast.ClassDef) -> bool:
        """
        Check if domain entity has identity.
        """
        for child in node.body:
            if isinstance(child, ast.FunctionDef):
                if child.name.lower() in ["id", "identity", "get_id"]:
                    return True
        return False

    def _calculate_cyclomatic_complexity(self, node: ast.FunctionDef) -> int:
        """
        Calculate cyclomatic complexity of a function.
        """
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1

        return complexity

    def _get_imported_module(self, node) -> str | None:
        """
        Get the imported module name.
        """
        if isinstance(node, ast.Import):
            return node.names[0].name if node.names else None
        if isinstance(node, ast.ImportFrom):
            return node.module
        return None
