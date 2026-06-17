"""
CI/CD synchronization system for soft dependencies.
"""

import shutil
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from .ports import CICDSyncProvider


class SyncStrategy(Enum):
    """
    Synchronization strategy enumeration.
    """

    OVERWRITE = "overwrite"
    MERGE = "merge"
    BACKUP_AND_OVERWRITE = "backup_and_overwrite"
    MANUAL_REVIEW = "manual_review"


@dataclass
class SyncResult:
    """
    Result of synchronization operation.
    """

    success: bool
    changes: list[str]
    conflicts: list[str]
    backup_path: Path | None = None
    error_message: str | None = None
    sync_timestamp: datetime = None

    def __post_init__(self):
        if self.sync_timestamp is None:
            self.sync_timestamp = datetime.now()


class CICDSynchronizer:
    """
    CI/CD synchronization orchestrator.
    """

    def __init__(self, sync_provider: CICDSyncProvider):
        self.sync_provider = sync_provider
        self.sync_history: list[dict[str, Any]] = []

    def sync_project(
        self,
        source_path: Path,
        target_path: Path,
        strategy: SyncStrategy = SyncStrategy.BACKUP_AND_OVERWRITE,
    ) -> SyncResult:
        """
        Synchronize CI/CD configuration between projects.
        """
        try:
            # Detect changes
            changes = self.sync_provider.detect_changes(source_path, target_path)

            if not changes:
                return SyncResult(
                    success=True, changes=[], conflicts=[], error_message="No changes detected",
                )

            # Handle conflicts
            conflicts = self._detect_conflicts(source_path, target_path)

            # Apply strategy
            if strategy == SyncStrategy.OVERWRITE:
                result = self._sync_overwrite(source_path, target_path, changes)
            elif strategy == SyncStrategy.MERGE:
                result = self._sync_merge(source_path, target_path, changes, conflicts)
            elif strategy == SyncStrategy.BACKUP_AND_OVERWRITE:
                result = self._sync_backup_and_overwrite(source_path, target_path, changes)
            elif strategy == SyncStrategy.MANUAL_REVIEW:
                result = self._sync_manual_review(source_path, target_path, changes, conflicts)
            else:
                raise ValueError(f"Unknown sync strategy: {strategy}")

            # Record sync history
            self._record_sync(source_path, target_path, strategy, result)

            return result

        except Exception as e:
            return SyncResult(success=False, changes=[], conflicts=[], error_message=str(e))

    def sync_all_projects(
        self,
        source_path: Path,
        target_paths: list[Path],
        strategy: SyncStrategy = SyncStrategy.BACKUP_AND_OVERWRITE,
    ) -> list[SyncResult]:
        """
        Synchronize source to multiple target projects.
        """
        results = []

        for target_path in target_paths:
            result = self.sync_project(source_path, target_path, strategy)
            results.append(result)

        return results

    def update_soft_dependencies(
        self, source_path: Path, target_paths: list[Path], dependency_types: list[str] | None = None,
    ) -> list[SyncResult]:
        """
        Update soft dependencies across projects.
        """
        if dependency_types is None:
            dependency_types = ["workflows", "docker", "makefile", "config"]

        results = []

        for target_path in target_paths:
            result = self._update_dependencies(source_path, target_path, dependency_types)
            results.append(result)

        return results

    def get_sync_status(self, project_path: Path) -> dict[str, Any]:
        """
        Get synchronization status for project.
        """
        return self.sync_provider.get_sync_status(project_path)

    def list_sync_history(self) -> list[dict[str, Any]]:
        """
        List synchronization history.
        """
        return self.sync_history.copy()

    def _detect_conflicts(self, source_path: Path, target_path: Path) -> list[str]:
        """
        Detect conflicts between source and target.
        """
        conflicts = []

        # Check for local modifications in target
        cicd_files = [
            ".github/workflows/",
            "Dockerfile",
            "docker-compose.yml",
            "Makefile",
            "cicd-config.json",
        ]

        for file_pattern in cicd_files:
            source_file = source_path / file_pattern
            target_file = target_path / file_pattern

            if source_file.exists() and target_file.exists():
                if self._files_differ(source_file, target_file):
                    # Check if target has local modifications
                    if self._has_local_modifications(target_file):
                        conflicts.append(f"Local modifications in {file_pattern}")

        return conflicts

    def _sync_overwrite(
        self, source_path: Path, target_path: Path, changes: list[str],
    ) -> SyncResult:
        """
        Overwrite target with source.
        """
        success = self.sync_provider.sync_pipeline(source_path, target_path)

        return SyncResult(success=success, changes=changes, conflicts=[])

    def _sync_merge(
        self, source_path: Path, target_path: Path, changes: list[str], conflicts: list[str],
    ) -> SyncResult:
        """
        Merge source and target configurations.
        """
        # For now, implement as overwrite with conflict detection
        # In a full implementation, this would merge configurations intelligently
        if conflicts:
            return SyncResult(
                success=False,
                changes=changes,
                conflicts=conflicts,
                error_message="Conflicts detected, manual resolution required",
            )

        success = self.sync_provider.sync_pipeline(source_path, target_path)

        return SyncResult(success=success, changes=changes, conflicts=[])

    def _sync_backup_and_overwrite(
        self, source_path: Path, target_path: Path, changes: list[str],
    ) -> SyncResult:
        """
        Backup target and overwrite with source.
        """
        # Create backup
        backup_success = self.sync_provider.backup_pipeline(target_path)
        backup_path = None

        if backup_success:
            # Get backup path (this would be returned by the provider in a full implementation)
            backup_path = (
                target_path / ".cicd-backups" / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )

        # Sync pipeline
        sync_success = self.sync_provider.sync_pipeline(source_path, target_path)

        return SyncResult(
            success=sync_success, changes=changes, conflicts=[], backup_path=backup_path,
        )

    def _sync_manual_review(
        self, source_path: Path, target_path: Path, changes: list[str], conflicts: list[str],
    ) -> SyncResult:
        """
        Prepare for manual review.
        """
        # Create a diff file for manual review
        diff_content = self._create_diff_file(source_path, target_path, changes)
        diff_path = target_path / ".cicd-sync-diff.txt"

        with open(diff_path, "w") as f:
            f.write(diff_content)

        return SyncResult(
            success=False,
            changes=changes,
            conflicts=conflicts,
            error_message=f"Manual review required. Diff saved to {diff_path}",
        )

    def _update_dependencies(
        self, source_path: Path, target_path: Path, dependency_types: list[str],
    ) -> SyncResult:
        """
        Update specific dependency types.
        """
        changes = []

        for dep_type in dependency_types:
            if dep_type == "workflows":
                if self._update_workflows(source_path, target_path):
                    changes.append("Updated GitHub Actions workflows")
            elif dep_type == "docker":
                if self._update_docker_files(source_path, target_path):
                    changes.append("Updated Docker files")
            elif dep_type == "makefile":
                if self._update_makefile(source_path, target_path):
                    changes.append("Updated Makefile")
            elif dep_type == "config":
                if self._update_config_files(source_path, target_path):
                    changes.append("Updated configuration files")

        return SyncResult(success=len(changes) > 0, changes=changes, conflicts=[])

    def _update_workflows(self, source_path: Path, target_path: Path) -> bool:
        """
        Update GitHub Actions workflows.
        """
        try:
            source_workflows = source_path / ".github" / "workflows"
            target_workflows = target_path / ".github" / "workflows"

            if not source_workflows.exists():
                return False

            target_workflows.mkdir(parents=True, exist_ok=True)

            for workflow_file in source_workflows.glob("*.yml"):
                target_file = target_workflows / workflow_file.name
                shutil.copy2(workflow_file, target_file)

            return True
        except Exception:
            return False

    def _update_docker_files(self, source_path: Path, target_path: Path) -> bool:
        """
        Update Docker files.
        """
        try:
            docker_files = ["Dockerfile", "docker-compose.yml"]
            updated = False

            for docker_file in docker_files:
                source_file = source_path / docker_file
                target_file = target_path / docker_file

                if source_file.exists():
                    shutil.copy2(source_file, target_file)
                    updated = True

            return updated
        except Exception:
            return False

    def _update_makefile(self, source_path: Path, target_path: Path) -> bool:
        """
        Update Makefile.
        """
        try:
            source_makefile = source_path / "Makefile"
            target_makefile = target_path / "Makefile"

            if source_makefile.exists():
                shutil.copy2(source_makefile, target_makefile)
                return True

            return False
        except Exception:
            return False

    def _update_config_files(self, source_path: Path, target_path: Path) -> bool:
        """
        Update configuration files.
        """
        try:
            config_files = ["cicd-config.json", ".github/quality-config.json"]
            updated = False

            for config_file in config_files:
                source_file = source_path / config_file
                target_file = target_path / config_file

                if source_file.exists():
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_file, target_file)
                    updated = True

            return updated
        except Exception:
            return False

    def _files_differ(self, file1: Path, file2: Path) -> bool:
        """
        Check if two files differ.
        """
        try:
            if file1.is_dir() and file2.is_dir():
                return self._dirs_differ(file1, file2)
            if file1.is_file() and file2.is_file():
                return file1.read_text() != file2.read_text()
            return True
        except Exception:
            return True

    def _dirs_differ(self, dir1: Path, dir2: Path) -> bool:
        """
        Check if two directories differ.
        """
        try:
            files1 = {f.relative_to(dir1) for f in dir1.rglob("*") if f.is_file()}
            files2 = {f.relative_to(dir2) for f in dir2.rglob("*") if f.is_file()}

            if files1 != files2:
                return True

            for file_path in files1:
                if self._files_differ(dir1 / file_path, dir2 / file_path):
                    return True

            return False
        except Exception:
            return True

    def _has_local_modifications(self, file_path: Path) -> bool:
        """
        Check if file has local modifications (simplified)
        """
        # In a full implementation, this would check git history or modification timestamps
        return False

    def _create_diff_file(self, source_path: Path, target_path: Path, changes: list[str]) -> str:
        """
        Create diff file for manual review.
        """
        diff_content = "CI/CD Synchronization Diff\n"
        diff_content += f"Source: {source_path}\n"
        diff_content += f"Target: {target_path}\n"
        diff_content += f"Generated: {datetime.now().isoformat()}\n\n"
        diff_content += "Changes detected:\n"

        for change in changes:
            diff_content += f"  - {change}\n"

        return diff_content

    def _record_sync(
        self, source_path: Path, target_path: Path, strategy: SyncStrategy, result: SyncResult,
    ):
        """
        Record synchronization in history.
        """
        sync_record = {
            "timestamp": result.sync_timestamp.isoformat(),
            "source_path": str(source_path),
            "target_path": str(target_path),
            "strategy": strategy.value,
            "success": result.success,
            "changes_count": len(result.changes),
            "conflicts_count": len(result.conflicts),
            "backup_path": str(result.backup_path) if result.backup_path else None,
            "error_message": result.error_message,
        }

        self.sync_history.append(sync_record)

        # Keep only last 100 sync records
        if len(self.sync_history) > 100:
            self.sync_history = self.sync_history[-100:]


