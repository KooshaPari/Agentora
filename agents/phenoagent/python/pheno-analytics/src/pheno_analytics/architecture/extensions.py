"""
Extension system for custom pattern detection and architecture analysis.
"""

from __future__ import annotations

import ast
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pheno.logging.core.logger import get_logger

from .models import ArchitecturePattern, DesignPattern, PatternMatch, SeverityLevel

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

logger = get_logger("pheno.analytics.architecture.extensions")


class PatternExtension(ABC):
    """
    Abstract base class for pattern extensions.
    """

    @abstractmethod
    def get_name(self) -> str:
        """
        Get the name of this extension.
        """

    @abstractmethod
    def get_version(self) -> str:
        """
        Get the version of this extension.
        """

    @abstractmethod
    def get_description(self) -> str:
        """
        Get the description of this extension.
        """

    @abstractmethod
    def get_patterns(self) -> list[ArchitecturePattern]:
        """
        Get architectural patterns defined by this extension.
        """

    @abstractmethod
    def get_design_patterns(self) -> list[DesignPattern]:
        """
        Get design patterns defined by this extension.
        """

    @abstractmethod
    def detect_patterns(self, file_path: Path, content: str, tree: ast.AST) -> list[PatternMatch]:
        """
        Detect patterns in a file.
        """


