"""
Migration engine for database schema management.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from .migration import Migration, MigrationStatus

if TYPE_CHECKING:
    from ..adapters.base import DatabaseAdapter


class MigrationEngine:
    """
    Database migration engine with version tracking.
    """

    MIGRATIONS_TABLE = "_migrations"

    def __init__(self, adapter: DatabaseAdapter):
        """Initialize migration engine.

        Args:
            adapter: Database adapter
        """
        self.adapter = adapter
        self._migrations: list[Migration] = []

    async def init(self):
        """
        Initialize migrations table.
        """
        # Create migrations tracking table
        sql = f"""
        CREATE TABLE IF NOT EXISTS {self.MIGRATIONS_TABLE} (
            version VARCHAR(255) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            applied_at TIMESTAMP NOT NULL,
            checksum VARCHAR(64) NOT NULL,
            status VARCHAR(50) NOT NULL
        )
        """
        await self.adapter.execute(sql)

    def register(
        self, version: str, name: str, up: callable, down: callable | None = None,
    ) -> Migration:
        """Register a migration.

        Args:
            version: Version string (e.g., "001", "20240101_120000")
            name: Migration name
            up: Upgrade function
            down: Downgrade function (optional)

        Returns:
            Migration instance
        """
        migration = Migration(
            version=version,
            name=name,
            up=up,
            down=down,
            checksum=self._calculate_checksum(version, name),
        )

        self._migrations.append(migration)
        return migration

    def load_from_directory(self, directory: str):
        """Load migrations from a directory.

        Args:
            directory: Path to migrations directory
        """
        import importlib.util

        migrations_dir = Path(directory)
        if not migrations_dir.exists():
            raise FileNotFoundError(f"Migrations directory not found: {directory}")

        # Find all migration files
        for file_path in sorted(migrations_dir.glob("*.py")):
            if file_path.name.startswith("_"):
                continue

            # Load module
            spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Get migration functions
                if hasattr(module, "up"):
                    version = file_path.stem.split("_")[0]
                    name = "_".join(file_path.stem.split("_")[1:])

                    self.register(
                        version=version, name=name, up=module.up, down=getattr(module, "down", None),
                    )

    async def get_applied_migrations(self) -> list[str]:
        """Get list of applied migration versions.

        Returns:
            List of applied migration versions
        """
        try:
            rows = await self.adapter.execute(
                f"SELECT version FROM {self.MIGRATIONS_TABLE} WHERE status = $1",
                [MigrationStatus.APPLIED.value],
            )
            return [row["version"] for row in rows]
        except Exception:
            # Table doesn't exist yet
            return []

    async def get_pending_migrations(self) -> list[Migration]:
        """Get pending migrations.

        Returns:
            List of pending migrations
        """
        applied = await self.get_applied_migrations()
        return [m for m in self._migrations if m.version not in applied]

    async def migrate(self, target: str | None = None) -> list[Migration]:
        """Run pending migrations up to target version.

        Args:
            target: Target version (runs all if None)

        Returns:
            List of applied migrations
        """
        await self.init()

        pending = await self.get_pending_migrations()
        if target:
            pending = [m for m in pending if m.version <= target]

        applied = []

        for migration in pending:
            try:
                # Run migration
                await migration.up(self.adapter)

                # Record in migrations table
                await self.adapter.insert(
                    self.MIGRATIONS_TABLE,
                    {
                        "version": migration.version,
                        "name": migration.name,
                        "applied_at": datetime.utcnow(),
                        "checksum": migration.checksum,
                        "status": MigrationStatus.APPLIED.value,
                    },
                )

                migration.status = MigrationStatus.APPLIED
                migration.applied_at = datetime.utcnow()
                applied.append(migration)

                print(f"✅ Applied migration: {migration.version}_{migration.name}")

            except Exception as e:
                migration.status = MigrationStatus.FAILED
                print(f"❌ Failed migration: {migration.version}_{migration.name}: {e}")
                raise

        return applied

    async def rollback(self, steps: int = 1) -> list[Migration]:
        """Rollback migrations.

        Args:
            steps: Number of migrations to rollback

        Returns:
            List of rolled back migrations
        """
        # Get applied migrations in reverse order
        applied = await self.get_applied_migrations()
        to_rollback = applied[-steps:]

        rolled_back = []

        for version in reversed(to_rollback):
            # Find migration
            migration = next((m for m in self._migrations if m.version == version), None)

            if not migration or not migration.down:
                print(f"⚠️  Cannot rollback {version}: No down migration")
                continue

            try:
                # Run down migration
                await migration.down(self.adapter)

                # Update status
                await self.adapter.execute(
                    f"UPDATE {self.MIGRATIONS_TABLE} SET status = $1 WHERE version = $2",
                    [MigrationStatus.ROLLED_BACK.value, version],
                )

                migration.status = MigrationStatus.ROLLED_BACK
                rolled_back.append(migration)

                print(f"↩️  Rolled back migration: {migration.version}_{migration.name}")

            except Exception as e:
                print(f"❌ Failed rollback: {migration.version}_{migration.name}: {e}")
                raise

        return rolled_back

    async def status(self) -> list[dict]:
        """Get migration status.

        Returns:
            List of migration statuses
        """
        applied = await self.get_applied_migrations()

        statuses = []
        for migration in self._migrations:
            statuses.append(
                {
                    "version": migration.version,
                    "name": migration.name,
                    "status": "applied" if migration.version in applied else "pending",
                    "applied_at": migration.applied_at,
                    "has_rollback": migration.down is not None,
                },
            )

        return statuses

    def _calculate_checksum(self, version: str, name: str) -> str:
        """Calculate migration checksum.

        Args:
            version: Migration version
            name: Migration name

        Returns:
            Checksum hash
        """
        content = f"{version}_{name}"
        return hashlib.sha256(content.encode()).hexdigest()
