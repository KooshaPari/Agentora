"""
Migration data structures.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime


class MigrationStatus(StrEnum):
    """
    Migration status.
    """

    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class Migration:
    """
    Database migration.
    """

    version: str
    name: str
    up: Callable
    down: Callable | None = None
    applied_at: datetime | None = None
    status: MigrationStatus = MigrationStatus.PENDING
    checksum: str | None = None

    def get_id(self) -> str:
        """Get migration ID.

        Returns:
            Migration ID (version_name)
        """
        return f"{self.version}_{self.name}"
