"""
Architecture detector configuration.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ArchitectureDetectorConfig:
    """
    Configuration for architecture detection.
    """

    skip_directories: list[str] = None
    skip_files: list[str] = None
    min_confidence: float = 0.3
    max_depth: int = 10
    include_hidden: bool = False
    analyze_dependencies: bool = True
    detect_cycles: bool = True

    def __post_init__(self):
        if self.skip_directories is None:
            self.skip_directories = [
                ".git",
                "__pycache__",
                "node_modules",
                ".venv",
                "venv",
                "dist",
                "build",
                ".pytest_cache",
                ".mypy_cache",
                ".tox",
                "htmlcov",
                "coverage",
                ".coverage",
                "site-packages",
            ]
        if self.skip_files is None:
            self.skip_files = ["*.pyc", "*.pyo", "*.pyd", "*.so", "*.dll"]
