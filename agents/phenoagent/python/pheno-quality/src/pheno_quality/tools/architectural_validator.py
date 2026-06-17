"""
Architectural pattern validation tool implementation.
"""

import ast
from pathlib import Path
from typing import Any

from ..core import (
    ImpactLevel,
    QualityAnalyzer,
    QualityConfig,
    QualityIssue,
    SeverityLevel,
)
from ..plugins import QualityPlugin
from ..utils import QualityUtils


class ArchitecturalValidator(QualityAnalyzer):
    """
    Architectural pattern validation tool.
    """

    def __init__(
        self, name: str = "architectural_validator", config: QualityConfig | None = None,
    ):
        super().__init__(name, config)
        self.patterns = {
            "hexagonal_architecture": self._validate_hexagonal_architecture,
            "clean_architecture": self._validate_clean_architecture,
            "solid_principles": self._validate_solid_principles,
            "layered_architecture": self._validate_layered_architecture,
            "domain_driven_design": self._validate_domain_driven_design,
            "microservices_patterns": self._validate_microservices_patterns,
        }

    def analyze_file(self, file_path: Path) -> list[QualityIssue]:
        """
        Analyze a single file for architectural patterns.
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            file_issues = []

            for validator_func in self.patterns.values():
                issues = validator_func(tree, file_path)
                file_issues.extend(issues)

            self.issues.extend(file_issues)
            return file_issues

        except Exception as e:
            error_issue = QualityIssue(
                id=QualityUtils.generate_issue_id("parse_error", str(file_path), 0),
                type="parse_error",
                severity=SeverityLevel.HIGH,
                file=str(file_path),
                line=0,
                column=0,
                message=f"Failed to parse file: {e!s}",
                suggestion="Check file syntax and encoding",
                confidence=1.0,
                impact=ImpactLevel.HIGH,
                tool=self.name,
                category="Parsing",
                tags=["error", "parsing"],
            )
            self.issues.append(error_issue)
            return [error_issue]

    def analyze_directory(self, directory_path: Path) -> list[QualityIssue]:
        """
        Analyze a directory for architectural patterns.
        """
        all_issues = []

        for file_path in directory_path.rglob("*.py"):
            if self._should_analyze_file(file_path):
                file_issues = self.analyze_file(file_path)
                all_issues.extend(file_issues)

        return all_issues

    def _should_analyze_file(self, file_path: Path) -> bool:
        """
        Check if file should be analyzed.
        """
        exclude_patterns = self.config.filters.get("exclude_patterns", [])
        return not QualityUtils.should_exclude_file(str(file_path), exclude_patterns)

    def _validate_hexagonal_architecture(
        self, tree: ast.AST, file_path: Path,
    ) -> list[QualityIssue]:
        """
        Validate Hexagonal Architecture patterns.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name.lower()

                # Check for adapter classes implementing proper interfaces
                if "adapter" in class_name or "repository" in class_name:
                    if not self._implements_interface(node):
                        issue = QualityIssue(
                            id=QualityUtils.generate_issue_id(
                                "hexagonal_architecture", str(file_path), node.lineno,
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
                            tool=self.name,
                            category=QualityUtils.categorize_issue(
                                "hexagonal_architecture", self.name,
                            ),
                            tags=QualityUtils.generate_tags(
                                "hexagonal_architecture", self.name, SeverityLevel.MEDIUM,
                            ),
                        )
                        issues.append(issue)

        return issues

    def _validate_clean_architecture(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Validate Clean Architecture principles.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name.lower()

                # Check dependency direction
                if self._is_domain_layer(class_name):
                    if self._imports_from_infrastructure(node):
                        issue = QualityIssue(
                            id=QualityUtils.generate_issue_id(
                                "clean_architecture", str(file_path), node.lineno,
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
                            tool=self.name,
                            category=QualityUtils.categorize_issue("clean_architecture", self.name),
                            tags=QualityUtils.generate_tags(
                                "clean_architecture", self.name, SeverityLevel.HIGH,
                            ),
                        )
                        issues.append(issue)

        return issues

    def _validate_solid_principles(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Validate SOLID principles.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check Single Responsibility Principle
                responsibilities = self._count_responsibilities(node)
                if responsibilities > 2:
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "solid_principles", str(file_path), node.lineno,
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
                        tool=self.name,
                        category=QualityUtils.categorize_issue("solid_principles", self.name),
                        tags=QualityUtils.generate_tags(
                            "solid_principles", self.name, SeverityLevel.MEDIUM,
                        ),
                    )
                    issues.append(issue)

        return issues

    def _validate_layered_architecture(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Validate Layered Architecture.
        """
        issues = []

        file_layer = self._determine_file_layer(file_path)

        for node in ast.walk(tree):
            if isinstance(node, (ast.ImportFrom, ast.Import)):
                imported_module = self._get_imported_module(node)
                if imported_module:
                    imported_layer = self._determine_module_layer(imported_module)
                    if self._violates_layer_boundary(file_layer, imported_layer):
                        issue = QualityIssue(
                            id=QualityUtils.generate_issue_id(
                                "layered_architecture", str(file_path), node.lineno,
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
                            tool=self.name,
                            category=QualityUtils.categorize_issue(
                                "layered_architecture", self.name,
                            ),
                            tags=QualityUtils.generate_tags(
                                "layered_architecture", self.name, SeverityLevel.HIGH,
                            ),
                        )
                        issues.append(issue)

        return issues

    def _validate_domain_driven_design(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Validate Domain-Driven Design patterns.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name.lower()

                # Check for proper domain entity structure
                if "entity" in class_name or "aggregate" in class_name:
                    if not self._has_domain_identity(node):
                        issue = QualityIssue(
                            id=QualityUtils.generate_issue_id(
                                "domain_driven_design", str(file_path), node.lineno,
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
                            tool=self.name,
                            category=QualityUtils.categorize_issue(
                                "domain_driven_design", self.name,
                            ),
                            tags=QualityUtils.generate_tags(
                                "domain_driven_design", self.name, SeverityLevel.MEDIUM,
                            ),
                        )
                        issues.append(issue)

        return issues

    def _validate_microservices_patterns(
        self, tree: ast.AST, file_path: Path,
    ) -> list[QualityIssue]:
        """
        Validate Microservices patterns.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name.lower()

                # Check for proper service boundaries
                if "service" in class_name:
                    if self._has_shared_database_dependencies(node):
                        issue = QualityIssue(
                            id=QualityUtils.generate_issue_id(
                                "microservices_patterns", str(file_path), node.lineno,
                            ),
                            type="microservices_patterns",
                            severity=SeverityLevel.HIGH,
                            file=str(file_path),
                            line=node.lineno,
                            column=node.col_offset,
                            message=f"Service '{node.name}' may have shared database dependencies",
                            suggestion="Ensure each microservice has its own database",
                            confidence=0.6,
                            impact=ImpactLevel.HIGH,
                            tool=self.name,
                            category=QualityUtils.categorize_issue(
                                "microservices_patterns", self.name,
                            ),
                            tags=QualityUtils.generate_tags(
                                "microservices_patterns", self.name, SeverityLevel.HIGH,
                            ),
                        )
                        issues.append(issue)

        return issues

    # Helper methods
    def _implements_interface(self, node: ast.ClassDef) -> bool:
        """
        Check if class implements an interface.
        """
        for base in node.bases:
            if isinstance(base, ast.Name):
                if "interface" in base.id.lower() or "protocol" in base.id.lower():
                    return True
        return False

    def _is_domain_layer(self, class_name: str) -> bool:
        """
        Check if class belongs to domain layer.
        """
        domain_keywords = ["entity", "model", "domain", "business", "aggregate", "value_object"]
        return any(keyword in class_name for keyword in domain_keywords)

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

        return len(responsibilities)

    def _determine_file_layer(self, file_path: Path) -> str:
        """
        Determine the architectural layer of a file.
        """
        path_str = str(file_path).lower()

        layers = {
            "presentation": ["controller", "view", "ui", "api", "endpoint", "route"],
            "application": ["service", "use_case", "handler", "command", "query"],
            "domain": ["entity", "model", "domain", "business", "aggregate", "value_object"],
            "infrastructure": ["repository", "persistence", "database", "external", "adapter"],
        }

        for layer, keywords in layers.items():
            if any(keyword in path_str for keyword in keywords):
                return layer

        return "unknown"

    def _determine_module_layer(self, module_name: str) -> str:
        """
        Determine the architectural layer of a module.
        """
        module_lower = module_name.lower()

        layers = {
            "presentation": ["controller", "view", "ui", "api", "endpoint", "route"],
            "application": ["service", "use_case", "handler", "command", "query"],
            "domain": ["entity", "model", "domain", "business", "aggregate", "value_object"],
            "infrastructure": ["repository", "persistence", "database", "external", "adapter"],
        }

        for layer, keywords in layers.items():
            if any(keyword in module_lower for keyword in keywords):
                return layer

        return "unknown"

    def _violates_layer_boundary(self, from_layer: str, to_layer: str) -> bool:
        """
        Check if import violates layer boundary.
        """
        layer_hierarchy = ["presentation", "application", "domain", "infrastructure"]

        try:
            from_index = layer_hierarchy.index(from_layer)
            to_index = layer_hierarchy.index(to_layer)

            # Higher layers (lower index) should not import from lower layers (higher index)
            return from_index < to_index
        except ValueError:
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

    def _has_shared_database_dependencies(self, node: ast.ClassDef) -> bool:
        """
        Check if service has shared database dependencies.
        """
        for child in ast.walk(node):
            if isinstance(child, (ast.Import, ast.ImportFrom)):
                module_name = self._get_imported_module(child)
                if module_name and "shared" in module_name.lower():
                    return True
        return False

    def _get_imported_module(self, node) -> str | None:
        """
        Get the imported module name.
        """
        if isinstance(node, ast.Import):
            return node.names[0].name if node.names else None
        if isinstance(node, ast.ImportFrom):
            return node.module
        return None


class ArchitecturalValidatorPlugin(QualityPlugin):
    """
    Plugin for architectural validation tool.
    """

    @property
    def name(self) -> str:
        return "architectural_validator"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return (
            "Architectural pattern validation for Hexagonal, Clean Architecture, SOLID principles"
        )

    @property
    def supported_extensions(self) -> list[str]:
        return [".py"]

    def create_analyzer(self, config: QualityConfig | None = None) -> QualityAnalyzer:
        return ArchitecturalValidator(config=config)

    def get_default_config(self) -> dict[str, Any]:
        return {
            "enabled_tools": ["architectural_validator"],
            "thresholds": {"max_responsibilities": 2, "layer_violation_severity": "high"},
            "filters": {"exclude_patterns": ["__pycache__", "*.pyc", ".git", "node_modules"]},
        }
