"""Upstream registry and tenancy tracking for the proxy server."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from copy import deepcopy
from typing import Any

from ..config import UpstreamConfig

RegisterHook = Callable[[str, UpstreamConfig], None]
UnregisterHook = Callable[[str], None]


class UpstreamRegistry:
    """
    Maintain upstream configurations and tenant associations.
    """

    def __init__(
        self,
        on_register: RegisterHook | None = None,
        on_unregister: UnregisterHook | None = None,
    ):
        self._upstreams: dict[str, UpstreamConfig] = {}
        self._tenants: dict[str, str] = {}
        self._health_states: dict[str, dict[str, Any]] = {}
        self._on_register = on_register
        self._on_unregister = on_unregister

    def add_upstream(
        self,
        path_prefix: str,
        *,
        host: str = "localhost",
        port: int,
        service_name: str | None = None,
        tenant: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> UpstreamConfig:
        """
        Register a new upstream and return its configuration.
        """
        service = service_name or self._service_name(path_prefix)
        config = UpstreamConfig(
            host=host,
            port=port,
            path_prefix=path_prefix,
            service_name=service,
            tenant=tenant,
            metadata=metadata,
        )
        self._upstreams[path_prefix] = config
        if tenant:
            self._tenants[path_prefix] = tenant
        elif path_prefix in self._tenants:
            self._tenants.pop(path_prefix)

        config.last_state_change = time.time()
        self._health_states[path_prefix] = self._build_health_state(path_prefix, config)

        if self._on_register:
            self._on_register(service, config)

        return config

    def remove_upstream(self, path_prefix: str) -> bool:
        """
        Remove an upstream by prefix; returns True if removed.
        """
        config = self._upstreams.pop(path_prefix, None)
        self._tenants.pop(path_prefix, None)
        self._health_states.pop(path_prefix, None)
        if not config:
            return False

        if self._on_unregister:
            self._on_unregister(self._service_name(path_prefix))
        return True

    def list_upstreams(self, tenant_filter: str | None = None) -> list[dict]:
        """
        Return a list of upstream metadata for admin APIs.
        """
        items: list[dict] = []
        for prefix, cfg in self._upstreams.items():
            tenant = self._tenants.get(prefix)
            if tenant_filter and tenant != tenant_filter:
                continue
            items.append(
                {
                    "path_prefix": prefix,
                    "host": cfg.host,
                    "port": cfg.port,
                    "tenant": tenant,
                    "service": cfg.service_name or self._service_name(prefix),
                    "healthy": cfg.is_healthy,
                    "last_checked": cfg.last_health_check,
                    "last_changed": getattr(cfg, "last_state_change", 0.0),
                },
            )
        return items

    def deregister_tenant(self, tenant: str | None, prefixes: Iterable[str]) -> list[str]:
        """
        Remove upstreams associated with a tenant or explicit prefixes.
        """
        removed: list[str] = []
        if tenant:
            to_remove = [prefix for prefix, value in self._tenants.items() if value == tenant]
        else:
            to_remove = list(prefixes)

        for prefix in to_remove:
            if self.remove_upstream(prefix):
                removed.append(prefix)

        return removed

    def find_upstream(self, path: str) -> UpstreamConfig | None:
        """
        Locate the best matching upstream for a request path.
        """
        for prefix, cfg in self._sorted_upstreams():
            if path.startswith(prefix) or prefix == "/":
                return cfg
        return None

    def iter_upstreams(self) -> Iterable[tuple[str, UpstreamConfig]]:
        """
        Iterate through registered upstreams.
        """
        return list(self._upstreams.items())

    def _sorted_upstreams(self) -> list[tuple[str, UpstreamConfig]]:
        return sorted(self._upstreams.items(), key=lambda item: len(item[0]), reverse=True)

    @staticmethod
    def _service_name(path_prefix: str) -> str:
        return path_prefix.strip("/") or "service"

    def update_health_state(
        self,
        path_prefix: str,
        healthy: bool,
        *,
        checked_at: float | None = None,
    ) -> dict[str, Any]:
        """Update tracked health state for an upstream."""

        config = self._upstreams.get(path_prefix)
        if not config:
            raise KeyError(f"Unknown upstream '{path_prefix}'")

        previous = config.is_healthy
        now = checked_at if checked_at is not None else time.time()
        config.last_health_check = now
        config.is_healthy = healthy
        if healthy != previous:
            config.last_state_change = now

        state = self._build_health_state(path_prefix, config)
        self._health_states[path_prefix] = state

        return {"state": state, "changed": healthy != previous, "previous": previous}

    def get_health_state(self, path_prefix: str) -> dict[str, Any] | None:
        """Return a copy of the tracked health state for an upstream."""

        state = self._health_states.get(path_prefix)
        return deepcopy(state) if state else None

    def snapshot(self) -> dict[str, Any]:
        """Return a serialisable snapshot of current upstream health."""

        collected_at = time.time()
        upstreams = [deepcopy(state) for state in self._health_states.values()]

        tenants: dict[str, dict[str, Any]] = {}
        for state in upstreams:
            tenant = state.get("tenant") or "default"
            tenant_entry = tenants.setdefault(
                tenant,
                {
                    "tenant": tenant,
                    "project": tenant,
                    "services": [],
                },
            )
            tenant_entry["services"].append(state)

        return {
            "collected_at": collected_at,
            "upstreams": upstreams,
            "tenants": tenants,
        }

    def _build_health_state(self, path_prefix: str, config: UpstreamConfig) -> dict[str, Any]:
        tenant = config.tenant or self._tenants.get(path_prefix)
        service = config.service_name or self._service_name(path_prefix)
        metadata = deepcopy(config.metadata)
        metadata.setdefault("path_prefix", path_prefix)
        metadata.setdefault("host", config.host)
        metadata.setdefault("port", config.port)

        return {
            "tenant": tenant,
            "project": tenant,
            "service": service,
            "path_prefix": path_prefix,
            "host": config.host,
            "port": config.port,
            "healthy": config.is_healthy,
            "last_checked": config.last_health_check,
            "last_changed": getattr(config, "last_state_change", 0.0),
            "metadata": metadata,
        }


__all__ = ["UpstreamRegistry"]
