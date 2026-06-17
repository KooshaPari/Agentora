"""
Test Cache - Smart Test Result Caching

Combines best features from both Zen and Atoms frameworks:
- Hash-based invalidation (tool, dependencies, framework, test file)
- Environment compatibility checking
- Age-based expiration
- File change detection
- Comprehensive statistics
"""

import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class TestCache:
    """Cache test results based on comprehensive dependency tracking.

    Cache invalidation triggers:
    - Tool implementation changes
    - Tool dependencies change
    - Framework files change
    - Test file changes
    - Environment changes (Python version, platform)
    - Cache age > 7 days
    - Previous test failed
    """

    # Prevent pytest from treating this utility as a test case when imported
    __test__ = False

    def __init__(
        self,
        cache_file: str = ".mcp_test_cache.json",
        project_root: Optional[Path] = None,
    ):
        """Initialize test cache.

        Args:
            cache_file: Path to cache file
            project_root: Project root directory (auto-detected if None)
        """
        self.cache_file = Path(cache_file)
        self.cache: Dict[str, Dict[str, Any]] = self._load_cache()
        self.project_root = project_root or self._detect_project_root()

    def _detect_project_root(self) -> Path:
        """
        Auto-detect project root (look for common markers).
        """
        current = Path(__file__).parent
        for _ in range(5):  # Search up to 5 levels
            if any(
                (current / marker).exists() for marker in [".git", "pyproject.toml", "setup.py"]
            ):
                return current
            current = current.parent
        return Path(__file__).parent.parent.parent  # Fallback

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

    def get_tool_hash(self, tool_name: str, tool_paths: Optional[List[Path]] = None) -> str:
        """Get hash of tool implementation.

        Args:
            tool_name: Tool name
            tool_paths: Optional list of paths to search

        Returns:
            MD5 hash of tool file content or "unknown" if not found
        """
        if tool_paths:
            for tool_file in tool_paths:
                if tool_file.exists():
                    return self.get_file_hash(tool_file)
        return "unknown"

    def get_dependencies_hash(self, dependency_files: List[Path]) -> str:
        """Get combined hash of all dependency files.

        Args:
            dependency_files: List of dependency file paths

        Returns:
            Combined MD5 hash of all dependency files
        """
        hashes = []
        for dep_path in dependency_files:
            dep_hash = self.get_file_hash(dep_path)
            hashes.append(dep_hash)

        if hashes:
            combined = "".join(hashes)
            return hashlib.md5(combined.encode()).hexdigest()

        return "none"

    def should_skip(
        self,
        test_name: str,
        tool_hash: str,
        dependencies_hash: str = "none",
        framework_hash: str = "none",
        test_file_hash: Optional[str] = None,
    ) -> bool:
        """Check if test should be skipped based on cache validation.

        Args:
            test_name: Name of the test function
            tool_hash: Hash of tool implementation
            dependencies_hash: Hash of tool dependencies
            framework_hash: Hash of framework files
            test_file_hash: Hash of test file (optional)

        Returns:
            True if test can be skipped (all unchanged)
        """
        # Check if test is cached
        if test_name not in self.cache:
            return False

        cached = self.cache[test_name]

        # CRITICAL: Must have passed previously - NEVER skip failed tests
        if cached.get("status") != "passed":
            return False

        # Check age (< 7 days)
        if time.time() - cached.get("timestamp", 0) >= 7 * 24 * 3600:
            return False

        # Check tool hash
        if cached.get("tool_hash") != tool_hash:
            return False

        # Check dependencies hash
        if cached.get("dependencies_hash") != dependencies_hash:
            return False

        # Check framework hash
        if cached.get("framework_hash") != framework_hash:
            return False

        # Check test file hash if provided
        if test_file_hash and cached.get("test_hash") != test_file_hash:
            return False

        # All checks passed - safe to skip
        return True

    def record(
        self,
        test_name: str,
        tool_name: str,
        status: str,
        duration: float,
        tool_hash: str,
        dependencies_hash: str = "none",
        framework_hash: str = "none",
        test_file_hash: Optional[str] = None,
        error: Optional[str] = None,
    ):
        """Record test result in cache with comprehensive metadata.

        Args:
            test_name: Name of the test function
            tool_name: Name of the tool being tested
            status: Test status ("passed", "failed", "error")
            duration: Test duration in seconds
            tool_hash: Hash of tool implementation
            dependencies_hash: Hash of tool dependencies
            framework_hash: Hash of framework files
            test_file_hash: Hash of test file (optional)
            error: Optional error message if test failed
        """
        self.cache[test_name] = {
            "tool_hash": tool_hash,
            "dependencies_hash": dependencies_hash,
            "framework_hash": framework_hash,
            "test_hash": test_file_hash,
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
        # Filter out environment metadata
        test_entries = {k: v for k, v in self.cache.items() if not k.startswith("_")}

        total = len(test_entries)
        passed = sum(1 for v in test_entries.values() if v.get("status") == "passed")
        failed = sum(1 for v in test_entries.values() if v.get("status") == "failed")

        # Get environment info
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
        tool_hash: str,
        dependencies_hash: str = "none",
        framework_hash: str = "none",
        test_file_hash: Optional[str] = None,
    ) -> Optional[str]:
        """Get human-readable reason why a test would not be skipped.

        Args:
            test_name: Name of the test function
            tool_hash: Hash of tool implementation
            dependencies_hash: Hash of tool dependencies
            framework_hash: Hash of framework files
            test_file_hash: Hash of test file (optional)

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

        if cached.get("tool_hash") != tool_hash:
            return "Tool file changed"

        if cached.get("dependencies_hash") != dependencies_hash:
            return "Dependencies changed"

        if cached.get("framework_hash") != framework_hash:
            return "Framework changed"

        if test_file_hash and cached.get("test_hash") != test_file_hash:
            return "Test file changed"

        return None
