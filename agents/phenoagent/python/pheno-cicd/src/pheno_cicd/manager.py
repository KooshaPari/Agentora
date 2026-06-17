"""
CI/CD management system for unified control across projects.
"""

import json
import sys
from pathlib import Path
from typing import Any

from .adapters import (
    DefaultConfigProvider,
    FileSystemRepository,
    FileSystemSyncProvider,
)
from .core import ProjectType
from .generator import CICDGeneratorFactory
from .quality import QualityGateIntegrator
from .sync import CICDSynchronizer, SoftDependencyManager, SyncStrategy


class CICDManager:
    """
    Main CI/CD management system.
    """

    def __init__(self, base_path: Path | None = None):
        self.base_path = base_path or Path.cwd()
        self.config_provider = DefaultConfigProvider()
        self.repository = FileSystemRepository(self.base_path)
        self.sync_provider = FileSystemSyncProvider(self.base_path)
        self.synchronizer = CICDSynchronizer(self.sync_provider)
        self.dependency_manager = SoftDependencyManager(self.base_path)
        self.quality_integrator = QualityGateIntegrator()

        # Load project registry
        self.project_registry = self._load_project_registry()

    def _load_project_registry(self) -> dict[str, dict[str, Any]]:
        """
        Load project registry from configuration.
        """
        registry_file = self.base_path / ".cicd" / "project-registry.json"

        if registry_file.exists():
            try:
                with open(registry_file) as f:
                    return json.load(f)
            except Exception:
                pass

        # Default registry - adjust paths based on current directory structure
        base_path = self.base_path
        if base_path.name == "pheno-sdk":
            # We're in pheno-sdk directory
            return {
                "pheno-sdk": {
                    "type": "pheno-sdk",
                    "path": ".",
                    "dependencies": [
                        "../zen-mcp-server",
                        "../atoms_mcp-old",
                        "../morph",
                        "../router",
                    ],
                    "auto_sync": True,
                    "quality_threshold": 80.0,
                },
            }
        # We're in the parent directory
        return {
            "pheno-sdk": {
                "type": "pheno-sdk",
                "path": "pheno-sdk",
                "dependencies": ["zen-mcp-server", "atoms_mcp-old", "morph", "router"],
                "auto_sync": True,
                "quality_threshold": 80.0,
            },
            "zen-mcp-server": {
                "type": "zen-mcp-server",
                "path": "zen-mcp-server",
                "dependencies": ["example/zen-mcp-server"],
                "auto_sync": True,
                "quality_threshold": 75.0,
            },
            "atoms_mcp-old": {
                "type": "atoms_mcp-old",
                "path": "atoms_mcp-old",
                "dependencies": [],
                "auto_sync": True,
                "quality_threshold": 70.0,
            },
            "morph": {
                "type": "morph",
                "path": "morph",
                "dependencies": [],
                "auto_sync": False,
                "quality_threshold": 70.0,
            },
            "router": {
                "type": "router",
                "path": "router",
                "dependencies": [],
                "auto_sync": False,
                "quality_threshold": 70.0,
            },
        }

    def generate_all(self, force: bool = False) -> dict[str, bool]:
        """
        Generate CI/CD for all projects.
        """
        results = {}

        for project_name, project_info in self.project_registry.items():
            try:
                project_path = self.base_path / project_info["path"]

                if not project_path.exists():
                    print(f"⚠️ Project {project_name} not found at {project_path}")
                    results[project_name] = False
                    continue

                # Check if already generated
                if not force and self.repository.load_pipeline(project_path):
                    print(f"ℹ️ CI/CD already exists for {project_name}, use --force to regenerate")
                    results[project_name] = True
                    continue

                # Generate CI/CD
                project_type = ProjectType(project_info["type"])
                config = self.config_provider.get_default_config(project_type)
                config.project_name = project_name

                # Apply project-specific settings
                if "quality_threshold" in project_info:
                    config.quality_thresholds["quality_score_threshold"] = project_info[
                        "quality_threshold"
                    ]

                generator = CICDGeneratorFactory.create_generator_from_config(config)
                pipeline = generator.generate_all(project_path)

                # Save pipeline
                self.repository.save_pipeline(project_path, pipeline)

                print(f"✅ Generated CI/CD for {project_name}")
                results[project_name] = True

            except Exception as e:
                print(f"❌ Error generating CI/CD for {project_name}: {e}")
                results[project_name] = False

        return results

    def sync_all(
        self, strategy: SyncStrategy = SyncStrategy.BACKUP_AND_OVERWRITE,
    ) -> dict[str, bool]:
        """
        Synchronize CI/CD across all projects.
        """
        results = {}

        # Get projects with auto_sync enabled
        auto_sync_projects = {
            name: info
            for name, info in self.project_registry.items()
            if info.get("auto_sync", False)
        }

        for project_name, project_info in auto_sync_projects.items():
            try:
                source_path = self.base_path / project_info["path"]
                dependencies = project_info.get("dependencies", [])

                if not dependencies:
                    print(f"ℹ️ No dependencies for {project_name}")
                    results[project_name] = True
                    continue

                # Sync to dependencies
                target_paths = [self.base_path / dep for dep in dependencies]
                target_paths = [p for p in target_paths if p.exists()]

                if not target_paths:
                    print(f"ℹ️ No valid dependency paths for {project_name}")
                    results[project_name] = True
                    continue

                sync_results = self.synchronizer.sync_all_projects(
                    source_path, target_paths, strategy,
                )
                success_count = sum(1 for r in sync_results if r.success)
                total_count = len(sync_results)

                print(f"🔄 Synced {project_name} to {success_count}/{total_count} dependencies")
                results[project_name] = success_count == total_count

            except Exception as e:
                print(f"❌ Error syncing {project_name}: {e}")
                results[project_name] = False

        return results

    def update_soft_dependencies(
        self, project_name: str, dependency_types: list[str] | None = None,
    ) -> bool:
        """
        Update soft dependencies for a project.
        """
        try:
            if project_name not in self.project_registry:
                print(f"❌ Project {project_name} not found in registry")
                return False

            project_info = self.project_registry[project_name]
            dependencies = project_info.get("dependencies", [])

            if not dependencies:
                print(f"ℹ️ No dependencies for {project_name}")
                return True

            source_path = self.base_path / project_info["path"]
            target_paths = [self.base_path / dep for dep in dependencies]
            target_paths = [p for p in target_paths if p.exists()]

            if not target_paths:
                print(f"ℹ️ No valid dependency paths for {project_name}")
                return True

            if dependency_types is None:
                dependency_types = ["workflows", "docker", "makefile", "config"]

            results = self.synchronizer.update_soft_dependencies(
                source_path, target_paths, dependency_types,
            )

            success_count = sum(1 for r in results if r.success)
            total_count = len(results)

            print(
                f"🔄 Updated {project_name} dependencies: {success_count}/{total_count} successful",
            )

            for i, result in enumerate(results):
                dependency = dependencies[i]
                if result.success:
                    print(f"✅ {dependency}: {', '.join(result.changes)}")
                else:
                    print(f"❌ {dependency}: {result.error_message}")

            return success_count == total_count

        except Exception as e:
            print(f"❌ Error updating dependencies for {project_name}: {e}")
            return False

    def update_all_dependencies(self, dependency_types: list[str] | None = None) -> dict[str, bool]:
        """
        Update soft dependencies for all projects.
        """
        results = {}

        for project_name in self.project_registry:
            results[project_name] = self.update_soft_dependencies(project_name, dependency_types)

        return results

    def validate_all(self) -> dict[str, list[str]]:
        """
        Validate CI/CD configuration for all projects.
        """
        results = {}

        for project_name, project_info in self.project_registry.items():
            try:
                project_path = self.base_path / project_info["path"]

                if not project_path.exists():
                    results[project_name] = [f"Project path not found: {project_path}"]
                    continue

                # Load configuration
                config = self.repository.load_config(project_path)
                if not config:
                    results[project_name] = ["No CI/CD configuration found"]
                    continue

                # Validate configuration
                errors = self.config_provider.validate_config(config)
                results[project_name] = errors

            except Exception as e:
                results[project_name] = [f"Validation error: {e}"]

        return results

    def status_all(self) -> dict[str, dict[str, Any]]:
        """
        Get status for all projects.
        """
        results = {}

        for project_name, project_info in self.project_registry.items():
            try:
                project_path = self.base_path / project_info["path"]

                if not project_path.exists():
                    results[project_name] = {"status": "not_found", "path": str(project_path)}
                    continue

                # Load configuration and pipeline
                config = self.repository.load_config(project_path)
                pipeline = self.repository.load_pipeline(project_path)

                # Get sync status
                sync_status = self.sync_provider.get_sync_status(project_path)

                results[project_name] = {
                    "status": "configured" if config else "not_configured",
                    "pipeline_generated": pipeline is not None,
                    "generated_at": pipeline.generated_at.isoformat() if pipeline else None,
                    "files_count": len(pipeline.list_files()) if pipeline else 0,
                    "last_sync": sync_status.get("last_sync"),
                    "has_changes": sync_status.get("has_changes", False),
                    "backup_count": sync_status.get("backup_count", 0),
                    "dependencies": project_info.get("dependencies", []),
                    "auto_sync": project_info.get("auto_sync", False),
                }

            except Exception as e:
                results[project_name] = {"status": "error", "error": str(e)}

        return results

    def add_project(
        self, name: str, project_type: str, path: str, dependencies: list[str] | None = None,
    ) -> bool:
        """
        Add a new project to the registry.
        """
        try:
            self.project_registry[name] = {
                "type": project_type,
                "path": path,
                "dependencies": dependencies or [],
                "auto_sync": True,
                "quality_threshold": 70.0,
            }

            self._save_project_registry()
            print(f"✅ Added project {name} to registry")
            return True

        except Exception as e:
            print(f"❌ Error adding project {name}: {e}")
            return False

    def remove_project(self, name: str) -> bool:
        """
        Remove a project from the registry.
        """
        try:
            if name not in self.project_registry:
                print(f"❌ Project {name} not found in registry")
                return False

            del self.project_registry[name]
            self._save_project_registry()
            print(f"✅ Removed project {name} from registry")
            return True

        except Exception as e:
            print(f"❌ Error removing project {name}: {e}")
            return False

    def update_project_config(self, name: str, config_updates: dict[str, Any]) -> bool:
        """
        Update project configuration.
        """
        try:
            if name not in self.project_registry:
                print(f"❌ Project {name} not found in registry")
                return False

            self.project_registry[name].update(config_updates)
            self._save_project_registry()
            print(f"✅ Updated configuration for {name}")
            return True

        except Exception as e:
            print(f"❌ Error updating project {name}: {e}")
            return False

    def _save_project_registry(self):
        """
        Save project registry to file.
        """
        registry_file = self.base_path / ".cicd" / "project-registry.json"
        registry_file.parent.mkdir(exist_ok=True)

        with open(registry_file, "w") as f:
            json.dump(self.project_registry, f, indent=2)

    def run_quality_checks(self, project_name: str | None = None) -> dict[str, bool]:
        """
        Run quality checks for projects.
        """
        results = {}

        projects_to_check = [project_name] if project_name else list(self.project_registry.keys())

        for name in projects_to_check:
            if name not in self.project_registry:
                results[name] = False
                continue

            try:
                project_path = self.base_path / self.project_registry[name]["path"]

                if not project_path.exists():
                    results[name] = False
                    continue

                # Run quality analysis
                project_type = ProjectType(self.project_registry[name]["type"])
                config = self.config_provider.get_default_config(project_type)

                generator = CICDGeneratorFactory.create_generator_from_config(config)
                pipeline = generator.generate_all(project_path)

                # Integrate quality checks
                pipeline = self.quality_integrator.integrate_quality_checks(pipeline)

                # Save updated pipeline
                self.repository.save_pipeline(project_path, pipeline)

                print(f"✅ Updated quality checks for {name}")
                results[name] = True

            except Exception as e:
                print(f"❌ Error running quality checks for {name}: {e}")
                results[name] = False

        return results


