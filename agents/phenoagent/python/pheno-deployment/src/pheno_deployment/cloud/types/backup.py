"""
Backup and migration types.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass
class BackupConfig:
    """
    Backup configuration including retention and scheduling.
    """

    enabled: bool
    retention_days: int
    point_in_time_recovery: bool
    schedule: str | None = None
    backup_window: str | None = None


@dataclass
class Backup:
    """
    Metadata describing a specific backup artifact.
    """

    id: str
    resource_id: str
    type: str
    status: str
    size_bytes: int
    started_at: datetime
    completed_at: datetime | None = None


@dataclass
class Migration:
    """
    Metadata describing a database migration artifact.
    """

    id: str
    name: str
    status: str
    sql: str | None = None
    script_path: str | None = None
    checksum: str | None = None
    applied_at: datetime | None = None


__all__ = ["Backup", "BackupConfig", "Migration"]
