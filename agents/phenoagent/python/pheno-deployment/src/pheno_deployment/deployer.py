"""
Main deployer with YAML config support.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class Deployer:
    """
    Multi-cloud deployment orchestrator.
    """

    def __init__(self):
        self.services: dict[str, Any] = {}

    @classmethod
    def from_yaml(cls, path: str) -> Deployer:
        """
        Load deployment config from YAML.
        """
        config = yaml.safe_load(Path(path).read_text())
        deployer = cls()
        deployer.services = config.get("services", {})
        return deployer

    async def deploy(self, service: str) -> dict[str, Any]:
        """
        Deploy a service.
        """
        if service not in self.services:
            raise KeyError(f"Service '{service}' not found")
        config = self.services[service]
        platform = config.get("platform", "vercel")
        print(f"Deploying {service} to {platform}...")
        return {"service": service, "platform": platform, "status": "deployed"}

    async def deploy_all(self) -> dict[str, Any]:
        """
        Deploy all services.
        """
        results = {}
        for service in self.services:
            results[service] = await self.deploy(service)
        return results