@dataclass(slots=True)
class CustomPatternDetector:
    """
    Custom pattern detector with configurable rules.
    """

    name: str
    description: str
    pattern_type: str
    detection_rules: list[Callable[[ast.AST, Path], list[PatternMatch]]]
    confidence_threshold: float = 0.5
    severity: SeverityLevel = SeverityLevel.MEDIUM
    tags: set[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = {"custom", "pattern"}

    def detect(self, file_path: Path, content: str, tree: ast.AST) -> list[PatternMatch]:
        """
        Run custom detection rules.
        """
        matches = []

        for rule in self.detection_rules:
            try:
                rule_matches = rule(tree, file_path)
                # Add custom metadata to matches
                for match in rule_matches:
                    match.pattern_type = self.pattern_type
                    match.tags.update(self.tags)
                    if match.confidence < self.confidence_threshold:
                        continue
                matches.extend(rule_matches)
            except Exception as e:
                logger.warning(f"Error running custom rule in {self.name}: {e}")

        return matches


class MicroservicesPatternExtension(PatternExtension):
    """
    Extension for microservices architecture patterns.
    """

    def get_name(self) -> str:
        return "microservices_patterns"

    def get_version(self) -> str:
        return "1.0.0"

    def get_description(self) -> str:
        return "Patterns and validations for microservices architecture"

    def get_patterns(self) -> list[ArchitecturePattern]:
        return [
            ArchitecturePattern(
                name="api_gateway",
                pattern_type=ArchitectureType.MICROSERVICES,
                description="API Gateway pattern for microservices",
                indicators=["gateway", "api_gateway", "proxy", "router"],
                required_layers=[LayerType.PRESENTATION],
                confidence_threshold=0.6,
            ),
            ArchitecturePattern(
                name="service_mesh",
                pattern_type=ArchitectureType.MICROSERVICES,
                description="Service Mesh pattern for microservices communication",
                indicators=["mesh", "sidecar", "proxy", "service_mesh"],
                required_layers=[LayerType.INFRASTRUCTURE],
                confidence_threshold=0.7,
            ),
            ArchitecturePattern(
                name="event_sourcing",
                pattern_type=ArchitectureType.EVENT_DRIVEN,
                description="Event Sourcing pattern for microservices",
                indicators=["event_store", "event_sourcing", "events", "event_log"],
                required_layers=[LayerType.INFRASTRUCTURE],
                confidence_threshold=0.8,
            ),
        ]

    def get_design_patterns(self) -> list[DesignPattern]:
        return [
            DesignPattern(
                name="circuit_breaker",
                pattern_type=DesignPatternType.BEHAVIORAL,
                description="Circuit Breaker pattern for fault tolerance",
                indicators=["circuit_breaker", "breaker", "fault_tolerance"],
                confidence_threshold=0.7,
            ),
            DesignPattern(
                name="bulkhead",
                pattern_type=DesignPatternType.ARCHITECTURAL,
                description="Bulkhead pattern for resource isolation",
                indicators=["bulkhead", "isolation", "resource_pool"],
                confidence_threshold=0.6,
            ),
            DesignPattern(
                name="saga",
                pattern_type=DesignPatternType.ARCHITECTURAL,
                description="Saga pattern for distributed transactions",
                indicators=["saga", "transaction", "compensation", "orchestration"],
                confidence_threshold=0.8,
            ),
        ]

    def detect_patterns(self, file_path: Path, content: str, tree: ast.AST) -> list[PatternMatch]:
        """
        Detect microservices patterns.
        """
        matches = []

        # Detect API Gateway
        if self._detect_api_gateway(tree, file_path):
            matches.append(
                PatternMatch(
                    pattern_name="api_gateway",
                    pattern_type="microservices",
                    file_path=file_path,
                    line_number=1,
                    column=0,
                    confidence=0.8,
                    description="API Gateway pattern detected",
                    suggestion="Ensure proper routing and load balancing configuration",
                    severity=SeverityLevel.LOW,
                    tags={"microservices", "api_gateway", "routing"},
                ),
            )

        # Detect Circuit Breaker
        if self._detect_circuit_breaker(tree, file_path):
            matches.append(
                PatternMatch(
                    pattern_name="circuit_breaker",
                    pattern_type="microservices",
                    file_path=file_path,
                    line_number=1,
                    column=0,
                    confidence=0.7,
                    description="Circuit Breaker pattern detected",
                    suggestion="Configure appropriate failure thresholds and recovery timeouts",
                    severity=SeverityLevel.LOW,
                    tags={"microservices", "circuit_breaker", "fault_tolerance"},
                ),
            )

        # Detect Event Sourcing
        if self._detect_event_sourcing(tree, file_path):
            matches.append(
                PatternMatch(
                    pattern_name="event_sourcing",
                    pattern_type="microservices",
                    file_path=file_path,
                    line_number=1,
                    column=0,
                    confidence=0.8,
                    description="Event Sourcing pattern detected",
                    suggestion="Ensure proper event versioning and migration strategies",
                    severity=SeverityLevel.LOW,
                    tags={"microservices", "event_sourcing", "events"},
                ),
            )

        return matches

    def _detect_api_gateway(self, tree: ast.AST, file_path: Path) -> bool:
        """
        Detect API Gateway pattern.
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name.lower()
                if any(keyword in class_name for keyword in ["gateway", "proxy", "router"]):
                    return True
        return False

    def _detect_circuit_breaker(self, tree: ast.AST, file_path: Path) -> bool:
        """
        Detect Circuit Breaker pattern.
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name.lower()
                if "circuit" in class_name and "breaker" in class_name:
                    return True
        return False

    def _detect_event_sourcing(self, tree: ast.AST, file_path: Path) -> bool:
        """
        Detect Event Sourcing pattern.
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name.lower()
                if "event" in class_name and ("store" in class_name or "sourcing" in class_name):
                    return True
        return False


class DomainDrivenDesignExtension(PatternExtension):
    """
    Extension for Domain-Driven Design patterns.
    """

    def get_name(self) -> str:
        return "domain_driven_design"

    def get_version(self) -> str:
        return "1.0.0"

    def get_description(self) -> str:
        return "Patterns and validations for Domain-Driven Design"

    def get_patterns(self) -> list[ArchitecturePattern]:
        return [
            ArchitecturePattern(
                name="bounded_context",
                pattern_type=ArchitectureType.MICROSERVICES,
                description="Bounded Context pattern from DDD",
                indicators=["bounded_context", "context", "domain_boundary"],
                required_layers=[LayerType.DOMAIN],
                confidence_threshold=0.7,
            ),
            ArchitecturePattern(
                name="aggregate",
                pattern_type=ArchitectureType.CLEAN,
                description="Aggregate pattern from DDD",
                indicators=["aggregate", "aggregate_root", "entity_aggregate"],
                required_layers=[LayerType.DOMAIN],
                confidence_threshold=0.8,
            ),
        ]

    def get_design_patterns(self) -> list[DesignPattern]:
        return [
            DesignPattern(
                name="value_object",
                pattern_type=DesignPatternType.ARCHITECTURAL,
                description="Value Object pattern from DDD",
                indicators=["value_object", "value", "immutable"],
                confidence_threshold=0.7,
            ),
            DesignPattern(
                name="domain_service",
                pattern_type=DesignPatternType.ARCHITECTURAL,
                description="Domain Service pattern from DDD",
                indicators=["domain_service", "domain_logic", "business_service"],
                confidence_threshold=0.6,
            ),
            DesignPattern(
                name="repository",
                pattern_type=DesignPatternType.ARCHITECTURAL,
                description="Repository pattern from DDD",
                indicators=["repository", "repo", "data_access"],
                confidence_threshold=0.7,
            ),
        ]

    def detect_patterns(self, file_path: Path, content: str, tree: ast.AST) -> list[PatternMatch]:
        """
        Detect DDD patterns.
        """
        matches = []

        # Detect Aggregate
        if self._detect_aggregate(tree, file_path):
            matches.append(
                PatternMatch(
                    pattern_name="aggregate",
                    pattern_type="ddd",
                    file_path=file_path,
                    line_number=1,
                    column=0,
                    confidence=0.8,
                    description="Aggregate pattern detected",
                    suggestion="Ensure aggregate maintains consistency boundaries",
                    severity=SeverityLevel.LOW,
                    tags={"ddd", "aggregate", "domain"},
                ),
            )

        # Detect Value Object
        if self._detect_value_object(tree, file_path):
            matches.append(
                PatternMatch(
                    pattern_name="value_object",
                    pattern_type="ddd",
                    file_path=file_path,
                    line_number=1,
                    column=0,
                    confidence=0.7,
                    description="Value Object pattern detected",
                    suggestion="Ensure value objects are immutable and have proper equality",
                    severity=SeverityLevel.LOW,
                    tags={"ddd", "value_object", "domain"},
                ),
            )

        return matches

    def _detect_aggregate(self, tree: ast.AST, file_path: Path) -> bool:
        """
        Detect Aggregate pattern.
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name.lower()
                if "aggregate" in class_name:
                    return True
        return False

    def _detect_value_object(self, tree: ast.AST, file_path: Path) -> bool:
        """
        Detect Value Object pattern.
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name.lower()
                if "value" in class_name and "object" in class_name:
                    return True
        return False


class ExtensionRegistry:
    """
    Registry for managing pattern extensions.
    """

    def __init__(self):
        self._extensions: dict[str, PatternExtension] = {}
        self._custom_detectors: dict[str, CustomPatternDetector] = {}

    def register_extension(self, extension: PatternExtension) -> None:
        """
        Register a pattern extension.
        """
        self._extensions[extension.get_name()] = extension
        logger.info(f"Registered pattern extension: {extension.get_name()}")

    def register_custom_detector(self, detector: CustomPatternDetector) -> None:
        """
        Register a custom pattern detector.
        """
        self._custom_detectors[detector.name] = detector
        logger.info(f"Registered custom detector: {detector.name}")

    def get_extension(self, name: str) -> PatternExtension | None:
        """
        Get an extension by name.
        """
        return self._extensions.get(name)

    def get_custom_detector(self, name: str) -> CustomPatternDetector | None:
        """
        Get a custom detector by name.
        """
        return self._custom_detectors.get(name)

    def list_extensions(self) -> list[str]:
        """
        List all registered extension names.
        """
        return list(self._extensions.keys())

    def list_custom_detectors(self) -> list[str]:
        """
        List all registered custom detector names.
        """
        return list(self._custom_detectors.keys())

    def get_all_patterns(self) -> list[ArchitecturePattern]:
        """
        Get all architectural patterns from all extensions.
        """
        patterns = []
        for extension in self._extensions.values():
            patterns.extend(extension.get_patterns())
        return patterns

    def get_all_design_patterns(self) -> list[DesignPattern]:
        """
        Get all design patterns from all extensions.
        """
        patterns = []
        for extension in self._extensions.values():
            patterns.extend(extension.get_design_patterns())
        return patterns

    def detect_all_patterns(
        self, file_path: Path, content: str, tree: ast.AST,
    ) -> list[PatternMatch]:
        """
        Run all extensions and custom detectors on a file.
        """
        all_matches = []

        # Run extensions
        for extension in self._extensions.values():
            try:
                matches = extension.detect_patterns(file_path, content, tree)
                all_matches.extend(matches)
            except Exception as e:
                logger.warning(
                    f"Error running extension {extension.get_name()} on {file_path}: {e}",
                )

        # Run custom detectors
        for detector in self._custom_detectors.values():
            try:
                matches = detector.detect(file_path, content, tree)
                all_matches.extend(matches)
            except Exception as e:
                logger.warning(f"Error running custom detector {detector.name} on {file_path}: {e}")

        return all_matches


# Factory functions for common custom detectors


def create_anti_pattern_detector() -> CustomPatternDetector:
    """
    Create a detector for common anti-patterns.
    """

    def detect_god_object(tree: ast.AST, file_path: Path) -> list[PatternMatch]:
        matches = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                if len(methods) > 15:
                    matches.append(
                        PatternMatch(
                            pattern_name="god_object",
                            pattern_type="anti_pattern",
                            file_path=file_path,
                            line_number=node.lineno,
                            column=node.col_offset,
                            confidence=0.8,
                            description=f"Class '{node.name}' appears to be a god object with {len(methods)} methods",
                            suggestion="Consider splitting into smaller, more focused classes",
                            severity=SeverityLevel.HIGH,
                            tags={"anti_pattern", "god_object", "refactoring"},
                        ),
                    )
        return matches

    def detect_feature_envy(tree: ast.AST, file_path: Path) -> list[PatternMatch]:
        matches = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                external_calls = 0
                internal_calls = 0

                for call in ast.walk(node):
                    if isinstance(call, ast.Call):
                        if isinstance(call.func, ast.Attribute):
                            if isinstance(call.func.value, ast.Name):
                                external_calls += 1
                            else:
                                internal_calls += 1

                if external_calls > internal_calls * 2:
                    matches.append(
                        PatternMatch(
                            pattern_name="feature_envy",
                            pattern_type="anti_pattern",
                            file_path=file_path,
                            line_number=node.lineno,
                            column=node.col_offset,
                            confidence=0.6,
                            description=f"Method '{node.name}' shows feature envy (more external calls than internal)",
                            suggestion="Consider moving this method to the class it's most interested in",
                            severity=SeverityLevel.MEDIUM,
                            tags={"anti_pattern", "feature_envy", "refactoring"},
                        ),
                    )
        return matches

    return CustomPatternDetector(
        name="anti_pattern_detector",
        description="Detects common anti-patterns in code",
        pattern_type="anti_pattern",
        detection_rules=[detect_god_object, detect_feature_envy],
        confidence_threshold=0.6,
        severity=SeverityLevel.MEDIUM,
        tags={"anti_pattern", "quality", "refactoring"},
    )


def create_security_pattern_detector() -> CustomPatternDetector:
    """
    Create a detector for security-related patterns.
    """

    def detect_sql_injection(tree: ast.AST, file_path: Path) -> list[PatternMatch]:
        matches = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in ["execute", "query", "raw"]:
                        # Look for string formatting in SQL queries
                        for arg in node.args:
                            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Mod):
                                matches.append(
                                    PatternMatch(
                                        pattern_name="sql_injection_risk",
                                        pattern_type="security",
                                        file_path=file_path,
                                        line_number=node.lineno,
                                        column=node.col_offset,
                                        confidence=0.7,
                                        description="Potential SQL injection vulnerability detected",
                                        suggestion="Use parameterized queries instead of string formatting",
                                        severity=SeverityLevel.HIGH,
                                        tags={"security", "sql_injection", "vulnerability"},
                                    ),
                                )
        return matches

    def detect_hardcoded_secrets(tree: ast.AST, file_path: Path) -> list[PatternMatch]:
        matches = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if any(
                            keyword in target.id.lower()
                            for keyword in ["password", "secret", "key", "token"]
                        ):
                            if isinstance(node.value, ast.Str):
                                matches.append(
                                    PatternMatch(
                                        pattern_name="hardcoded_secret",
                                        pattern_type="security",
                                        file_path=file_path,
                                        line_number=node.lineno,
                                        column=node.col_offset,
                                        confidence=0.9,
                                        description=f"Hardcoded secret detected in variable '{target.id}'",
                                        suggestion="Use environment variables or secure configuration management",
                                        severity=SeverityLevel.CRITICAL,
                                        tags={"security", "hardcoded_secret", "vulnerability"},
                                    ),
                                )
        return matches

    return CustomPatternDetector(
        name="security_pattern_detector",
        description="Detects security-related patterns and vulnerabilities",
        pattern_type="security",
        detection_rules=[detect_sql_injection, detect_hardcoded_secrets],
        confidence_threshold=0.7,
        severity=SeverityLevel.HIGH,
        tags={"security", "vulnerability", "protection"},
    )
