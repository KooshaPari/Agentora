"""File System Scheme Handler.

Provides access to files via file:// URIs.
"""

import json
from pathlib import Path
from typing import Any

import yaml

from pheno.ports.mcp import ResourceSchemeHandler


class FileSchemeHandler(ResourceSchemeHandler):
    """
    Handler for file:// scheme.

    Provides read access to files on the file system.
    Automatically parses JSON and YAML files.

    URI Format:
        file:///absolute/path/to/file
        file://./relative/path/to/file
        file://*.json  (list all JSON files in current dir)

    Example:
        >>> handler = FileSchemeHandler()
        >>> config = await handler.get_resource("file://./config.json")
        >>> files = await handler.list_resources("file://*.yaml")
    """

    def __init__(self, base_path: Path | None = None):
        """Initialize file scheme handler.

        Args:
            base_path: Optional base path for relative URIs
        """
        self.base_path = base_path or Path.cwd()

    async def get_resource(self, uri: str) -> Any:
        """Get file contents.

        Args:
            uri: URI in format file://path/to/file

        Returns:
            File contents (parsed if JSON/YAML)

        Raises:
            ValueError: If file not found

        Example:
            >>> data = await handler.get_resource("file://./data.json")
        """
        _, path_str = uri.split("://", 1)

        # Handle absolute vs relative paths
        if path_str.startswith("/"):
            path = Path(path_str)
        else:
            path = self.base_path / path_str.lstrip("./")

        if not path.exists():
            raise ValueError(f"File not found: {path}")

        if not path.is_file():
            raise ValueError(f"Not a file: {path}")

        # Read file
        content = path.read_text()

        # Parse based on extension
        if path.suffix == ".json":
            return json.loads(content)
        if path.suffix in [".yaml", ".yml"]:
            return yaml.safe_load(content)
        return content

    async def list_resources(self, uri: str) -> list[str]:
        """List files matching pattern.

        Args:
            uri: URI pattern (e.g., file://*.json)

        Returns:
            List of matching file URIs

        Example:
            >>> files = await handler.list_resources("file://*.json")
        """
        _, pattern = uri.split("://", 1)

        # Handle absolute vs relative paths
        if pattern.startswith("/"):
            base = Path("/")
            glob_pattern = pattern.lstrip("/")
        else:
            base = self.base_path
            glob_pattern = pattern.lstrip("./")

        # List matching files
        return [f"file://{p!s}" for p in base.glob(glob_pattern) if p.is_file()]


    def supports_scheme(self, scheme: str) -> bool:
        """
        Check if scheme is supported.
        """
        return scheme == "file"


__all__ = ["FileSchemeHandler"]
