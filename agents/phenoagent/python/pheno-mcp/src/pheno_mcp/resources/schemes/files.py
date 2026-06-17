"""
File navigation resource scheme.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .base import ResourceSchemeHandler
from .common import LOGGER

if TYPE_CHECKING:
    from ..template_engine import ResourceContext


class FilesResourceScheme(ResourceSchemeHandler):
    """Handler for files:// resources - file system navigation."""

    def __init__(self):
        super().__init__("files")
        self.allowed_directories = [
            Path.cwd(),
            Path("logs"),
            Path("docs"),
            Path("config"),
            Path("static"),
        ]

    async def handle_request(self, context: ResourceContext) -> dict[str, Any]:
        """
        Default to browsing directory contents.
        """
        return await self.browse_directory(context)

    async def browse_directory(self, context: ResourceContext) -> dict[str, Any]:
        """
        Browse directory contents.
        """
        path = context.get_parameter("path", ".")
        show_hidden = context.get_parameter("show_hidden", "false").lower() == "true"

        try:
            directory = Path(path).resolve()

            if not any(
                directory.is_relative_to(allowed.resolve()) for allowed in self.allowed_directories
            ):
                return {"error": "Access denied to directory"}

            if not directory.exists():
                return {"error": "Directory does not exist"}

            if not directory.is_dir():
                return {"error": "Path is not a directory"}

            entries: list[dict[str, Any]] = []
            for entry in directory.iterdir():
                if not show_hidden and entry.name.startswith("."):
                    continue

                stat = entry.stat()
                entries.append(
                    {
                        "name": entry.name,
                        "type": "directory" if entry.is_dir() else "file",
                        "size": stat.st_size,
                        "modified": int(stat.st_mtime),
                        "permissions": oct(stat.st_mode)[-3:],
                    },
                )

            entries.sort(key=lambda item: (item["type"] != "directory", item["name"]))

            return {
                "directory": str(directory),
                "entries": entries,
                "total": len(entries),
                "show_hidden": show_hidden,
                "timestamp": int(time.time()),
            }

        except Exception as exc:  # pragma: no cover - defensive
            LOGGER.error("Error browsing directory '%s': %s", path, exc)
            return {"error": str(exc)}

    async def get_file_info(self, context: ResourceContext) -> dict[str, Any]:
        """
        Get information about a specific file.
        """
        path = context.get_parameter("path")

        if not path:
            return {"error": "path parameter is required"}

        try:
            file_path = Path(path).resolve()

            if not any(
                file_path.is_relative_to(allowed.resolve()) for allowed in self.allowed_directories
            ):
                return {"error": "Access denied to file"}

            if not file_path.exists():
                return {"error": "File does not exist"}

            stat = file_path.stat()
            info: dict[str, Any] = {
                "path": str(file_path),
                "name": file_path.name,
                "type": "directory" if file_path.is_dir() else "file",
                "size": stat.st_size,
                "modified": int(stat.st_mtime),
                "created": int(stat.st_ctime),
                "permissions": oct(stat.st_mode)[-3:],
                "owner": stat.st_uid,
                "group": stat.st_gid,
            }

            if file_path.is_file():
                info["extension"] = file_path.suffix.lower()
                info["is_text"] = self._is_text_file(file_path)

                if info["is_text"] and stat.st_size < 1024 * 1024:
                    try:
                        with open(file_path, encoding="utf-8") as fh:
                            content = fh.read()
                        info["preview"] = content[:500] + "..." if len(content) > 500 else content
                        info["lines"] = len(content.splitlines())
                    except Exception:
                        info["preview"] = "Unable to read file content"

            return info

        except Exception as exc:  # pragma: no cover - defensive
            LOGGER.error("Error getting file info for '%s': %s", path, exc)
            return {"error": str(exc)}

    def _is_text_file(self, file_path: Path) -> bool:
        """
        Check if file is likely a text file.
        """
        text_extensions = {
            ".txt",
            ".md",
            ".py",
            ".js",
            ".ts",
            ".json",
            ".yaml",
            ".yml",
            ".toml",
            ".ini",
            ".cfg",
            ".conf",
            ".log",
            ".csv",
            ".xml",
            ".html",
            ".css",
            ".scss",
            ".sql",
            ".sh",
            ".bash",
            ".dockerfile",
            ".env",
        }
        return file_path.suffix.lower() in text_extensions


__all__ = ["FilesResourceScheme"]
