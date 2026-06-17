"""
CI/CD generation and synchronization CLI.
"""

import argparse
import json
import sys
from pathlib import Path

from .adapters import (
    DefaultConfigProvider,
    FileSystemRepository,
    FileSystemSyncProvider,
)
from .core import CICDConfig, ProjectType
from .generator import CICDGeneratorFactory
from .sync import CICDSynchronizer, SoftDependencyManager, SyncStrategy


class CICDCLI:
    """
    CI/CD CLI interface.
    """

    def __init__(self):
        self.config_provider = DefaultConfigProvider()
        self.repository = FileSystemRepository(Path.cwd())
        self.sync_provider = FileSystemSyncProvider(Path.cwd())
        self.synchronizer = CICDSynchronizer(self.sync_provider)
        self.dependency_manager = SoftDependencyManager(Path.cwd())

    def generate(self, args) -> int:
        """
        Generate CI/CD pipeline.
        """
        try:
            # Determine project type
            project_type = (
                ProjectType(args.project_type)
                if args.project_type
                else self._detect_project_type(args.path)
            )

            # Create or load configuration
            if args.config:
                config = self._load_config_from_file(args.config)
            else:
                config = self.config_provider.get_default_config(project_type)
                config.project_name = args.project_name or project_type.value

            # Create generator
            generator = CICDGeneratorFactory.create_generator_from_config(config)

            # Generate pipeline
            project_path = Path(args.path)
            pipeline = generator.generate_all(project_path)

            # Save pipeline
            self.repository.save_pipeline(project_path, pipeline)

            print(f"✅ Generated CI/CD pipeline for {config.project_name}")
            print("📁 Files created:")
            for file_path in pipeline.list_files():
                print(f"  - {file_path}")

            return 0

        except Exception as e:
            print(f"❌ Error generating CI/CD pipeline: {e}")
            return 1

    def sync(self, args) -> int:
        """
        Synchronize CI/CD configuration.
        """
        try:
            source_path = Path(args.source)
            target_paths = [Path(p) for p in args.targets]

            # Determine sync strategy
            strategy = (
                SyncStrategy(args.strategy) if args.strategy else SyncStrategy.BACKUP_AND_OVERWRITE
            )

            # Sync projects
            results = self.synchronizer.sync_all_projects(source_path, target_paths, strategy)

            # Report results
            success_count = sum(1 for r in results if r.success)
            total_count = len(results)

            print(f"🔄 Synchronized {success_count}/{total_count} projects")

            for i, result in enumerate(results):
                target_path = target_paths[i]
                if result.success:
                    print(f"✅ {target_path.name}: {len(result.changes)} changes applied")
                else:
                    print(f"❌ {target_path.name}: {result.error_message}")

            return 0 if success_count == total_count else 1

        except Exception as e:
            print(f"❌ Error synchronizing CI/CD: {e}")
            return 1

    def update(self, args) -> int:
        """
        Update soft dependencies.
        """
        try:
            project_name = args.project
            dependency_types = args.types or ["workflows", "docker", "makefile", "config"]

            # Get dependencies
            dependencies = self.dependency_manager.get_dependencies(project_name)

            if not dependencies:
                print(f"ℹ️ No dependencies found for {project_name}")
                return 0

            print(f"🔄 Updating dependencies for {project_name}: {', '.join(dependencies)}")

            # Update dependencies
            source_path = Path.cwd() / project_name
            target_paths = [Path.cwd() / dep for dep in dependencies]

            results = self.synchronizer.update_soft_dependencies(
                source_path, target_paths, dependency_types,
            )

            # Report results
            success_count = sum(1 for r in results if r.success)
            total_count = len(results)

            print(f"✅ Updated {success_count}/{total_count} dependencies")

            for i, result in enumerate(results):
                dependency = dependencies[i]
                if result.success:
                    print(f"✅ {dependency}: {', '.join(result.changes)}")
                else:
                    print(f"❌ {dependency}: {result.error_message}")

            return 0 if success_count == total_count else 1

        except Exception as e:
            print(f"❌ Error updating dependencies: {e}")
            return 1

    def status(self, args) -> int:
        """
        Show CI/CD status.
        """
        try:
            project_path = Path(args.path)

            # Load configuration
            config = self.repository.load_config(project_path)
            if not config:
                print(f"❌ No CI/CD configuration found in {project_path}")
                return 1

            # Load pipeline
            pipeline = self.repository.load_pipeline(project_path)

            print(f"📊 CI/CD Status for {config.project_name}")
            print(f"Project Type: {config.project_type.value}")
            print(f"Python Versions: {', '.join(config.python_versions)}")
            print(f"OS Versions: {', '.join(config.os_versions)}")

            if pipeline:
                print(f"Generated: {pipeline.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"Files: {len(pipeline.list_files())}")
            else:
                print("Pipeline: Not generated")

            # Show sync status
            sync_status = self.sync_provider.get_sync_status(project_path)
            print(f"Last Sync: {sync_status.get('last_sync', 'Never')}")
            print(f"Has Changes: {sync_status.get('has_changes', False)}")
            print(f"Backups: {sync_status.get('backup_count', 0)}")

            return 0

        except Exception as e:
            print(f"❌ Error getting status: {e}")
            return 1

    def validate(self, args) -> int:
        """
        Validate CI/CD configuration.
        """
        try:
            project_path = Path(args.path)

            # Load configuration
            config = self.repository.load_config(project_path)
            if not config:
                print(f"❌ No CI/CD configuration found in {project_path}")
                return 1

            # Validate configuration
            errors = self.config_provider.validate_config(config)

            if errors:
                print("❌ Configuration validation failed:")
                for error in errors:
                    print(f"  - {error}")
                return 1
            print("✅ Configuration is valid")
            return 0

        except Exception as e:
            print(f"❌ Error validating configuration: {e}")
            return 1

    def _detect_project_type(self, path: str) -> ProjectType:
        """
        Detect project type from path.
        """
        path_obj = Path(path)

        if "pheno-sdk" in path_obj.name:
            return ProjectType.PHENO_SDK
        if "zen-mcp-server" in path_obj.name:
            return ProjectType.ZEN_MCP_SERVER
        if "atoms_mcp-old" in path_obj.name:
            return ProjectType.ATOMS_MCP_OLD
        if "morph" in path_obj.name:
            return ProjectType.MORPH
        if "router" in path_obj.name:
            return ProjectType.ROUTER
        return ProjectType.PHENO_SDK  # Default

    def _load_config_from_file(self, config_path: str) -> CICDConfig:
        """
        Load configuration from file.
        """
        with open(config_path) as f:
            data = json.load(f)
        return CICDConfig.from_dict(data)


def main():
    """
    Main CLI entry point.
    """
    parser = argparse.ArgumentParser(description="Pheno CI/CD Generator and Synchronizer")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Generate command
    generate_parser = subparsers.add_parser("generate", help="Generate CI/CD pipeline")
    generate_parser.add_argument("path", help="Project path")
    generate_parser.add_argument(
        "--project-type", choices=[pt.value for pt in ProjectType], help="Project type",
    )
    generate_parser.add_argument("--project-name", help="Project name")
    generate_parser.add_argument("--config", help="Configuration file path")

    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Synchronize CI/CD configuration")
    sync_parser.add_argument("source", help="Source project path")
    sync_parser.add_argument("targets", nargs="+", help="Target project paths")
    sync_parser.add_argument(
        "--strategy", choices=[s.value for s in SyncStrategy], help="Sync strategy",
    )

    # Update command
    update_parser = subparsers.add_parser("update", help="Update soft dependencies")
    update_parser.add_argument("project", help="Project name")
    update_parser.add_argument("--types", nargs="+", help="Dependency types to update")

    # Status command
    status_parser = subparsers.add_parser("status", help="Show CI/CD status")
    status_parser.add_argument("path", help="Project path")

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate CI/CD configuration")
    validate_parser.add_argument("path", help="Project path")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    cli = CICDCLI()

    if args.command == "generate":
        return cli.generate(args)
    if args.command == "sync":
        return cli.sync(args)
    if args.command == "update":
        return cli.update(args)
    if args.command == "status":
        return cli.status(args)
    if args.command == "validate":
        return cli.validate(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
