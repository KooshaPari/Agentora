"""
Generic Test Cache Framework - Smart Caching Based on Tool Code Hashes

Caches test results and skips re-running tests when:
- Tool implementation hasn't changed (based on file hash)
- Previous test passed
- Test function hasn't changed
- Framework dependencies haven't changed
- Test file itself hasn't changed
- Environment (Python version, dependencies) hasn't changed

This significantly speeds up test runs during development while ensuring
cache is only used when truly safe, preventing false passes from stale results.

This is a generic base class that can be extended by specific MCP implementations
by providing their own TOOL_DEPENDENCIES and FRAMEWORK_CORE_FILES.
"""

import hashlib
import json
import sys
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional


class BaseTestCache(ABC):
    """Generic cache for test results based on comprehensive dependency tracking.

    This base class provides all the generic caching logic. Subclasses should:
    1. Implement get_tool_dependencies() to return tool-specific dependency mappings
    2. Implement get_framework_files() to return framework core files
    3. Optionally override get_tool_search_paths() for custom tool file locations
    """

    def __init__(self, cache_file: str = ".test_cache.json", project_root: Optional[Path] = None):
        """Initialize test cache.

        Args:
            cache_file: Name of the cache file
            project_root: Project root directory (defaults to 3 levels up from this file)
        """
        self.cache_file = Path(cache_file)
        self.cache: Dict[str, Dict[str, Any]] = self._load_cache()

        # Allow override of project root for flexibility
        if project_root:
            self.project_root = Path(project_root)
        else:
            self.project_root = Path(__file__).parent.parent.parent

        # Default tool directories (can be overridden)
        self.tools_dir = self.project_root / "tools"
        self.src_tools_dir = self.project_root / "src" / "tools"

    @abstractmethod
    def get_tool_dependencies(self) -> Dict[str, List[str]]:
        """Get tool dependency mapping.

        Returns:
            Dictionary mapping tool names to list of dependency file paths
            Example: {"entity_tool": ["tools/base.py", "errors.py"]}
        """
        pass

    @abstractmethod
    def get_framework_files(self) -> List[str]:
        """Get framework core files that affect all tests.

        Returns:
            List of framework file paths relative to project root
            Example: ["tests/framework/__init__.py", "tests/framework/decorators.py"]
        """
        pass

    def get_tool_search_paths(self, tool_name: str) -> List[Path]:
        """Get possible file paths for a tool.

        Override this method to customize tool file search locations.

        Args:
            tool_name: Tool file name (e.g., "workspace_tool", "entity_tool")

        Returns:
            List of possible file paths to search
        """
        return [
            self.tools_dir / f"{tool_name}.py",
            self.src_tools_dir / f"{tool_name}.py",
            self.tools_dir / tool_name.replace("_tool", "") / "__init__.py",
            self.src_tools_dir / tool_name.replace("_tool", "") / "__init__.py",
            self.tools_dir / f"{tool_name.replace('_tool', '')}.py",
            self.src_tools_dir / f"{tool_name.replace('_tool', '')}.py",
        ]

    def _load_cache(self) -> Dict[str, Dict[str, Any]]:
        """
        Load cache from disk.
        """
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r") as f:
                    cache = json.load(f)
                    # Validate cache version and environment
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
        # Check if cache has environment metadata
        if "_environment" not in cache:
            return False

        env = cache["_environment"]
        current_env = self._get_environment()

        # Must match Python version
        if env.get("python_version") != current_env["python_version"]:
            return False

        # Cache is compatible
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
            # Add environment metadata
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
            tool_name: Tool file name (e.g., "workspace_tool", "entity_tool")

        Returns:
            MD5 hash of tool file content or "unknown" if not found
        """
        # Use customizable search paths
        possible_paths = self.get_tool_search_paths(tool_name)

        for tool_file in possible_paths:
            if tool_file.exists():
                return self.get_file_hash(tool_file)

        return "unknown"

    def get_dependencies_hash(self, tool_name: str) -> str:
        """Get combined hash of all dependencies for a tool.

        Args:
            tool_name: Tool file name (e.g., "workspace_tool", "entity_tool")

        Returns:
            Combined MD5 hash of all dependency files
        """
        # Get dependency paths for this tool from subclass
        tool_deps = self.get_tool_dependencies()
        dep_paths = tool_deps.get(tool_name, [])

        # Collect all dependency hashes
        hashes = []
        for dep_path in dep_paths:
            full_path = self.project_root / dep_path
            dep_hash = self.get_file_hash(full_path)
            hashes.append(dep_hash)

        # Combine all hashes
        if hashes:
            combined = "".join(hashes)
            return hashlib.md5(combined.encode()).hexdigest()

        return "none"

    def get_framework_hash(self) -> str:
        """Get combined hash of framework core files.

        Returns:
            Combined MD5 hash of all framework files
        """
        framework_files = self.get_framework_files()
        hashes = []
        for framework_file in framework_files:
            full_path = self.project_root / framework_file
            file_hash = self.get_file_hash(full_path)
            hashes.append(file_hash)

        # Combine all hashes
        combined = "".join(hashes)
        return hashlib.md5(combined.encode()).hexdigest()

    def should_skip(
        self,
        test_name: str,
        tool_name: str,
        test_file_path: Optional[Path | str] = None,
    ) -> bool:
        """Check if test should be skipped based on comprehensive cache validation.

        Args:
            test_name: Name of the test function
            tool_name: Name of the tool being tested
            test_file_path: Path to the test file itself (optional)

        Returns:
            True if test can be skipped (ALL unchanged: tool, deps, framework, test file)

        IMPORTANT: Failed tests are NEVER cached - always re-run to verify fixes.
        """
        # Check if test is cached
        if test_name not in self.cache:
            return False

        cached = self.cache[test_name]

        # CRITICAL: Must have passed previously - NEVER skip failed tests
        if cached.get("status") != "passed":
            # Failed, error, or skipped tests must always re-run
            return False

        # Check age (< 7 days)
        if time.time() - cached.get("timestamp", 0) >= 7 * 24 * 3600:
            return False

        # Check tool file hash
        tool_hash = self.get_tool_hash(tool_name)
        if cached.get("tool_hash") != tool_hash:
            return False

        # Check dependencies hash
        deps_hash = self.get_dependencies_hash(tool_name)
        if cached.get("dependencies_hash") != deps_hash:
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
        # Compute all hashes
        tool_hash = self.get_tool_hash(tool_name)
        deps_hash = self.get_dependencies_hash(tool_name)
        framework_hash = self.get_framework_hash()
        test_hash = self.get_file_hash(test_file_path) if test_file_path else None

        # Store comprehensive cache entry
        self.cache[test_name] = {
            "tool_hash": tool_hash,
            "dependencies_hash": deps_hash,
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
        to_remove = []

        for test_name, cached_data in self.cache.items():
            if cached_data.get("tool_name") == tool_name:
                to_remove.append(test_name)

        for key in to_remove:
            del self.cache[key]

        self._save_cache()

    def clear_all(self):
        """
        Clear all cached test results (alias for clear()).
        """
        self.clear()

    def invalidate_by_file(self, file_path: Path | str):
        """Invalidate cache entries affected by a file change.

        Args:
            file_path: Path to the file that changed
        """
        file_path = Path(file_path)
        relative_path = None

        try:
            relative_path = file_path.relative_to(self.project_root)
        except ValueError:
            # File not in project root
            return

        relative_str = str(relative_path)
        to_remove = []

        # Get mappings from subclass
        tool_deps = self.get_tool_dependencies()
        framework_files = self.get_framework_files()

        # Check which tests are affected by this file
        for test_name, cached_data in self.cache.items():
            tool_name = cached_data.get("tool_name", "")

            # Check if it's the tool file itself
            if any(
                relative_str == dep_path or relative_str.endswith(dep_path)
                for dep_path in [
                    f"tools/{tool_name}.py",
                    f"tools/{tool_name.replace('_tool', '')}.py",
                ]
            ):
                to_remove.append(test_name)
                continue

            # Check if it's a dependency
            deps = tool_deps.get(tool_name, [])
            if any(
                relative_str == dep_path or relative_str.endswith(dep_path) for dep_path in deps
            ):
                to_remove.append(test_name)
                continue

            # Check if it's a framework file
            if any(relative_str == fw_file for fw_file in framework_files):
                to_remove.append(test_name)
                continue

        # Remove affected entries
        for key in to_remove:
            del self.cache[key]

        if to_remove:
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

        deps_hash = self.get_dependencies_hash(tool_name)
        if cached.get("dependencies_hash") != deps_hash:
            return "Dependencies changed"

        framework_hash = self.get_framework_hash()
        if cached.get("framework_hash") != framework_hash:
            return "Framework changed"

        if test_file_path:
            test_hash = self.get_file_hash(test_file_path)
            if cached.get("test_hash") != test_hash:
                return "Test file changed"

        return None


# Usage Example:
# ===============
#
# from pheno.testing.mcp_qa.testing.test_cache import BaseTestCache
# from pathlib import Path
#
# # Create a concrete implementation
# class MyTestCache(BaseTestCache):
#     def get_tool_dependencies(self):
#         return {
#             "my_tool": ["tools/base.py", "errors.py"],
#         }
#
#     def get_framework_files(self):
#         return ["tests/framework/__init__.py"]
#
# # Initialize cache
# cache = MyTestCache()
#
# # Before running a test, check if it should be skipped
# test_file = Path(__file__)
# if cache.should_skip("test_my_feature", "my_tool", test_file):
#     print("Skipping test - cached result is still valid")
#     return
#
# # Run the test
# start = time.time()
# try:
#     run_test()
#     status = "passed"
#     error = None
# except Exception as e:
#     status = "failed"
#     error = str(e)
# duration = time.time() - start
#
# # Record the result
# cache.record("test_my_feature", "my_tool", status, duration, error, test_file)
