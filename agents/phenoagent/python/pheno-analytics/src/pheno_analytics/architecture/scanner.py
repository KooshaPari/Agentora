"""
Directory and file scanning utilities.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import ArchitectureDetectorConfig


def scan_directories(
    root: Path,
    config: ArchitectureDetectorConfig,
) -> dict[str, list[str]]:
    """
    Scan directory structure for analysis.
    """
    structure: dict[str, list[str]] = {}
    skip_tokens = set(config.skip_directories)

    for item in root.rglob("*"):
        if not item.is_dir():
            continue

        if not config.include_hidden and item.name.startswith("."):
            continue

        if any(token in item.parts for token in skip_tokens):
            continue

        depth = len(item.relative_to(root).parts)
        if depth > config.max_depth:
            continue

        dir_name = item.name.lower()
        parent = item.parent.name.lower() if item.parent != root else "root"

        structure.setdefault(parent, []).append(dir_name)

    return structure


def should_analyze_file(file_path: Path, config: ArchitectureDetectorConfig) -> bool:
    """
    Check if a file should be analyzed.
    """
    if not config.include_hidden and file_path.name.startswith("."):
        return False

    for skip_dir in config.skip_directories:
        if skip_dir in file_path.parts:
            return False

    for skip_pattern in config.skip_files:
        if file_path.match(skip_pattern):
            return False

    return True


def count_files_and_lines(
    root_path: Path, config: ArchitectureDetectorConfig
) -> tuple[int, int]:
    """
    Count analyzed files and total lines of code.
    """
    file_count = 0
    line_count = 0

    for file_path in root_path.rglob("*.py"):
        if should_analyze_file(file_path, config):
            file_count += 1
            try:
                with open(file_path, encoding="utf-8") as f:
                    line_count += len(f.readlines())
            except Exception:
                pass

    return file_count, line_count
