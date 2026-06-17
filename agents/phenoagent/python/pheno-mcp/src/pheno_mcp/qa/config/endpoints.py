"""
Endpoint registry for MCP QA environments.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Environment(Enum):
    PRODUCTION = "production"
    PREVIEW = "preview"
    LOCAL = "local"


class MCPProject(Enum):
    ATOMS = "atoms"
    ZEN = "zen"
    SANDBOX = "sandbox"


@dataclass
class EndpointConfig:
    production: str
    preview: str | None = None
    local: str | None = None


class EndpointRegistry:
    """
    Central registry for MCP endpoints across environments.
    """

    _registry: dict[MCPProject, EndpointConfig] = {
        MCPProject.ATOMS: EndpointConfig(
            production="https://mcp.atoms.tech",
            preview="https://preview.mcp.atoms.tech",
            local="http://localhost:50002",
        ),
        MCPProject.ZEN: EndpointConfig(
            production="https://mcp.zenml.ai",
            preview="https://preview.mcp.zenml.ai",
            local="http://localhost:50012",
        ),
        MCPProject.SANDBOX: EndpointConfig(
            production="https://mcp-sandbox.kooshapari.com",
            local="http://localhost:50100",
        ),
    }

    @classmethod
    def register_config(cls, project: MCPProject, config: EndpointConfig) -> None:
        cls._registry[project] = config

    @classmethod
    def get_endpoint(cls, project: MCPProject, environment: Environment) -> str:
        config = cls._registry.get(project)
        if not config:
            raise KeyError(f"No endpoint configuration registered for project '{project.value}'")

        if environment is Environment.PRODUCTION and config.production:
            return config.production
        if environment is Environment.PREVIEW and config.preview:
            return config.preview
        if environment is Environment.LOCAL and config.local:
            return config.local

        raise KeyError(
            f"No endpoint configured for project '{project.value}' in environment '{environment.value}'",
        )

    @classmethod
    def set_endpoint(cls, project: MCPProject, environment: Environment, value: str) -> None:
        config = cls._registry.setdefault(project, EndpointConfig(production=""))
        if environment is Environment.PRODUCTION:
            config.production = value
        elif environment is Environment.PREVIEW:
            config.preview = value
        else:
            config.local = value

    @classmethod
    def list_projects(cls) -> tuple[MCPProject, ...]:
        return tuple(cls._registry.keys())


__all__ = ["EndpointConfig", "EndpointRegistry", "Environment", "MCPProject"]
