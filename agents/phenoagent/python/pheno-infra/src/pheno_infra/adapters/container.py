"""
Infrastructure adapter container helpers built on the unified adapter registry.
"""

from __future__ import annotations

from typing import Any

from pheno.core.registry.adapters import (
    AdapterRegistry,
    AdapterType,
    get_adapter_registry,
)


def get_container() -> AdapterRegistry:
    """
    Return the shared infrastructure container (adapter registry).
    """
    return get_adapter_registry()


def register_default_adapters(container: AdapterRegistry | None = None) -> AdapterRegistry:
    """
    Register default infrastructure adapters (idempotent).
    """
    container = container or get_container()

    # Database adapters -------------------------------------------------
    try:
        from pheno.plugins.supabase import SupabaseAdapter

        if "supabase" not in container.list_adapters(AdapterType.DATABASE):
            container.register_adapter(
                AdapterType.DATABASE,
                "supabase",
                SupabaseAdapter,
                factory=lambda _registry, **kwargs: SupabaseAdapter(**kwargs),
                singleton=True,
                health_check=lambda adapter: True,
            )
    except Exception as exc:  # pragma: no cover - optional dependency
        from logging import getLogger

        getLogger(__name__).debug("Supabase adapter unavailable: %s", exc)

    return container


async def run_health_checks(container: AdapterRegistry | None = None) -> dict[str, dict[str, Any]]:
    """
    Execute health checks for registered infrastructure adapters.
    """
    container = container or get_container()
    return await container.run_health_checks()


__all__ = [
    "get_container",
    "register_default_adapters",
    "run_health_checks",
]
