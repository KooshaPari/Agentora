"""
Tunneling core types: enums, exceptions, protocol, and dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable
from urllib.parse import urlparse, urlunparse


class TunnelType(Enum):
    QUICK = "quick"
    PERSISTENT = "persistent"


class TunnelStatus(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"
    UNKNOWN = "unknown"


class CloudflareTunnelError(Exception):
    pass


class TunnelNotFoundError(CloudflareTunnelError):
    pass


class TunnelConfigurationError(CloudflareTunnelError):
    pass


class TunnelOperationError(CloudflareTunnelError):
    pass


@runtime_checkable
class TunnelProtocol(Protocol):
    def start(self) -> bool: ...
    def stop(self) -> bool: ...
    def get_status(self) -> TunnelStatus: ...


@dataclass
class TunnelConfig:
    name: str
    local_url: str
    tunnel_type: TunnelType = TunnelType.QUICK

    hostname: str | None = None
    credentials_file: str | None = None
    config_file: str | None = None
    log_level: str = "info"
    protocol: str = "auto"

    ingress_rules: list[dict[str, Any]] = field(default_factory=list)
    warp_routing: bool = False

    tunnel_token: str | None = None
    cert_path: str | None = None

    no_autoupdate: bool = False
    retries: int = 5
    grace_period: float = 5.0

    def __post_init__(self) -> None:
        self._validate_config()

    def _validate_config(self) -> None:
        if not self.name or not self.name.strip():
            raise TunnelConfigurationError("Tunnel name cannot be empty")
        if not self.local_url or not self.local_url.strip():
            raise TunnelConfigurationError("Local URL cannot be empty")

        parsed_url = urlparse(self.local_url)
        if parsed_url.hostname in {"localhost", "127.0.0.1"}:
            host = "0.0.0.0"
            userinfo = ""
            if parsed_url.username:
                userinfo = parsed_url.username
                if parsed_url.password:
                    userinfo += f":{parsed_url.password}"
                userinfo += "@"
            port = f":{parsed_url.port}" if parsed_url.port else ""
            netloc = f"{userinfo}{host}{port}"
            parsed_url = parsed_url._replace(netloc=netloc)
            self.local_url = urlunparse(parsed_url)

        if self.tunnel_type == TunnelType.PERSISTENT and not self.hostname:
            raise TunnelConfigurationError("Hostname is required for persistent tunnels")
        if self.retries < 0:
            raise TunnelConfigurationError("Retries must be non-negative")
        if self.grace_period < 0:
            raise TunnelConfigurationError("Grace period must be non-negative")


@dataclass
class TunnelInfo:
    name: str
    status: TunnelStatus
    url: str | None = None
    process_id: int | None = None
    config: TunnelConfig | None = None
    created_at: str | None = None
    last_updated: str | None = None
    error_message: str | None = None
