"""
Pattern detection tool implementation.
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


class PatternDetector(QualityAnalyzer):
    """
    Advanced pattern detection tool.
    """

    def __init__(self, name: str = "pattern_detector", config: QualityConfig | None = None):
        super().__init__(name, config)
        self.patterns = {
            "god_object": self._detect_god_object,
            "feature_envy": self._detect_feature_envy,
            "data_clump": self._detect_data_clump,
            "shotgun_surgery": self._detect_shotgun_surgery,
            "divergent_change": self._detect_divergent_change,
            "parallel_inheritance": self._detect_parallel_inheritance,
            "lazy_class": self._detect_lazy_class,
            "inappropriate_intimacy": self._detect_inappropriate_intimacy,
            "message_chain": self._detect_message_chain,
            "middle_man": self._detect_middle_man,
            "incomplete_library_class": self._detect_incomplete_library_class,
            "temporary_field": self._detect_temporary_field,
            "refused_bequest": self._detect_refused_bequest,
            "alternative_classes": self._detect_alternative_classes,
            "duplicate_code_blocks": self._detect_duplicate_code_blocks,
        }

    def analyze_file(self, file_path: Path) -> list[QualityIssue]:
        """
        Analyze a single file for patterns.
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            file_issues = []

            for detector_func in self.patterns.values():
                issues = detector_func(tree, file_path)
                file_issues.extend(issues)

            self.issues.extend(file_issues)
            return file_issues

        except Exception as e:
            # Return a single error issue
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
        Analyze a directory for patterns.
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

    def _detect_god_object(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Detect god objects.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                if len(methods) > 15:  # Threshold for god object
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "god_object", str(file_path), node.lineno,
                        ),
                        type="god_object",
                        severity=SeverityLevel.HIGH,
                        file=str(file_path),
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Class '{node.name}' appears to be a god object with {len(methods)} methods",
                        suggestion="Consider splitting into smaller, more focused classes",
                        confidence=0.7,
                        impact=ImpactLevel.HIGH,
                        tool=self.name,
                        category=QualityUtils.categorize_issue("god_object", self.name),
                        tags=QualityUtils.generate_tags(
                            "god_object", self.name, SeverityLevel.HIGH,
                        ),
                    )
                    issues.append(issue)

        return issues

    def _detect_feature_envy(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Detect feature envy.
        """
        issues = []

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
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "feature_envy", str(file_path), node.lineno,
                        ),
                        type="feature_envy",
                        severity=SeverityLevel.MEDIUM,
                        file=str(file_path),
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Method '{node.name}' shows feature envy (more external calls than internal)",
                        suggestion="Consider moving this method to the class it's most interested in",
                        confidence=0.6,
                        impact=ImpactLevel.MEDIUM,
                        tool=self.name,
                        category=QualityUtils.categorize_issue("feature_envy", self.name),
                        tags=QualityUtils.generate_tags(
                            "feature_envy", self.name, SeverityLevel.MEDIUM,
                        ),
                    )
                    issues.append(issue)

        return issues

    def _detect_data_clump(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Detect data clumps.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                params = node.args.args
                if len(params) > 3:
                    param_names = [p.arg for p in params]
                    if len(set(param_names)) < len(param_names) * 0.8:
                        issue = QualityIssue(
                            id=QualityUtils.generate_issue_id(
                                "data_clump", str(file_path), node.lineno,
                            ),
                            type="data_clump",
                            severity=SeverityLevel.LOW,
                            file=str(file_path),
                            line=node.lineno,
                            column=node.col_offset,
                            message=f"Function '{node.name}' may have data clumps in parameters",
                            suggestion="Consider grouping related parameters into a data structure",
                            confidence=0.4,
                            impact=ImpactLevel.LOW,
                            tool=self.name,
                            category=QualityUtils.categorize_issue("data_clump", self.name),
                            tags=QualityUtils.generate_tags(
                                "data_clump", self.name, SeverityLevel.LOW,
                            ),
                        )
                        issues.append(issue)

        return issues

    def _detect_shotgun_surgery(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Detect shotgun surgery.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                assignments = [n for n in ast.walk(node) if isinstance(n, ast.Assign)]
                if len(assignments) > 10:
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "shotgun_surgery", str(file_path), node.lineno,
                        ),
                        type="shotgun_surgery",
                        severity=SeverityLevel.MEDIUM,
                        file=str(file_path),
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Function '{node.name}' may be doing shotgun surgery",
                        suggestion="Consider breaking into smaller, more focused functions",
                        confidence=0.5,
                        impact=ImpactLevel.MEDIUM,
                        tool=self.name,
                        category=QualityUtils.categorize_issue("shotgun_surgery", self.name),
                        tags=QualityUtils.generate_tags(
                            "shotgun_surgery", self.name, SeverityLevel.MEDIUM,
                        ),
                    )
                    issues.append(issue)

        return issues

    def _detect_divergent_change(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Detect divergent change.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                method_types = set()
                for method in methods:
                    if "get" in method.name.lower():
                        method_types.add("getter")
                    elif "set" in method.name.lower():
                        method_types.add("setter")
                    elif "create" in method.name.lower():
                        method_types.add("creator")
                    elif "delete" in method.name.lower():
                        method_types.add("deleter")
                    elif "validate" in method.name.lower():
                        method_types.add("validator")

                if len(method_types) > 4:
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "divergent_change", str(file_path), node.lineno,
                        ),
                        type="divergent_change",
                        severity=SeverityLevel.MEDIUM,
                        file=str(file_path),
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Class '{node.name}' may have divergent change",
                        suggestion="Consider splitting into classes with single responsibilities",
                        confidence=0.6,
                        impact=ImpactLevel.MEDIUM,
                        tool=self.name,
                        category=QualityUtils.categorize_issue("divergent_change", self.name),
                        tags=QualityUtils.generate_tags(
                            "divergent_change", self.name, SeverityLevel.MEDIUM,
                        ),
                    )
                    issues.append(issue)

        return issues

    def _detect_parallel_inheritance(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Detect parallel inheritance.
        """
        issues = []

        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

        for i, class1 in enumerate(classes):
            for class2 in classes[i + 1 :]:
                methods1 = {m.name for m in class1.body if isinstance(m, ast.FunctionDef)}
                methods2 = {m.name for m in class2.body if isinstance(m, ast.FunctionDef)}

                common_methods = methods1.intersection(methods2)
                if len(common_methods) > len(methods1) * 0.5:
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "parallel_inheritance", str(file_path), class1.lineno,
                        ),
                        type="parallel_inheritance",
                        severity=SeverityLevel.MEDIUM,
                        file=str(file_path),
                        line=class1.lineno,
                        column=class1.col_offset,
                        message=f"Classes '{class1.name}' and '{class2.name}' may have parallel inheritance",
                        suggestion="Consider using composition or shared base class",
                        confidence=0.5,
                        impact=ImpactLevel.MEDIUM,
                        tool=self.name,
                        category=QualityUtils.categorize_issue("parallel_inheritance", self.name),
                        tags=QualityUtils.generate_tags(
                            "parallel_inheritance", self.name, SeverityLevel.MEDIUM,
                        ),
                    )
                    issues.append(issue)

        return issues

    def _detect_lazy_class(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Detect lazy classes.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                if len(methods) < 3:
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "lazy_class", str(file_path), node.lineno,
                        ),
                        type="lazy_class",
                        severity=SeverityLevel.LOW,
                        file=str(file_path),
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Class '{node.name}' may be a lazy class with only {len(methods)} methods",
                        suggestion="Consider merging with another class or removing",
                        confidence=0.4,
                        impact=ImpactLevel.LOW,
                        tool=self.name,
                        category=QualityUtils.categorize_issue("lazy_class", self.name),
                        tags=QualityUtils.generate_tags("lazy_class", self.name, SeverityLevel.LOW),
                    )
                    issues.append(issue)

        return issues

    def _detect_inappropriate_intimacy(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Detect inappropriate intimacy.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                class_accesses = set()
                for call in ast.walk(node):
                    if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute):
                        if isinstance(call.func.value, ast.Name):
                            class_accesses.add(call.func.value.id)

                if len(class_accesses) > 5:
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "inappropriate_intimacy", str(file_path), node.lineno,
                        ),
                        type="inappropriate_intimacy",
                        severity=SeverityLevel.MEDIUM,
                        file=str(file_path),
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Function '{node.name}' accesses many different classes",
                        suggestion="Consider reducing dependencies between classes",
                        confidence=0.5,
                        impact=ImpactLevel.MEDIUM,
                        tool=self.name,
                        category=QualityUtils.categorize_issue("inappropriate_intimacy", self.name),
                        tags=QualityUtils.generate_tags(
                            "inappropriate_intimacy", self.name, SeverityLevel.MEDIUM,
                        ),
                    )
                    issues.append(issue)

        return issues

    def _detect_message_chain(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Detect message chains.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                chain_length = self._get_chain_length(node)
                if chain_length > 3:
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "message_chain", str(file_path), node.lineno,
                        ),
                        type="message_chain",
                        severity=SeverityLevel.MEDIUM,
                        file=str(file_path),
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Message chain of {chain_length} calls found",
                        suggestion="Consider using intermediate variables or law of demeter",
                        confidence=0.6,
                        impact=ImpactLevel.MEDIUM,
                        tool=self.name,
                        category=QualityUtils.categorize_issue("message_chain", self.name),
                        tags=QualityUtils.generate_tags(
                            "message_chain", self.name, SeverityLevel.MEDIUM,
                        ),
                    )
                    issues.append(issue)

        return issues

    def _detect_middle_man(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Detect middle man classes.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                delegation_count = 0

                for method in methods:
                    calls = [n for n in ast.walk(method) if isinstance(n, ast.Call)]
                    if len(calls) == 1:
                        delegation_count += 1

                if delegation_count > len(methods) * 0.7:
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "middle_man", str(file_path), node.lineno,
                        ),
                        type="middle_man",
                        severity=SeverityLevel.MEDIUM,
                        file=str(file_path),
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Class '{node.name}' may be a middle man",
                        suggestion="Consider removing the middle man and calling directly",
                        confidence=0.6,
                        impact=ImpactLevel.MEDIUM,
                        tool=self.name,
                        category=QualityUtils.categorize_issue("middle_man", self.name),
                        tags=QualityUtils.generate_tags(
                            "middle_man", self.name, SeverityLevel.MEDIUM,
                        ),
                    )
                    issues.append(issue)

        return issues

    def _detect_incomplete_library_class(
        self, tree: ast.AST, file_path: Path,
    ) -> list[QualityIssue]:
        """
        Detect incomplete library class usage.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.bases:
                methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                if len(methods) < 2:
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "incomplete_library_class", str(file_path), node.lineno,
                        ),
                        type="incomplete_library_class",
                        severity=SeverityLevel.LOW,
                        file=str(file_path),
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Class '{node.name}' may be incomplete library class",
                        suggestion="Consider using composition instead of inheritance",
                        confidence=0.4,
                        impact=ImpactLevel.LOW,
                        tool=self.name,
                        category=QualityUtils.categorize_issue(
                            "incomplete_library_class", self.name,
                        ),
                        tags=QualityUtils.generate_tags(
                            "incomplete_library_class", self.name, SeverityLevel.LOW,
                        ),
                    )
                    issues.append(issue)

        return issues

    def _detect_temporary_field(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Detect temporary fields.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                assignments = []
                for method in ast.walk(node):
                    if isinstance(method, ast.Assign):
                        for target in method.targets:
                            if (
                                isinstance(target, ast.Attribute)
                                and isinstance(target.value, ast.Name)
                                and target.value.id == "self"
                            ):
                                assignments.append(target.attr)

                uses = []
                for method in ast.walk(node):
                    if (
                        isinstance(method, ast.Attribute)
                        and isinstance(method.value, ast.Name)
                        and method.value.id == "self"
                    ):
                        uses.append(method.attr)

                for field in set(assignments):
                    if uses.count(field) < assignments.count(field) * 0.3:
                        issue = QualityIssue(
                            id=QualityUtils.generate_issue_id(
                                "temporary_field", str(file_path), node.lineno,
                            ),
                            type="temporary_field",
                            severity=SeverityLevel.LOW,
                            file=str(file_path),
                            line=node.lineno,
                            column=node.col_offset,
                            message=f"Field '{field}' may be temporary",
                            suggestion="Consider using local variables instead",
                            confidence=0.4,
                            impact=ImpactLevel.LOW,
                            tool=self.name,
                            category=QualityUtils.categorize_issue("temporary_field", self.name),
                            tags=QualityUtils.generate_tags(
                                "temporary_field", self.name, SeverityLevel.LOW,
                            ),
                        )
                        issues.append(issue)

        return issues

    def _detect_refused_bequest(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Detect refused bequest.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if node.bases:
                    overrides = []
                    for method in node.body:
                        if isinstance(method, ast.FunctionDef):
                            for base in node.bases:
                                if isinstance(base, ast.Name):
                                    overrides.append(method.name)

                    if len(overrides) > 3:
                        issue = QualityIssue(
                            id=QualityUtils.generate_issue_id(
                                "refused_bequest", str(file_path), node.lineno,
                            ),
                            type="refused_bequest",
                            severity=SeverityLevel.MEDIUM,
                            file=str(file_path),
                            line=node.lineno,
                            column=node.col_offset,
                            message=f"Class '{node.name}' may be refusing bequest",
                            suggestion="Consider using composition instead of inheritance",
                            confidence=0.5,
                            impact=ImpactLevel.MEDIUM,
                            tool=self.name,
                            category=QualityUtils.categorize_issue("refused_bequest", self.name),
                            tags=QualityUtils.generate_tags(
                                "refused_bequest", self.name, SeverityLevel.MEDIUM,
                            ),
                        )
                        issues.append(issue)

        return issues

    def _detect_alternative_classes(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Detect alternative classes.
        """
        issues = []

        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

        for i, class1 in enumerate(classes):
            for class2 in classes[i + 1 :]:
                methods1 = {m.name for m in class1.body if isinstance(m, ast.FunctionDef)}
                methods2 = {m.name for m in class2.body if isinstance(m, ast.FunctionDef)}

                common_methods = methods1.intersection(methods2)
                if len(common_methods) > 2:
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "alternative_classes", str(file_path), class1.lineno,
                        ),
                        type="alternative_classes",
                        severity=SeverityLevel.LOW,
                        file=str(file_path),
                        line=class1.lineno,
                        column=class1.col_offset,
                        message=f"Classes '{class1.name}' and '{class2.name}' may be alternatives",
                        suggestion="Consider unifying the interfaces",
                        confidence=0.4,
                        impact=ImpactLevel.LOW,
                        tool=self.name,
                        category=QualityUtils.categorize_issue("alternative_classes", self.name),
                        tags=QualityUtils.generate_tags(
                            "alternative_classes", self.name, SeverityLevel.LOW,
                        ),
                    )
                    issues.append(issue)

        return issues

    def _detect_duplicate_code_blocks(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
        """
        Detect duplicate code blocks.
        """
        issues = []

        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

        for i, func1 in enumerate(functions):
            for func2 in functions[i + 1 :]:
                if self._functions_similar(func1, func2):
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "duplicate_code_blocks", str(file_path), func1.lineno,
                        ),
                        type="duplicate_code_blocks",
                        severity=SeverityLevel.MEDIUM,
                        file=str(file_path),
                        line=func1.lineno,
                        column=func1.col_offset,
                        message=f"Functions '{func1.name}' and '{func2.name}' may be duplicates",
                        suggestion="Consider extracting common code into a shared function",
                        confidence=0.6,
                        impact=ImpactLevel.MEDIUM,
                        tool=self.name,
                        category=QualityUtils.categorize_issue("duplicate_code_blocks", self.name),
                        tags=QualityUtils.generate_tags(
                            "duplicate_code_blocks", self.name, SeverityLevel.MEDIUM,
                        ),
                    )
                    issues.append(issue)

        return issues

    def _get_chain_length(self, node: ast.Call) -> int:
        """
        Get the length of a method call chain.
        """
        length = 1
        current = node.func

        while isinstance(current, ast.Attribute):
            length += 1
            current = current.value

        return length

    def _functions_similar(self, func1: ast.FunctionDef, func2: ast.FunctionDef) -> bool:
        """
        Check if two functions are similar.
        """
        if len(func1.body) != len(func2.body):
            return False

        for stmt1, stmt2 in zip(func1.body, func2.body, strict=False):
            if type(stmt1) != type(stmt2):
                return False

        return True


