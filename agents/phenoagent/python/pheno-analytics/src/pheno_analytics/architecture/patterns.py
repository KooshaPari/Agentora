"""
Pattern detection and registry system.
"""

from __future__ import annotations

import ast
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pheno.logging.core.logger import get_logger

from .models import ArchitecturePattern, DesignPattern, PatternMatch, SeverityLevel

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

logger = get_logger("pheno.analytics.architecture.patterns")


class PatternDetector(ABC):
    """
    Abstract base class for pattern detectors.
    """

    @abstractmethod
    def detect(self, file_path: Path, content: str, tree: ast.AST) -> list[PatternMatch]:
        """
        Detect patterns in a file.
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Name of the detector.
        """

    @property
    @abstractmethod
    def description(self) -> str:
        """
        Description of what this detector finds.
        """


class DesignPatternDetector(PatternDetector):
    """
    Detects design patterns in code.
    """

    def __init__(self):
        self._patterns = {
            "singleton": self._detect_singleton,
            "factory": self._detect_factory,
            "observer": self._detect_observer,
            "strategy": self._detect_strategy,
            "adapter": self._detect_adapter,
            "decorator": self._detect_decorator,
            "repository": self._detect_repository,
            "service": self._detect_service,
            "controller": self._detect_controller,
            "middleware": self._detect_middleware,
        }

    @property
    def name(self) -> str:
        return "design_pattern_detector"

    @property
    def description(self) -> str:
        return "Detects common design patterns in code"

    def detect(self, file_path: Path, content: str, tree: ast.AST) -> list[PatternMatch]:
        """
        Detect design patterns in the file.
        """
        matches = []

        for pattern_name, detector_func in self._patterns.items():
            try:
                pattern_matches = detector_func(tree, file_path)
                matches.extend(pattern_matches)
            except Exception as e:
                logger.warning(f"Error detecting pattern {pattern_name} in {file_path}: {e}")

        return matches

    def _detect_singleton(self, tree: ast.AST, file_path: Path) -> list[PatternMatch]:
        """
        Detect singleton pattern.
        """
        matches = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Look for singleton indicators
                has_instance_var = False
                has_get_instance = False

                for child in node.body:
                    if isinstance(child, ast.Assign):
                        for target in child.targets:
                            if isinstance(target, ast.Name) and target.id == "_instance":
                                has_instance_var = True
                    elif isinstance(child, ast.FunctionDef):
                        if child.name in {"get_instance", "instance"}:
                            has_get_instance = True
                        elif child.name == "__new__":
                            pass

                if has_instance_var and has_get_instance:
                    matches.append(
                        PatternMatch(
                            pattern_name="singleton",
                            pattern_type="creational",
                            file_path=file_path,
                            line_number=node.lineno,
                            column=node.col_offset,
                            confidence=0.8,
                            description=f"Class '{node.name}' appears to implement Singleton pattern",
                            suggestion="Ensure thread safety if used in multi-threaded environment",
                            severity=SeverityLevel.LOW,
                            tags={"pattern", "singleton", "creational"},
                        ),
                    )

        return matches

    def _detect_factory(self, tree: ast.AST, file_path: Path) -> list[PatternMatch]:
        """
        Detect factory pattern.
        """
        matches = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name.lower()

                # Look for factory indicators
                if "factory" in class_name or "builder" in class_name or "creator" in class_name:
                    has_create_method = False
                    has_static_methods = False

                    for child in node.body:
                        if isinstance(child, ast.FunctionDef):
                            if "create" in child.name.lower() or "build" in child.name.lower():
                                has_create_method = True
                            if child.name.startswith("create_") or child.name.startswith("build_"):
                                has_static_methods = True

                    if has_create_method or has_static_methods:
                        matches.append(
                            PatternMatch(
                                pattern_name="factory",
                                pattern_type="creational",
                                file_path=file_path,
                                line_number=node.lineno,
                                column=node.col_offset,
                                confidence=0.7,
                                description=f"Class '{node.name}' appears to implement Factory pattern",
                                suggestion="Consider using abstract factory for complex object hierarchies",
                                severity=SeverityLevel.LOW,
                                tags={"pattern", "factory", "creational"},
                            ),
                        )

        return matches

    def _detect_observer(self, tree: ast.AST, file_path: Path) -> list[PatternMatch]:
        """
        Detect observer pattern.
        """
        matches = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name.lower()

                # Look for observer indicators
                if (
                    "observer" in class_name
                    or "listener" in class_name
                    or "subscriber" in class_name
                ):
                    has_notify = False
                    has_attach = False
                    has_detach = False

                    for child in node.body:
                        if isinstance(child, ast.FunctionDef):
                            method_name = child.name.lower()
                            if "notify" in method_name or "update" in method_name:
                                has_notify = True
                            elif "attach" in method_name or "subscribe" in method_name:
                                has_attach = True
                            elif "detach" in method_name or "unsubscribe" in method_name:
                                has_detach = True

                    if has_notify and (has_attach or has_detach):
                        matches.append(
                            PatternMatch(
                                pattern_name="observer",
                                pattern_type="behavioral",
                                file_path=file_path,
                                line_number=node.lineno,
                                column=node.col_offset,
                                confidence=0.8,
                                description=f"Class '{node.name}' appears to implement Observer pattern",
                                suggestion="Consider using event-driven architecture for better decoupling",
                                severity=SeverityLevel.LOW,
                                tags={"pattern", "observer", "behavioral"},
                            ),
                        )

        return matches

    def _detect_strategy(self, tree: ast.AST, file_path: Path) -> list[PatternMatch]:
        """
        Detect strategy pattern.
        """
        matches = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name.lower()

                # Look for strategy indicators
                if "strategy" in class_name or "algorithm" in class_name or "policy" in class_name:
                    has_execute = False
                    has_interface_methods = False

                    for child in node.body:
                        if isinstance(child, ast.FunctionDef):
                            method_name = child.name.lower()
                            if (
                                "execute" in method_name
                                or "run" in method_name
                                or "apply" in method_name
                            ):
                                has_execute = True
                            if child.name.startswith("execute_") or child.name.startswith("run_"):
                                has_interface_methods = True

                    if has_execute or has_interface_methods:
                        matches.append(
                            PatternMatch(
                                pattern_name="strategy",
                                pattern_type="behavioral",
                                file_path=file_path,
                                line_number=node.lineno,
                                column=node.col_offset,
                                confidence=0.7,
                                description=f"Class '{node.name}' appears to implement Strategy pattern",
                                suggestion="Consider using dependency injection for strategy selection",
                                severity=SeverityLevel.LOW,
                                tags={"pattern", "strategy", "behavioral"},
                            ),
                        )

        return matches

    def _detect_adapter(self, tree: ast.AST, file_path: Path) -> list[PatternMatch]:
        """
        Detect adapter pattern.
        """
        matches = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name.lower()

                # Look for adapter indicators
                if "adapter" in class_name or "wrapper" in class_name or "translator" in class_name:
                    has_adaptee_reference = False

                    for child in node.body:
                        if isinstance(child, ast.FunctionDef):
                            # Look for methods that delegate to another object
                            for stmt in child.body:
                                if isinstance(stmt, ast.Call) and isinstance(
                                    stmt.func, ast.Attribute,
                                ):
                                    if isinstance(stmt.func.value, ast.Name):
                                        has_adaptee_reference = True

                        elif isinstance(child, ast.Assign):
                            # Look for adaptee references
                            for target in child.targets:
                                if isinstance(target, ast.Name) and "adaptee" in target.id.lower():
                                    has_adaptee_reference = True

                    if has_adaptee_reference:
                        matches.append(
                            PatternMatch(
                                pattern_name="adapter",
                                pattern_type="structural",
                                file_path=file_path,
                                line_number=node.lineno,
                                column=node.col_offset,
                                confidence=0.6,
                                description=f"Class '{node.name}' appears to implement Adapter pattern",
                                suggestion="Ensure the adapter properly implements the target interface",
                                severity=SeverityLevel.LOW,
                                tags={"pattern", "adapter", "structural"},
                            ),
                        )

        return matches

    def _detect_decorator(self, tree: ast.AST, file_path: Path) -> list[PatternMatch]:
        """
        Detect decorator pattern.
        """
        matches = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name.lower()

                # Look for decorator indicators
                if "decorator" in class_name or "wrapper" in class_name or "enhancer" in class_name:
                    has_component_reference = False
                    has_decorate_method = False

                    for child in node.body:
                        if isinstance(child, ast.FunctionDef):
                            method_name = child.name.lower()
                            if "decorate" in method_name or "enhance" in method_name:
                                has_decorate_method = True

                        elif isinstance(child, ast.Assign):
                            for target in child.targets:
                                if (
                                    isinstance(target, ast.Name)
                                    and "component" in target.id.lower()
                                ):
                                    has_component_reference = True

                    if has_component_reference or has_decorate_method:
                        matches.append(
                            PatternMatch(
                                pattern_name="decorator",
                                pattern_type="structural",
                                file_path=file_path,
                                line_number=node.lineno,
                                column=node.col_offset,
                                confidence=0.6,
                                description=f"Class '{node.name}' appears to implement Decorator pattern",
                                suggestion="Consider using Python's built-in decorator syntax for simpler cases",
                                severity=SeverityLevel.LOW,
                                tags={"pattern", "decorator", "structural"},
                            ),
                        )

        return matches

    def _detect_repository(self, tree: ast.AST, file_path: Path) -> list[PatternMatch]:
        """
        Detect repository pattern.
        """
        matches = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name.lower()

                # Look for repository indicators
                if (
                    "repository" in class_name
                    or "repo" in class_name
                    or "data_access" in class_name
                ):
                    has_crud_methods = False
                    crud_methods = ["create", "read", "update", "delete", "find", "get", "save"]

                    for child in node.body:
                        if isinstance(child, ast.FunctionDef):
                            method_name = child.name.lower()
                            if any(crud in method_name for crud in crud_methods):
                                has_crud_methods = True
                                break

                    if has_crud_methods:
                        matches.append(
                            PatternMatch(
                                pattern_name="repository",
                                pattern_type="architectural",
                                file_path=file_path,
                                line_number=node.lineno,
                                column=node.col_offset,
                                confidence=0.8,
                                description=f"Class '{node.name}' appears to implement Repository pattern",
                                suggestion="Consider using generic repository for common CRUD operations",
                                severity=SeverityLevel.LOW,
                                tags={"pattern", "repository", "architectural"},
                            ),
                        )

        return matches

    def _detect_service(self, tree: ast.AST, file_path: Path) -> list[PatternMatch]:
        """
        Detect service pattern.
        """
        matches = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name.lower()

                # Look for service indicators
                if "service" in class_name or "manager" in class_name or "handler" in class_name:
                    has_business_logic = False

                    for child in node.body:
                        if isinstance(child, ast.FunctionDef):
                            # Look for business logic methods
                            method_name = child.name.lower()
                            if any(
                                keyword in method_name
                                for keyword in ["process", "handle", "execute", "manage"]
                            ):
                                has_business_logic = True

                        elif isinstance(child, ast.Assign):
                            # Look for injected dependencies
                            for target in child.targets:
                                if isinstance(target, ast.Name) and target.id.endswith("_service"):
                                    pass

                    if has_business_logic:
                        matches.append(
                            PatternMatch(
                                pattern_name="service",
                                pattern_type="architectural",
                                file_path=file_path,
                                line_number=node.lineno,
                                column=node.col_offset,
                                confidence=0.7,
                                description=f"Class '{node.name}' appears to implement Service pattern",
                                suggestion="Ensure service has single responsibility and proper error handling",
                                severity=SeverityLevel.LOW,
                                tags={"pattern", "service", "architectural"},
                            ),
                        )

        return matches

    def _detect_controller(self, tree: ast.AST, file_path: Path) -> list[PatternMatch]:
        """
        Detect controller pattern.
        """
        matches = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name.lower()

                # Look for controller indicators
                if (
                    "controller" in class_name
                    or "handler" in class_name
                    or "endpoint" in class_name
                ):
                    has_http_methods = False
                    has_request_handling = False

                    for child in node.body:
                        if isinstance(child, ast.FunctionDef):
                            method_name = child.name.lower()
                            # Look for HTTP method names
                            if method_name in [
                                "get",
                                "post",
                                "put",
                                "delete",
                                "patch",
                                "head",
                                "options",
                            ]:
                                has_http_methods = True
                            # Look for request handling methods
                            if "handle" in method_name or "process" in method_name:
                                has_request_handling = True

                    if has_http_methods or has_request_handling:
                        matches.append(
                            PatternMatch(
                                pattern_name="controller",
                                pattern_type="architectural",
                                file_path=file_path,
                                line_number=node.lineno,
                                column=node.col_offset,
                                confidence=0.8,
                                description=f"Class '{node.name}' appears to implement Controller pattern",
                                suggestion="Keep controllers thin and delegate business logic to services",
                                severity=SeverityLevel.LOW,
                                tags={"pattern", "controller", "architectural"},
                            ),
                        )

        return matches

    def _detect_middleware(self, tree: ast.AST, file_path: Path) -> list[PatternMatch]:
        """
        Detect middleware pattern.
        """
        matches = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name.lower()

                # Look for middleware indicators
                if (
                    "middleware" in class_name
                    or "interceptor" in class_name
                    or "filter" in class_name
                ):
                    has_process_method = False
                    has_next_reference = False

                    for child in node.body:
                        if isinstance(child, ast.FunctionDef):
                            method_name = child.name.lower()
                            if (
                                "process" in method_name
                                or "handle" in method_name
                                or "intercept" in method_name
                            ):
                                has_process_method = True

                                # Look for next() calls
                                for stmt in child.body:
                                    if isinstance(stmt, ast.Call) and isinstance(
                                        stmt.func, ast.Name,
                                    ):
                                        if stmt.func.id == "next":
                                            has_next_reference = True

                    if has_process_method and has_next_reference:
                        matches.append(
                            PatternMatch(
                                pattern_name="middleware",
                                pattern_type="architectural",
                                file_path=file_path,
                                line_number=node.lineno,
                                column=node.col_offset,
                                confidence=0.8,
                                description=f"Class '{node.name}' appears to implement Middleware pattern",
                                suggestion="Ensure middleware is stateless and handles errors gracefully",
                                severity=SeverityLevel.LOW,
                                tags={"pattern", "middleware", "architectural"},
                            ),
                        )

        return matches


