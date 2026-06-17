"""
Dataclasses and simple types for ServiceManager (split from monolith).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path


@dataclass
class ServiceConfig:
    name: str
    command: list[str]
    cwd: Path | None = None
    env: dict[str, str] | None = None
    port: int | None = None
    preferred_port: int | None = None
    enable_tunnel: bool = False
    tunnel_domain: str | None = None
    watch_paths: list[Path] | None = None
    watch_patterns: list[str] | None = None
    restart_on_failure: bool = True
    max_restart_attempts: int = 3
    restart_delay: float = 2.0
    health_check_url: str | None = None
    health_check_interval: float = 10.0
    tunnel_ready_timeout: int = 45
    tunnel_health_endpoint: str = "/healthz"
    enable_fallback: bool = True
    fallback_page: str = "loading"
    fallback_refresh_interval: int = 5
    fallback_message: str | None = None
    path_prefix: str = "/"
    # Optional: map specific log needles to lifecycle stages
    log_stage_patterns: list[tuple[str, str, str]] | None = None
    # Phase 1 metadata fields
    project: str | None = None
    service_type: str | None = None
    scope: str | None = None


@dataclass
class ResourceConfig:
    name: str
    host: str = "localhost"
    port: int = 5432
    check_interval: float = 10.0
    required: bool = True


@dataclass
class ServiceStatus:
    name: str
    state: str  # "stopped", "starting", "running", "error", "reloading"
    pid: int | None = None
    port: int | None = None
    tunnel_url: str | None = None
    started_at: datetime | None = None
    restart_count: int = 0
    last_health_check: datetime | None = None
    health_status: str = "unknown"
    error_message: str | None = None
    logs: list[dict[str, Any]] | None = None
    last_output: str | None = None

    def __post_init__(self) -> None:
        if self.logs is None:
            self.logs = []


@dataclass
class ResourceStatus:
    name: str
    available: bool
    last_check: datetime | None = None
    error_message: str | None = None
