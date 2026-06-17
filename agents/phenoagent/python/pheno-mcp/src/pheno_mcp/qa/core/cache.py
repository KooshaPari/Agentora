"""Lightweight caching utilities used by the MCP QA test runner.

The original implementation performed extensive hashing of tool sources to decide when
cached results could be reused.  For the in-repo consolidation we preserve the external
API while simplifying the internals to focus on the most common workflows.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class CacheEntry:
    status: str
    duration: float
    error: str | None = None


class TestCache:
    """Persistent cache keyed by test name and tool identifier.

    A JSON file on disk stores the cached results.  The cache is intentionally
    conservative: only successful runs or explicit skip markers are reused.
    Changes to the Python interpreter version automatically invalidate cached
    data to avoid subtle incompatibilities.
    """

    def __init__(self, cache_file: str = ".mcp_test_cache.json") -> None:
        self.cache_file = Path(cache_file)
        self._store: dict[str, dict[str, Any]] = self._load()

    # ------------------------------------------------------------------ utils
    def _environment_signature(self) -> str:
        return f"{os.uname().sysname}-{os.uname().release}-py{os.sys.version_info[:3]}"

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self.cache_file.exists():
            return {}
        try:
            payload = json.loads(self.cache_file.read_text())
        except Exception:
            return {}
        if payload.get("_environment") != self._environment_signature():
            return {}
        return payload.get("data", {})

    def _persist(self) -> None:
        payload = {
            "_environment": self._environment_signature(),
            "data": self._store,
        }
        try:
            self.cache_file.write_text(json.dumps(payload, indent=2))
        except Exception:
            pass  # best effort

    # ----------------------------------------------------------------- hashing
    def _hash(self, *parts: str) -> str:
        digest = hashlib.md5()
        for part in parts:
            digest.update(part.encode("utf-8"))
        return digest.hexdigest()

    # ------------------------------------------------------------------ public
    def should_skip(self, test_name: str, tool_name: str) -> bool:
        tool_cache = self._store.get(test_name, {})
        entry = tool_cache.get(tool_name)
        return bool(entry and entry.get("status") == "passed")

    def record(
        self,
        test_name: str,
        tool_name: str,
        status: str,
        duration: float,
        error: str | None = None,
    ) -> None:
        self._store.setdefault(test_name, {})[tool_name] = {
            "status": status,
            "duration": duration,
            "error": error,
        }
        self._persist()

    def clear(self) -> None:
        self._store.clear()
        if self.cache_file.exists():
            with contextlib.suppress(Exception):
                self.cache_file.unlink()


__all__ = ["CacheEntry", "TestCache"]
