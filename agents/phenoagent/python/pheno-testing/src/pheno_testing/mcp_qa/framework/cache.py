"""
Test Cache - Smart Caching Based on Code Hashes

Intelligently caches test results and skips re-running tests when:
- Tool implementation hasn't changed (based on file hash)
- Previous test passed
- Test function hasn't changed
- Framework dependencies haven't changed
- Test file itself hasn't changed
- Environment (Python version, dependencies) hasn't changed

This significantly speeds up test runs during development while ensuring
cache is only used when truly safe, preventing false passes from stale results.
"""

import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Default framework core files that affect all tests
DEFAULT_FRAMEWORK_FILES = [
    "mcp_qa/framework/__init__.py",
    "mcp_qa/framework/cache.py",
    "mcp_qa/framework/decorators.py",
    "mcp_qa/fixtures/__init__.py",
]


class TestCache:
    """
    Cache test results based on comprehensive dependency tracking.
    """

    def __init__(
        self,
        cache_file: str = ".mcp_qa_cache.json",
        project_root: Optional[Path] = None,
    ):
        """Initialize test cache.

        Args:
            cache_file: Path to cache file
            project_root: Project root directory (auto-detected if not provided)
        """
        self.cache_file = Path(cache_file)
        self.cache: Dict[str, Dict[str, Any]] = self._load_cache()

        if project_root:
            self.project_root = Path(project_root)
        else:
            # Auto-detect project root
            current = Path.cwd()
            while current != current.parent:
                if (current / ".git").exists() or (current / "pyproject.toml").exists():
                    self.project_root = current
                    break
                current = current.parent
            else:
                self.project_root = Path.cwd()

    def _load_cache(self) -> Dict[str, Dict[str, Any]]:
        """
        Load cache from disk.
        """
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r") as f:
                    cache = json.load(f)
                    if self._is_cache_compatible(cache):
                        return cache
                    else:
                        # Environment changed, invalidate cache
                        return {}
            except Exception:
                return {}
        return {}

    def _is_cache_compatible(self, cache: Dict) -> bool:
        """
        Check if cached results are compatible with current environment.
        """
        if "_environment" not in cache:
            return False

        env = cache["_environment"]
        current_env = self._get_environment()

        # Must match Python version
        if env.get("python_version") != current_env["python_version"]:
            return False

        return True

    def _get_environment(self) -> Dict[str, str]:
        """
        Get current execution environment metadata.
        """
        return {
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform": sys.platform,
        }

    def _save_cache(self):
        """
        Save cache to disk with environment metadata.
        """
        try:
            cache_with_env = {"_environment": self._get_environment(), **self.cache}
            with open(self.cache_file, "w") as f:
                json.dump(cache_with_env, f, indent=2)
        except Exception:
            pass  # Best effort

    def get_file_hash(self, file_path: Path | str) -> str:
        """Get hash of a file's content.

        Args:
            file_path: Path to file

        Returns:
            MD5 hash of file content or "unknown" if not found
        """
        file_path = Path(file_path)
        if file_path.exists():
            try:
                content = file_path.read_text()
                return hashlib.md5(content.encode()).hexdigest()
            except Exception:
                pass
        return "unknown"

    def get_tool_hash(self, tool_name: str) -> str:
        """Get hash of tool implementation.

        Args:
            tool_name: Tool file name (e.g., "chat_tool", "query_tool")

        Returns:
            MD5 hash of tool file content or "unknown" if not found
        """
        # Try multiple possible locations
        possible_paths = [
            self.project_root / "tools" / f"{tool_name}.py",
            self.project_root / "src" / "tools" / f"{tool_name}.py",
            self.project_root / "tools" / tool_name.replace("_tool", "") / "__init__.py",
            self.project_root / "src" / "tools" / tool_name.replace("_tool", "") / "__init__.py",
        ]

        for tool_file in possible_paths:
            if tool_file.exists():
                return self.get_file_hash(tool_file)

        return "unknown"

    def get_framework_hash(self, framework_files: Optional[List[str]] = None) -> str:
        """Get combined hash of framework core files.

        Args:
            framework_files: List of framework files to hash

        Returns:
            Combined MD5 hash of all framework files
        """
        if framework_files is None:
            framework_files = DEFAULT_FRAMEWORK_FILES

        hashes = []
        for framework_file in framework_files:
            full_path = self.project_root / framework_file
            file_hash = self.get_file_hash(full_path)
            hashes.append(file_hash)

        combined = "".join(hashes)
        return hashlib.md5(combined.encode()).hexdigest()

    def should_skip(
        self,
        test_name: str,
        tool_name: str,
        test_file_path: Optional[Path | str] = None,
        max_age_days: int = 7,
    ) -> bool:
        """Check if test should be skipped based on cache validation.

        Args:
            test_name: Name of the test function
            tool_name: Name of the tool being tested
            test_file_path: Path to the test file itself (optional)
            max_age_days: Maximum age of cache entry in days

        Returns:
            True if test can be skipped (ALL unchanged: tool, framework, test file)

        Note:
            Failed tests are NEVER cached - always re-run to verify fixes.
        """
        if test_name not in self.cache:
            return False

        cached = self.cache[test_name]

        # CRITICAL: Must have passed previously - NEVER skip failed tests
        if cached.get("status") != "passed":
            return False

        # Check age
        if time.time() - cached.get("timestamp", 0) >= max_age_days * 24 * 3600:
            return False

        # Check tool file hash
        tool_hash = self.get_tool_hash(tool_name)
        if cached.get("tool_hash") != tool_hash:
            return False

        # Check framework hash
        framework_hash = self.get_framework_hash()
        if cached.get("framework_hash") != framework_hash:
            return False

        # Check test file hash if provided
        if test_file_path:
            test_hash = self.get_file_hash(test_file_path)
            if cached.get("test_hash") != test_hash:
                return False

        # All checks passed - safe to skip
        return True

    def record(
        self,
        test_name: str,
        tool_name: str,
        status: str,
        duration: float,
        error: Optional[str] = None,
        test_file_path: Optional[Path | str] = None,
    ):
        """Record test result in cache with comprehensive metadata.

        Args:
            test_name: Name of the test function
            tool_name: Name of the tool being tested
            status: Test status ("passed", "failed", "error")
            duration: Test duration in seconds
            error: Optional error message if test failed
            test_file_path: Path to the test file itself (optional)
        """
        tool_hash = self.get_tool_hash(tool_name)
        framework_hash = self.get_framework_hash()
        test_hash = self.get_file_hash(test_file_path) if test_file_path else None

        self.cache[test_name] = {
            "tool_hash": tool_hash,
            "framework_hash": framework_hash,
            "test_hash": test_hash,
            "status": status,
            "duration": duration,
            "timestamp": time.time(),
            "error": error,
            "tool_name": tool_name,
        }
        self._save_cache()

    def clear(self):
        """
        Clear all cached test results.
        """
        self.cache = {}
        self._save_cache()

    def clear_tool(self, tool_name: str):
        """
        Clear cached results for a specific tool.
        """
        to_remove = [
            test_name
            for test_name, cached_data in self.cache.items()
            if cached_data.get("tool_name") == tool_name
        ]

        for key in to_remove:
            del self.cache[key]

        self._save_cache()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics.
        """
        test_entries = {k: v for k, v in self.cache.items() if not k.startswith("_")}

        total = len(test_entries)
        passed = sum(1 for v in test_entries.values() if v.get("status") == "passed")
        failed = sum(1 for v in test_entries.values() if v.get("status") == "failed")

        env = self.cache.get("_environment", {})

        return {
            "total_cached": total,
            "passed": passed,
            "failed": failed,
            "cache_file": str(self.cache_file),
            "environment": env,
        }

    def get_invalidation_reason(
        self,
        test_name: str,
        tool_name: str,
        test_file_path: Optional[Path | str] = None,
    ) -> Optional[str]:
        """Get human-readable reason why a test would not be skipped.

        Args:
            test_name: Name of the test function
            tool_name: Name of the tool being tested
            test_file_path: Path to the test file itself (optional)

        Returns:
            Reason string if test cannot be skipped, None if it can be skipped
        """
        if test_name not in self.cache:
            return "Test not in cache"

        cached = self.cache[test_name]

        if cached.get("status") != "passed":
            return f"Previous status: {cached.get('status')}"

        age = time.time() - cached.get("timestamp", 0)
        if age >= 7 * 24 * 3600:
            return f"Cache too old ({age / 86400:.1f} days)"

        tool_hash = self.get_tool_hash(tool_name)
        if cached.get("tool_hash") != tool_hash:
            return "Tool file changed"

        framework_hash = self.get_framework_hash()
        if cached.get("framework_hash") != framework_hash:
            return "Framework changed"

        if test_file_path:
            test_hash = self.get_file_hash(test_file_path)
            if cached.get("test_hash") != test_hash:
                return "Test file changed"

        return None