class PatternDetectorPlugin(QualityPlugin):
    """
    Plugin for pattern detection tool.
    """

    @property
    def name(self) -> str:
        return "pattern_detector"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Advanced pattern detection for anti-patterns and design issues"

    @property
    def supported_extensions(self) -> list[str]:
        return [".py"]

    def create_analyzer(self, config: QualityConfig | None = None) -> QualityAnalyzer:
        return PatternDetector(config=config)

    def get_default_config(self) -> dict[str, Any]:
        return {
            "enabled_tools": ["pattern_detector"],
            "thresholds": {
                "god_object_methods": 15,
                "feature_envy_ratio": 2.0,
                "data_clump_params": 3,
                "shotgun_surgery_assignments": 10,
                "divergent_change_types": 4,
                "parallel_inheritance_ratio": 0.5,
                "lazy_class_methods": 3,
                "inappropriate_intimacy_classes": 5,
                "message_chain_length": 3,
                "middle_man_delegation_ratio": 0.7,
                "incomplete_library_methods": 2,
                "temporary_field_usage_ratio": 0.3,
                "refused_bequest_overrides": 3,
                "alternative_classes_common": 2,
            },
            "filters": {"exclude_patterns": ["__pycache__", "*.pyc", ".git", "node_modules"]},
        }