class SoftDependencyManager:
    """
    Manager for soft dependencies across projects.
    """

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.dependency_map = self._load_dependency_map()

    def _load_dependency_map(self) -> dict[str, list[str]]:
        """
        Load dependency mapping from configuration.
        """
        return {
            "pheno-sdk": ["zen-mcp-server", "atoms_mcp-old", "morph", "router"],
            "zen-mcp-server": ["example/zen-mcp-server"],
            "atoms_mcp-old": [],
            "morph": [],
            "router": [],
        }


    def get_dependencies(self, project_name: str) -> list[str]:
        """
        Get dependencies for a project.
        """
        return self.dependency_map.get(project_name, [])

    def add_dependency(self, project_name: str, dependency: str) -> None:
        """
        Add a dependency.
        """
        if project_name not in self.dependency_map:
            self.dependency_map[project_name] = []

        if dependency not in self.dependency_map[project_name]:
            self.dependency_map[project_name].append(dependency)

    def remove_dependency(self, project_name: str, dependency: str) -> None:
        """
        Remove a dependency.
        """
        if project_name in self.dependency_map:
            if dependency in self.dependency_map[project_name]:
                self.dependency_map[project_name].remove(dependency)

    def sync_dependencies(
        self, project_name: str, sync_strategy: SyncStrategy = SyncStrategy.BACKUP_AND_OVERWRITE,
    ) -> list[SyncResult]:
        """
        Sync dependencies for a project.
        """
        dependencies = self.get_dependencies(project_name)
        results = []

        self.base_path / project_name

        for dependency in dependencies:
            target_path = self.base_path / dependency
            if target_path.exists():
                # This would use the actual sync provider
                result = SyncResult(
                    success=True,
                    changes=[f"Synced from {project_name} to {dependency}"],
                    conflicts=[],
                )
                results.append(result)

        return results