class PatternRegistry:
    """
    Registry for managing pattern detectors and patterns.
    """

    def __init__(self):
        self._detectors: dict[str, PatternDetector] = {}
        self._architectural_patterns: dict[str, ArchitecturePattern] = {}
        self._design_patterns: dict[str, DesignPattern] = {}
        self._custom_detectors: list[PatternDetector] = []

    def register_detector(self, detector: PatternDetector) -> None:
        """
        Register a pattern detector.
        """
        self._detectors[detector.name] = detector
        logger.info(f"Registered pattern detector: {detector.name}")

    def register_architectural_pattern(self, pattern: ArchitecturePattern) -> None:
        """
        Register an architectural pattern.
        """
        self._architectural_patterns[pattern.name] = pattern
        logger.info(f"Registered architectural pattern: {pattern.name}")

    def register_design_pattern(self, pattern: DesignPattern) -> None:
        """
        Register a design pattern.
        """
        self._design_patterns[pattern.name] = pattern
        logger.info(f"Registered design pattern: {pattern.name}")

    def get_detector(self, name: str) -> PatternDetector | None:
        """
        Get a pattern detector by name.
        """
        return self._detectors.get(name)

    def get_architectural_pattern(self, name: str) -> ArchitecturePattern | None:
        """
        Get an architectural pattern by name.
        """
        return self._architectural_patterns.get(name)

    def get_design_pattern(self, name: str) -> DesignPattern | None:
        """
        Get a design pattern by name.
        """
        return self._design_patterns.get(name)

    def list_detectors(self) -> list[str]:
        """
        List all registered detector names.
        """
        return list(self._detectors.keys())

    def list_architectural_patterns(self) -> list[str]:
        """
        List all registered architectural pattern names.
        """
        return list(self._architectural_patterns.keys())

    def list_design_patterns(self) -> list[str]:
        """
        List all registered design pattern names.
        """
        return list(self._design_patterns.keys())

    def detect_patterns(self, file_path: Path, content: str, tree: ast.AST) -> list[PatternMatch]:
        """
        Run all registered detectors on a file.
        """
        all_matches = []

        for detector in self._detectors.values():
            try:
                matches = detector.detect(file_path, content, tree)
                all_matches.extend(matches)
            except Exception as e:
                logger.warning(f"Error running detector {detector.name} on {file_path}: {e}")

        return all_matches


class CustomPatternDetector(PatternDetector):
    """
    Custom pattern detector that can be configured with custom rules.
    """

    def __init__(
        self,
        name: str,
        description: str,
        detection_rules: list[Callable[[ast.AST, Path], list[PatternMatch]]],
    ):
        self._name = name
        self._description = description
        self._rules = detection_rules

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def detect(self, file_path: Path, content: str, tree: ast.AST) -> list[PatternMatch]:
        """
        Run custom detection rules.
        """
        matches = []

        for rule in self._rules:
            try:
                rule_matches = rule(tree, file_path)
                matches.extend(rule_matches)
            except Exception as e:
                logger.warning(f"Error running custom rule in {self.name}: {e}")

        return matches
