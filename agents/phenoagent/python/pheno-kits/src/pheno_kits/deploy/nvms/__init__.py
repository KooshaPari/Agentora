"""
NVMSParser module for Node Version Manager Script parsing.
"""

from pathlib import Path
from typing import Dict, List, Optional


class NVMSParser:
    """
    Parser for Node Version Manager Script files.
    """

    def __init__(self, nvms_file: Path | None = None):
        """
        Initialize parser with optional NVMS file path.
        """
        self.nvms_file = nvms_file or Path(".nvms")

    def parse(self) -> dict[str, str]:
        """
        Parse NVMS file and return version mappings.
        """
        if not self.nvms_file.exists():
            return {}

        versions = {}
        try:
            with open(self.nvms_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        if "=" in line:
                            key, value = line.split("=", 1)
                            versions[key.strip()] = value.strip()
        except Exception:
            pass

        return versions

    def get_node_version(self) -> str | None:
        """
        Get Node.js version from NVMS file.
        """
        versions = self.parse()
        return versions.get("node")

    def get_npm_version(self) -> str | None:
        """
        Get npm version from NVMS file.
        """
        versions = self.parse()
        return versions.get("npm")


__all__ = ["NVMSParser"]
