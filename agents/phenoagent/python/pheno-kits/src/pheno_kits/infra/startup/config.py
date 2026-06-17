"""
Startup configuration structures for the unified startup framework.

The :class:`~pheno.kits.infra.startup.StartupConfig` dataclass captures the
minimal information a project must provide so that :class:`UnifiedStartup`
can orchestrate infrastructure concerns on its behalf. Projects define the
resources they need, while the SDK takes care of provisioning, discovery,
and lifecycle management.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from .framework import UnifiedStartup

if False:  # pragma: nocover - avoid circular import at runtime
    pass


class StartupHook(Protocol):
    """Protocol describing lifecycle hooks accepted by :class:`StartupConfig`.

    Hooks receive the active :class:`UnifiedStartup` instance and may be
    synchronous or asynchronous callables. The protocol is intentionally
    lightweight so that projects can provide plain functions, lambdas, or
    bound methods without additional boilerplate.
    """

    def __call__(self, startup: UnifiedStartup) -> Awaitable[None] | None:
        ...


@dataclass(slots=True)
class StartupConfig:
    """Configuration container for :class:`UnifiedStartup`.

    Parameters
    ----------
    project_name:
        Canonical project slug used for registry keys, tunnel identifiers,
        and log routing. The value is sanitized before being persisted.
    preferred_port:
        Preferred local port for the main application service. The startup
        framework attempts to honour this preference while still resolving
        port conflicts automatically.
    tunnel_subdomain:
        Desired subdomain for public tunnels (e.g. ``"ai"`` to produce
        ``ai.example.com``). The value is optional but encouraged when
        tunnels are enabled.
    resources:
        Mapping of resource names to configuration dictionaries. Each
        dictionary should include the keys required by the corresponding
        resource adapter (e.g. ``type``, ``image``, ``ports`` for Docker
        resources) plus metadata such as ``mode`` and ``scope``.
    domain:
        Base domain used for tunnel routing. Defaults to ``kooshapari.com``.
    enable_tunnel:
        Whether to create an ingress tunnel for the primary service.
    enable_fallback:
        Whether to start the shared fallback server. The default is ``True``
        because it provides a friendlier user experience during boot.
    enable_proxy:
        Whether to start the smart proxy. Disabled by default since many
        projects do not require proxy routing.
    on_startup / on_shutdown:
        Optional lifecycle hooks invoked after successful startup and before
        teardown respectively. Hooks may be synchronous or asynchronous and
        are awaited when necessary.
    """

    project_name: str
    preferred_port: int
    tunnel_subdomain: str
    resources: dict[str, dict[str, Any]] = field(default_factory=dict)
    domain: str = "kooshapari.com"
    enable_tunnel: bool = True
    enable_fallback: bool = True
    enable_proxy: bool = False
    on_startup: StartupHook | None = None
    on_shutdown: StartupHook | None = None

