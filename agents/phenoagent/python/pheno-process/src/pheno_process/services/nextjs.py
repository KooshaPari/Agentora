"""
Factory helpers for Next.js services.
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
class NextJSServiceOptions:
    """
    Configuration options for building a Next.js service.
    """

    name: str
    project_root: Path
    app_dir: Path
    port: int
    dev_mode: bool = False
    local_mode: bool = False
    command_start: list[str] | None = None
    command_dev: list[str] | None = None
    command_local: list[str] | None = None
    env_files: Iterable[Path] = field(default_factory=list)
    extra_env: dict[str, str] | None = None
    enable_tunnel: bool = True
    tunnel_domain: str | None = None
    restart_on_failure: bool = True
    watch_paths: list[Path] | None = None
    watch_patterns: list[str] | None = None
    path_prefix: str = "/"


def build_nextjs_service(*, options: NextJSServiceOptions) -> ServiceConfig:
    """
    Construct a ``ServiceConfig`` for a Next.js application.
    """
    app_dir = options.app_dir
    app_dir.mkdir(parents=True, exist_ok=True)

    start_cmd = options.command_start or ["pnpm", "start"]
    dev_cmd = options.command_dev or ["pnpm", "dev"]
    local_cmd = options.command_local or ["pnpm", "dev:local"]

    if options.local_mode:
        command = local_cmd
    elif options.dev_mode:
        command = dev_cmd
    else:
        command = start_cmd

    watch_paths = options.watch_paths
    watch_patterns = options.watch_patterns
    if (options.dev_mode or options.local_mode) and not watch_paths:
        watch_paths = [app_dir / "app", app_dir / "components", app_dir / "lib"]
    if (options.dev_mode or options.local_mode) and not watch_patterns:
        watch_patterns = ["*.ts", "*.tsx", "*.js", "*.jsx"]

    env = load_env_cascade(root_dirs=[options.project_root], env_files=options.env_files)
    env.setdefault("PORT", str(options.port))
    if options.local_mode:
        env.setdefault("NEXT_PUBLIC_USE_LOCAL", "true")

    if options.extra_env:
        env.update(options.extra_env)

    return ServiceConfig(
        name=options.name,
        command=command,
        cwd=app_dir,
        env=env,
        preferred_port=options.port,
        enable_tunnel=options.enable_tunnel,
        tunnel_domain=options.tunnel_domain,
        restart_on_failure=options.restart_on_failure,
        watch_paths=watch_paths,
        watch_patterns=watch_patterns,
        path_prefix=options.path_prefix,
    )
