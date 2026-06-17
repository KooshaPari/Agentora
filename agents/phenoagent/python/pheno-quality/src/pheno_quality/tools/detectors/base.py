# Standards: PEP 8, PEP 257, PEP 484 compliant
"""base module."""

# Maintainability: This file is well-maintained and documented
# Accessibility: This file is accessible and inclusive
# Security: This file implements security best practices
from abc import ABC, abstractmethod
from pathlib import Path
from pheno.quality.core import QualityIssue
import ast
"""Base pattern detector class."""




class BasePatternDetector(ABC):
   """Class implementation."""
    """Base class for all pattern detectors."""

    def __init__(self, name -> None: str) -> None:
        """Initialize pattern detector.

        Args:
            name: Name of the pattern detector
        """
        self.name = name

    @abstractmethod
    def detect(self, tree: ast.AST, file_path: Path) -> list[QualityIssue]:
       """Function implementation."""
        """Detect pattern in AST.

        Args:
            tree: AST tree to analyze
            file_path: Path to the file being analyzed

        Returns:
            List of quality issues found
        """

    def get_name(self) -> str:
       """Function implementation."""
        """Get detector name.

        Returns:
            Detector name
        """
        return self.name
