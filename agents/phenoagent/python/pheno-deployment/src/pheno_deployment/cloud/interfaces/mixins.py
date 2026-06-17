"""
Optional protocol mixins for cloud providers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ..types import (
        AlertConfig,
        Backup,
        BackupConfig,
        HealthCheckStatus,
        LogOptions,
        LogStream,
        Metric,
        MetricOptions,
        ScaleConfig,
        TimeRange,
    )


class Scalable(Protocol):
    async def set_scale(self, resource_id: str, config: ScaleConfig) -> None: ...

    async def get_scale_config(self, resource_id: str) -> ScaleConfig: ...

    async def auto_scale(self, resource_id: str, enabled: bool) -> None: ...


class Loggable(Protocol):
    async def stream_logs(self, resource_id: str, opts: LogOptions) -> LogStream: ...

    async def set_log_level(self, resource_id: str, level: str) -> None: ...

    async def get_log_retention(self, resource_id: str) -> int: ...


class Executable(Protocol):
    async def exec(self, resource_id: str, command: str) -> str: ...

    async def run_command(self, resource_id: str, command: str) -> LogStream: ...

    async def get_shell(self, resource_id: str, instance_id: str) -> None: ...


class Backupable(Protocol):
    async def create_backup(self, resource_id: str, config: BackupConfig) -> Backup: ...

    async def restore_backup(self, resource_id: str, backup_id: str) -> None: ...

    async def list_backups(self, resource_id: str) -> list[Backup]: ...

    async def delete_backup(self, backup_id: str) -> None: ...

    async def get_backup_config(self, resource_id: str) -> BackupConfig: ...

    async def set_backup_config(self, resource_id: str, config: BackupConfig) -> None: ...


class Monitorable(Protocol):
    async def set_alert(self, resource_id: str, alert: AlertConfig) -> None: ...

    async def list_alerts(self, resource_id: str) -> list[AlertConfig]: ...

    async def delete_alert(self, alert_id: str) -> None: ...

    async def get_health_check(self, resource_id: str) -> HealthCheckStatus: ...

    async def get_metrics(self, resource_id: str, opts: MetricOptions) -> list[Metric]: ...

    async def stream_metrics(self, resource_id: str, time_range: TimeRange) -> LogStream: ...


__all__ = ["Backupable", "Executable", "Loggable", "Monitorable", "Scalable"]
