"""
Factory helpers for Go-based services.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pheno.config import load_env_cascade
from pheno.infra.service_manager import ServiceConfig

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path


@dataclass
class GoServiceOptions:
    """
    Configuration options for building a Go service.
    """

    name: str
    project_root: Path
    module_dir: Path
    port: int
    command: list[str] | None = None
    env_files: Iterable[Path] = field(default_factory=list)
    extra_env: dict[str, str] | None = None
    go_cache_dir: Path | None = None
    go_mod_cache_dir: Path | None = None
    set_go_defaults: bool = True
    path_prefix: str = "/"
    health_check_url: str | None = None
    enable_tunnel: bool = True
    tunnel_domain: str | None = None
    restart_on_failure: bool = True


def _ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_go_service(
    *,
    options: GoServiceOptions,
) -> ServiceConfig:
    """
    Construct a ``ServiceConfig`` for a Go binary or module.
    """
    module_dir = options.module_dir
    module_dir.mkdir(parents=True, exist_ok=True)

    command = options.command or ["go", "run", "."]

    cache_dir = options.go_cache_dir or (module_dir / ".gocache")
    mod_cache_dir = options.go_mod_cache_dir or (module_dir / ".gomodcache")
    _ensure_directory(cache_dir)
    _ensure_directory(mod_cache_dir)

    env = load_env_cascade(root_dirs=[options.project_root], env_files=options.env_files)
    env.setdefault("PORT", str(options.port))
    env.setdefault("GOCACHE", str(cache_dir))
    env.setdefault("GOMODCACHE", str(mod_cache_dir))

    if options.set_go_defaults:
        env.setdefault("GOPROXY", "off")
        env.setdefault("GONOSUMDB", "*")

    if options.extra_env:
        env.update(options.extra_env)

    return ServiceConfig(
        name=options.name,
        command=command,
        cwd=module_dir,
        env=env,
        preferred_port=options.port,
        enable_tunnel=options.enable_tunnel,
        tunnel_domain=options.tunnel_domain,
        restart_on_failure=options.restart_on_failure,
        health_check_url=options.health_check_url,
        path_prefix=options.path_prefix,
    )
