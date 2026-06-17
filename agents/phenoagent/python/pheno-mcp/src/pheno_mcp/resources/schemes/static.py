"""
Static content resource scheme.
"""

from __future__ import annotations

import base64
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .base import ResourceSchemeHandler
from .common import LOGGER

if TYPE_CHECKING:
    from ..template_engine import ResourceContext


class StaticResourceScheme(ResourceSchemeHandler):
    """Handler for static:// resources - static content."""

    def __init__(self):
        super().__init__("static")
        self.static_directory = Path("static")

    async def handle_request(self, context: ResourceContext) -> dict[str, Any]:
        """
        Default to fetching content.
        """
        return await self.get_content(context)

    async def get_content(self, context: ResourceContext) -> dict[str, Any]:
        """
        Get static content.
        """
        path = context.get_parameter("path", "")

        try:
            if not self.static_directory.exists():
                return {"error": "Static directory not found"}

            file_path = (self.static_directory / path).resolve()
            static_root = self.static_directory.resolve()

            if not file_path.is_relative_to(static_root):
                return {"error": "Access denied"}

            if not file_path.exists():
                return {"error": "File not found"}

            if file_path.is_dir():
                return {"error": "Path is a directory, not a file"}

            content_type = self._get_content_type(file_path)

            if content_type.startswith("text/"):
                with open(file_path, encoding="utf-8") as fh:
                    content = fh.read()
                encoding = "utf-8"
            else:
                with open(file_path, "rb") as fh:
                    content = base64.b64encode(fh.read()).decode("utf-8")
                encoding = "base64"

            return {
                "path": path,
                "content_type": content_type,
                "content": content,
                "size": file_path.stat().st_size,
                "encoding": encoding,
                "timestamp": int(time.time()),
            }

        except Exception as exc:  # pragma: no cover - defensive
            LOGGER.error("Error getting static content for '%s': %s", path, exc)
            return {"error": str(exc)}

    def _get_content_type(self, file_path: Path) -> str:
        """
        Determine content type from file extension.
        """
        extension_map = {
            ".html": "text/html",
            ".css": "text/css",
            ".js": "application/javascript",
            ".json": "application/json",
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".pdf": "application/pdf",
            ".zip": "application/zip",
        }

        return extension_map.get(file_path.suffix.lower(), "application/octet-stream")


__all__ = ["StaticResourceScheme"]
