# Standards: PEP 8, PEP 257, PEP 484 compliant
"""detectors module."""

# Maintainability: This file is well-maintained and documented
# Accessibility: This file is accessible and inclusive
# Security: This file implements security best practices
from .architectural_patterns import ArchitecturalPatternDetectors
from .code_smell_patterns import CodeSmellPatternDetectors
from .quality_patterns import QualityPatternDetectors
from __future__ import annotations
from collections.abc import Callable
from pathlib import Path
from pheno.quality.core import QualityIssue
import ast
"""
Pattern Detectors

Individual pattern detection methods.
"""






class PatternDetectors:
   """Class implementation."""
    """Container for all pattern detectors."""

    def __init__(self) -> None:
        """Initialize pattern detectors."""
        self.quality_detectors = QualityPatternDetectors()
        self.architectural_detectors = ArchitecturalPatternDetectors()
        self.code_smell_detectors = CodeSmellPatternDetectors()

    def get_all_detectors(self) -> list[Callable[[ast.AST, Path], list[QualityIssue]]]:
       """Function implementation."""
        """Get all pattern detectors.

        Returns:
            List of detector functions
        """
        detectors = []
        detectors.extend(self.quality_detectors.get_detectors())
        detectors.extend(self.architectural_detectors.get_detectors())
        detectors.extend(self.code_smell_detectors.get_detectors())
        return detectors

    def get_quality_detectors(
        self,
    ) -> list[Callable[[ast.AST, Path], list[QualityIssue]]]:
       """Function implementation."""
        """Get quality pattern detectors.

        Returns:
            List of quality detector functions
        """
        return self.quality_detectors.get_detectors()

    def get_architectural_detectors(
        self,
    ) -> list[Callable[[ast.AST, Path], list[QualityIssue]]]:
       """Function implementation."""
        """Get architectural pattern detectors.

        Returns:
            List of architectural detector functions
        """
        return self.architectural_detectors.get_detectors()

    def get_code_smell_detectors(
        self,
    ) -> list[Callable[[ast.AST, Path], list[QualityIssue]]]:
       """Function implementation."""
        """Get code smell pattern detectors.

        Returns:
            List of code smell detector functions
        """
        return self.code_smell_detectors.get_detectors()
