"""Pheno-SDK Vendoring System.

Handles vendoring of pheno-sdk packages for production deployments. Provides
programmatic access to replace custom shell scripts.
"""

import importlib.util
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PackageInfo:
    """
    Information about a pheno-sdk package.
    """

    dir_name: str  # Directory name in pheno-sdk (e.g., "adapter-kit")
    module_name: str  # Python module name (e.g., "adapter_kit")
    source_path: Path
    is_available: bool = False
    has_setup: bool = False
    python_files_count: int = 0
    size_bytes: int = 0


class PhenoVendor:
    """Vendoring manager for pheno-sdk packages.

    Usage:
        vendor = PhenoVendor(project_root="/path/to/project")
        vendor.vendor_all()
        vendor.validate()
    """

    # Known pheno-sdk packages (directory -> module name mapping)
    PACKAGE_MAPPINGS = {
        "pydevkit": "pydevkit",
        "adapter-kit": "adapter_kit",
        "stream-kit": "stream_kit",
        "storage-kit": "storage_kit",
        "db-kit": "db_kit",
        "mcp-QA": "mcp_qa",
        "process-monitor-sdk": "process_monitor",
        "tui-kit": "tui_kit",
        "workflow-kit": "workflow_kit",
        "event-kit": "event_kit",
        "deploy-kit": "deploy_kit",
        "observability-kit": "observability_kit",
        "cli-builder-kit": "cli_builder",
        "filewatch-kit": "filewatch_kit",
        "mcp-sdk-kit": "mcp_sdk_kit",
    }

    # Files/dirs to exclude from vendoring
    EXCLUDE_PATTERNS = {
        "__pycache__",
        "*.pyc",
        "*.pyo",
        ".pytest_cache",
        ".mypy_cache",
        "*.egg-info",
        ".git",
        ".github",
        "tests",
        "docs",
        "examples",
        ".venv",
        "venv",
        "node_modules",
    }

    def __init__(
        self,
        project_root: Path | None = None,
        pheno_sdk_root: Path | None = None,
        vendor_dir: str = "pheno_vendor",
    ):
        """Initialize the vendoring manager.

        Args:
            project_root: Root of the project to vendor into (default: cwd)
            pheno_sdk_root: Location of pheno-sdk (default: ../pheno-sdk)
            vendor_dir: Name of vendor directory (default: pheno_vendor)
        """
        self.project_root = Path(project_root or Path.cwd()).resolve()

        # Auto-detect pheno-sdk location
        if pheno_sdk_root:
            self.pheno_sdk_root = Path(pheno_sdk_root).resolve()
        else:
            # Try common locations
            candidates = [
                self.project_root.parent / "pheno-sdk",
                Path.home() / "temp-PRODVERCEL/485/kush/pheno-sdk",
                Path("/Users/kooshapari/temp-PRODVERCEL/485/kush/pheno-sdk"),
            ]
            for candidate in candidates:
                if candidate.exists() and candidate.is_dir():
                    self.pheno_sdk_root = candidate
                    break
            else:
                raise FileNotFoundError(
                    "Could not find pheno-sdk. Set PHENO_SDK_ROOT environment "
                    "variable or pass pheno_sdk_root parameter.",
                )

        self.vendor_dir = self.project_root / vendor_dir
        self.packages: dict[str, PackageInfo] = {}

        # Scan available packages
        self._scan_packages()

    def _scan_packages(self) -> None:
        """
        Scan pheno-sdk for available packages.
        """
        for dir_name, module_name in self.PACKAGE_MAPPINGS.items():
            source_path = self.pheno_sdk_root / dir_name

            pkg_info = PackageInfo(
                dir_name=dir_name,
                module_name=module_name,
                source_path=source_path,
            )

            if source_path.exists():
                pkg_info.is_available = True

                # Check for setup files
                pkg_info.has_setup = any(
                    [
                        (source_path / "setup.py").exists(),
                        (source_path / "setup.cfg").exists(),
                        (source_path / "pyproject.toml").exists(),
                    ],
                )

                # Count Python files
                if pkg_info.has_setup:
                    py_files = list(source_path.rglob("*.py"))
                    pkg_info.python_files_count = len(py_files)
                    pkg_info.size_bytes = sum(f.stat().st_size for f in py_files)

            self.packages[module_name] = pkg_info

    def detect_used_packages(self) -> set[str]:
        """Auto-detect which pheno-sdk packages are used by this project.

        Returns:
            Set of module names that are imported in the project
        """
        used_packages = set()

        # Check requirements.txt
        req_file = self.project_root / "requirements.txt"
        if req_file.exists():
            content = req_file.read_text()
            for module_name in self.packages:
                # Look for editable installs
                if f"pheno-sdk/{self.packages[module_name].dir_name}" in content:
                    used_packages.add(module_name)

        # Check Python imports in project
        for py_file in self.project_root.rglob("*.py"):
            if "pheno_vendor" in str(py_file) or ".venv" in str(py_file):
                continue

            try:
                content = py_file.read_text()
                for module_name in self.packages:
                    # Look for import statements
                    patterns = [
                        f"import {module_name}",
                        f"from {module_name}",
                    ]
                    if any(pattern in content for pattern in patterns):
                        used_packages.add(module_name)
            except Exception:
                pass

        return used_packages

    def vendor_packages(
        self,
        packages: list[str] | None = None,
        auto_detect: bool = True,
        clean: bool = True,
    ) -> dict[str, bool]:
        """Vendor specified packages (or auto-detect).

        Args:
            packages: List of package module names to vendor (None = all)
            auto_detect: If True, only vendor packages actually used
            clean: Clean vendor dir before vendoring

        Returns:
            Dict mapping package name to success status
        """
        results = {}

        # Determine which packages to vendor
        if packages is None:
            if auto_detect:
                packages_to_vendor = self.detect_used_packages()
            else:
                packages_to_vendor = {
                    name
                    for name, info in self.packages.items()
                    if info.is_available and info.has_setup
                }
        else:
            packages_to_vendor = set(packages)

        # Clean vendor directory
        if clean and self.vendor_dir.exists():
            shutil.rmtree(self.vendor_dir)

        # Create vendor directory
        self.vendor_dir.mkdir(parents=True, exist_ok=True)

        # Create __init__.py
        init_file = self.vendor_dir / "__init__.py"
        init_file.write_text(
            '''"""
Vendored pheno-sdk packages for production deployment.

This directory contains copies of pheno-sdk packages to avoid
dependency on relative paths in production environments.
"""

__version__ = "1.0.0"
''',
        )

        # Vendor each package
        for module_name in packages_to_vendor:
            if module_name not in self.packages:
                results[module_name] = False
                continue

            pkg_info = self.packages[module_name]
            if not pkg_info.is_available or not pkg_info.has_setup:
                results[module_name] = False
                continue

            try:
                self._copy_package(pkg_info)
                results[module_name] = True
            except Exception as e:
                print(f"Failed to vendor {module_name}: {e}")
                results[module_name] = False

        # Handle KInfra if it exists
        self._handle_kinfra()

        return results

    def _copy_package(self, pkg_info: PackageInfo) -> None:
        """
        Copy a single package to vendor directory.
        """
        dest_path = self.vendor_dir / pkg_info.module_name

        # Find the actual Python package
        source_pkg_path = pkg_info.source_path / pkg_info.module_name

        if not source_pkg_path.exists():
            # Try src/ layout
            src_path = pkg_info.source_path / "src" / pkg_info.module_name
            if src_path.exists():
                source_pkg_path = src_path
            else:
                # Use the whole directory
                source_pkg_path = pkg_info.source_path

        # Copy the package
        if source_pkg_path.is_dir():
            shutil.copytree(
                source_pkg_path,
                dest_path,
                ignore=shutil.ignore_patterns(*self.EXCLUDE_PATTERNS),
                dirs_exist_ok=True,
            )

        # Copy metadata files
        for meta_file in ["setup.py", "setup.cfg", "pyproject.toml", "README.md", "LICENSE"]:
            meta_src = pkg_info.source_path / meta_file
            if meta_src.exists():
                shutil.copy2(meta_src, dest_path / meta_file)

    def _handle_kinfra(self) -> None:
        """
        Handle KInfra package (special case).
        """
        kinfra_path = self.pheno_sdk_root / "KInfra"

        if not kinfra_path.exists():
            return

        # KInfra might be a symlink
        if kinfra_path.is_symlink():
            kinfra_path = kinfra_path.resolve()

        # Look for Python library
        kinfra_python = kinfra_path / "libraries/python"
        if not kinfra_python.exists():
            return

        dest_path = self.vendor_dir / "kinfra"

        # Find the actual package
        kinfra_pkg = kinfra_python / "kinfra"
        if kinfra_pkg.exists():
            shutil.copytree(
                kinfra_pkg,
                dest_path,
                ignore=shutil.ignore_patterns(*self.EXCLUDE_PATTERNS),
                dirs_exist_ok=True,
            )

        # Copy metadata
        for meta_file in ["setup.py", "pyproject.toml", "README.md"]:
            meta_src = kinfra_python / meta_file
            if meta_src.exists():
                shutil.copy2(meta_src, dest_path / meta_file)

    def generate_prod_requirements(
        self,
        output_file: Path | None = None,
    ) -> Path:
        """Generate requirements-prod.txt without pheno-sdk editable installs.

        Args:
            output_file: Path to output file (default: requirements-prod.txt)

        Returns:
            Path to generated file
        """
        if output_file is None:
            output_file = self.project_root / "requirements-prod.txt"
        else:
            output_file = Path(output_file)

        req_file = self.project_root / "requirements.txt"
        if not req_file.exists():
            raise FileNotFoundError(f"requirements.txt not found at {req_file}")

        # Read requirements
        lines = req_file.read_text().splitlines()

        # Filter out pheno-sdk editable installs
        prod_lines = []
        prod_lines.append("# " + "=" * 76)
        prod_lines.append("# Production Requirements")
        prod_lines.append("# " + "=" * 76)
        prod_lines.append("# This file uses VENDORED pheno-sdk packages from pheno_vendor/")
        prod_lines.append("# For development, use requirements.txt with editable installs")
        prod_lines.append("# Generated by pheno-vendor")
        prod_lines.append("# " + "=" * 76)
        prod_lines.append("")

        for line in lines:
            # Skip editable pheno-sdk installs
            if line.strip().startswith("-e") and "pheno-sdk" in line:
                continue
            # Skip comments about pheno-sdk
            if "PHENO-SDK" in line.upper():
                continue
            # Keep everything else
            prod_lines.append(line)

        # Write production requirements
        output_file.write_text("\n".join(prod_lines))

        return output_file

    def create_sitecustomize(self) -> Path:
        """Create sitecustomize.py to add pheno_vendor to sys.path.

        Returns:
            Path to created file
        """
        sitecustomize = self.project_root / "sitecustomize.py"

        sitecustomize.write_text(
            '''"""
Site customization to add vendored pheno-sdk packages to sys.path.

This file is automatically loaded by Python at startup and ensures
vendored packages in pheno_vendor/ are available for import.
"""

import sys
from pathlib import Path

# Add pheno_vendor to path if it exists
vendor_path = Path(__file__).parent / "pheno_vendor"
if vendor_path.exists() and str(vendor_path) not in sys.path:
    sys.path.insert(0, str(vendor_path))
''',
        )

        return sitecustomize

    def validate_vendored(
        self, packages: list[str] | None = None,
    ) -> dict[str, tuple[bool, str]]:
        """Validate vendored packages.

        Args:
            packages: List of packages to validate (None = all in vendor dir)

        Returns:
            Dict mapping package name to (success, message) tuple
        """
        results = {}

        if not self.vendor_dir.exists():
            return {"vendor_dir": (False, "Vendor directory does not exist")}

        # Determine packages to validate
        if packages is None:
            vendored_packages = [
                d.name
                for d in self.vendor_dir.iterdir()
                if d.is_dir() and not d.name.startswith("_")
            ]
        else:
            vendored_packages = packages

        for pkg_name in vendored_packages:
            pkg_path = self.vendor_dir / pkg_name

            if not pkg_path.exists():
                results[pkg_name] = (False, "Package directory not found")
                continue

            # Check for Python files
            py_files = list(pkg_path.rglob("*.py"))
            if not py_files:
                results[pkg_name] = (False, "No Python files found")
                continue

            # Check for __init__.py
            init_file = pkg_path / "__init__.py"
            if not init_file.exists():
                results[pkg_name] = (False, "No __init__.py found")
                continue

            results[pkg_name] = (True, f"Valid ({len(py_files)} Python files)")

        return results

    def test_imports(self, packages: list[str] | None = None) -> dict[str, tuple[bool, str]]:
        """Test that vendored packages can be imported.

        Args:
            packages: List of packages to test (None = all in vendor dir)

        Returns:
            Dict mapping package name to (success, message) tuple
        """
        results = {}

        # Add vendor dir to path temporarily
        vendor_str = str(self.vendor_dir)
        if vendor_str not in sys.path:
            sys.path.insert(0, vendor_str)

        if packages is None:
            packages = [
                d.name
                for d in self.vendor_dir.iterdir()
                if d.is_dir() and not d.name.startswith("_")
            ]

        for pkg_name in packages:
            try:
                # Try to import
                spec = importlib.util.find_spec(pkg_name)
                if spec is None:
                    results[pkg_name] = (False, "Module not found")
                    continue

                # Try to load
                module = importlib.util.module_from_spec(spec)
                if spec.loader:
                    spec.loader.exec_module(module)

                results[pkg_name] = (True, f"Import successful (from {spec.origin})")
            except Exception as e:
                results[pkg_name] = (False, f"Import failed: {e}")

        # Remove vendor dir from path
        if vendor_str in sys.path:
            sys.path.remove(vendor_str)

        return results

    def generate_manifest(self) -> Path:
        """Generate manifest of vendored packages.

        Returns:
            Path to manifest file
        """
        manifest_path = self.vendor_dir / "VENDOR_MANIFEST.txt"

        lines = ["Pheno-SDK Vendored Packages Manifest"]
        lines.append(f"Generated: {subprocess.check_output(['date']).decode().strip()}")
        lines.append(f"Source: {self.pheno_sdk_root}")
        lines.append("")
        lines.append("Packages:")

        for pkg_dir in sorted(self.vendor_dir.iterdir()):
            if not pkg_dir.is_dir() or pkg_dir.name.startswith("_"):
                continue

            files = list(pkg_dir.rglob("*"))
            py_files = [f for f in files if f.suffix == ".py"]

            # Calculate size
            size_bytes = sum(f.stat().st_size for f in files if f.is_file())
            size_mb = size_bytes / (1024 * 1024)

            lines.append(f"  - {pkg_dir.name} ({len(py_files)} .py files, {size_mb:.2f} MB)")

        # Total size
        total_size = sum(f.stat().st_size for f in self.vendor_dir.rglob("*") if f.is_file())
        total_mb = total_size / (1024 * 1024)
        lines.append("")
        lines.append(f"Total size: {total_mb:.2f} MB")

        manifest_path.write_text("\n".join(lines))
        return manifest_path

    def clean(self) -> bool:
        """Remove vendored packages directory.

        Returns:
            True if successful
        """
        if self.vendor_dir.exists():
            shutil.rmtree(self.vendor_dir)
            return True
        return False

    def vendor_all(self, auto_detect: bool = True, validate: bool = True) -> bool:
        """Complete vendoring workflow.

        Args:
            auto_detect: Only vendor packages actually used
            validate: Run validation after vendoring

        Returns:
            True if successful
        """
        print(f"Vendoring pheno-sdk packages to {self.vendor_dir}")
        print(f"Source: {self.pheno_sdk_root}")
        print()

        # Vendor packages
        results = self.vendor_packages(auto_detect=auto_detect)

        successful = sum(1 for success in results.values() if success)
        print(f"Vendored {successful}/{len(results)} packages")

        # Generate files
        print("\nGenerating production files...")
        self.generate_prod_requirements()
        print("  Created requirements-prod.txt")

        self.create_sitecustomize()
        print("  Created sitecustomize.py")

        self.generate_manifest()
        print("  Created VENDOR_MANIFEST.txt")

        # Validate
        if validate:
            print("\nValidating vendored packages...")
            validation_results = self.validate_vendored()

            for pkg_name, (success, message) in validation_results.items():
                status = "✓" if success else "✗"
                print(f"  {status} {pkg_name}: {message}")

            all_valid = all(success for success, _ in validation_results.values())

            if all_valid:
                print("\n✓ All packages validated successfully!")
                return True
            print("\n✗ Some packages failed validation")
            return False

        return successful > 0
