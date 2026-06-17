"""
Unified startup framework for Pheno-SDK infrastructure kits.

The startup package exposes a thin façade around the infrastructure toolkit,
making it straightforward for projects to bootstrap local or remote resources.

Typical usage::

    from pheno.kits.infra.startup import StartupConfig, UnifiedStartup

    async def setup():
        config = StartupConfig(
            project_name="router",
            preferred_port=8080,
            tunnel_subdomain="ai",
            resources={"postgres": {...}},
        )
        return await UnifiedStartup(config).startup()
"""

from .config import StartupConfig
from .framework import UnifiedStartup

__all__ = ["StartupConfig", "UnifiedStartup"]

