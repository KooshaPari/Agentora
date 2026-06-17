"""
Generic service helpers for KInfra-managed projects.
"""

__all__ = []

try:
    from pheno.infra.orchestration import (
        GoServiceOptions,
        NextJSServiceOptions,
        ServiceFactory,
        ServiceLauncher,
        build_go_service,
        build_nextjs_service,
    )
except ImportError:
    GoServiceOptions = None  # type: ignore
    NextJSServiceOptions = None  # type: ignore
    ServiceFactory = None  # type: ignore
    ServiceLauncher = None  # type: ignore
    build_go_service = None  # type: ignore
    build_nextjs_service = None  # type: ignore
else:
    __all__ = [
        "GoServiceOptions",
        "NextJSServiceOptions",
        "ServiceFactory",
        "ServiceLauncher",
        "build_go_service",
        "build_nextjs_service",
    ]