def main():
    """
    Main entry point for CI/CD management.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Pheno CI/CD Manager")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Generate command
    generate_parser = subparsers.add_parser("generate", help="Generate CI/CD for all projects")
    generate_parser.add_argument("--force", action="store_true", help="Force regeneration")

    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Synchronize CI/CD across projects")
    sync_parser.add_argument(
        "--strategy",
        choices=[s.value for s in SyncStrategy],
        default=SyncStrategy.BACKUP_AND_OVERWRITE.value,
        help="Sync strategy",
    )

    # Update command
    update_parser = subparsers.add_parser("update", help="Update soft dependencies")
    update_parser.add_argument("--project", help="Specific project to update")
    update_parser.add_argument("--types", nargs="+", help="Dependency types to update")

    # Status command
    subparsers.add_parser("status", help="Show status for all projects")

    # Validate command
    subparsers.add_parser("validate", help="Validate CI/CD configurations")

    # Quality command
    quality_parser = subparsers.add_parser("quality", help="Run quality checks")
    quality_parser.add_argument("--project", help="Specific project to check")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    manager = CICDManager()

    try:
        if args.command == "generate":
            results = manager.generate_all(force=args.force)
            success_count = sum(1 for r in results.values() if r)
            total_count = len(results)
            print(f"\\n📊 Generated CI/CD for {success_count}/{total_count} projects")
            return 0 if success_count == total_count else 1

        if args.command == "sync":
            results = manager.sync_all(SyncStrategy(args.strategy))
            success_count = sum(1 for r in results.values() if r)
            total_count = len(results)
            print(f"\\n📊 Synced {success_count}/{total_count} projects")
            return 0 if success_count == total_count else 1

        if args.command == "update":
            if args.project:
                success = manager.update_soft_dependencies(args.project, args.types)
                return 0 if success else 1
            results = manager.update_all_dependencies(args.types)
            success_count = sum(1 for r in results.values() if r)
            total_count = len(results)
            print(f"\\n📊 Updated dependencies for {success_count}/{total_count} projects")
            return 0 if success_count == total_count else 1

        if args.command == "status":
            results = manager.status_all()
            print("\\n📊 CI/CD Status:")
            for name, status in results.items():
                print(f"\\n{name}:")
                for key, value in status.items():
                    print(f"  {key}: {value}")
            return 0

        if args.command == "validate":
            results = manager.validate_all()
            print("\\n📊 Validation Results:")
            for name, errors in results.items():
                if errors:
                    print(f"\\n❌ {name}:")
                    for error in errors:
                        print(f"  - {error}")
                else:
                    print(f"\\n✅ {name}: Valid")
            return 0

        if args.command == "quality":
            results = manager.run_quality_checks(args.project)
            success_count = sum(1 for r in results.values() if r)
            total_count = len(results)
            print(f"\\n📊 Updated quality checks for {success_count}/{total_count} projects")
            return 0 if success_count == total_count else 1

        parser.print_help()
        return 1

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
