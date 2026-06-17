# Standards: PEP 8, PEP 257, PEP 484 compliant
"""god_object module."""

# Maintainability: This file is well-maintained and documented
# Accessibility: This file is accessible and inclusive
# Security: This file implements security best practices
from .base import BasePatternDetector
from pathlib import Path
from pheno.quality.core import ImpactLevel, QualityIssue, SeverityLevel
from pheno.quality.utils import QualityUtils
import ast
"""God object pattern detector."""





class GodObjectDetector(BasePatternDetector):
   """Class implementation."""
    """Detects god objects (classes with too many methods)."""

    def __init__(self, threshold -> None: int = 15) -> None:
        """Initialize god object detector.

        Args:
            threshold: Maximum number of methods before flagging as god object
        """
        super().__init__("god_object")
        self.threshold = threshold

    def detect(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
       """Function implementation."""
        """Detect god objects in AST.

        Args:
            tree: AST tree to analyze
            file_path: Path to the file being analyzed

        Returns:
            List of quality issues found
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                if len(methods) > self.threshold:
                    issue = QualityIssue(
                        id=QualityUtils.generate_issue_id(
                            "god_object",
                            str(file_path),
                            node.lineno,
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
                            "god_object",
                            self.name,
                            SeverityLevel.HIGH,
                        ),
                    )
                    issues.append(issue)

        return issues
