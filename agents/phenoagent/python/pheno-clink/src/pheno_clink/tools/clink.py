"""Clink tool bridge - placeholder for zen-mcp-server integration."""

from __future__ import annotations

from typing import Any

from ..registry import get_registry


class CLinkTool:
    """Bridge MCP requests to configured CLI agents.

    This is a placeholder class that zen-mcp-server can import and subclass. The actual
    implementation details depend on zen's SimpleTool base classes and MCP-specific
    integrations.
    """

    def __init__(self) -> None:
        self._registry = get_registry()
        self._cli_names = self._registry.list_clients()

        # Set up role mapping
        self._role_map: dict[str, list[str]] = {}
        for name in self._cli_names:
            try:
                self._role_map[name] = self._registry.list_roles(name)
            except Exception:
                self._role_map[name] = ["default"]

        self._all_roles = sorted({role for roles in self._role_map.values() for role in roles})

        # Determine default CLI
        if "gemini" in self._cli_names:
            self._default_cli_name = "gemini"
        else:
            self._default_cli_name = self._cli_names[0] if self._cli_names else None

    def get_registry(self):
        """
        Get the clink registry for schema building.
        """
        return self._registry

    def get_available_clis(self) -> list[str]:
        """
        Get list of available CLI clients.
        """
        return self._cli_names.copy()

    def get_available_roles(self, cli_name: str) -> list[str]:
        """
        Get available roles for a specific CLI.
        """
        return self._role_map.get(cli_name, ["default"]).copy()

    def get_all_roles(self) -> list[str]:
        """
        Get all available roles across all CLIs.
        """
        return self._all_roles.copy()

    def get_default_cli(self) -> str | None:
        """
        Get the default CLI name.
        """
        return self._default_cli_name

    def get_input_schema_info(self) -> dict[str, Any]:
        """Get schema information for building the MCP input schema.

        Returns:
            Dictionary containing CLI names, role mappings, and defaults
            that can be used to build a proper MCP schema.
        """
        role_descriptions = []
        for name in self._cli_names:
            roles = ", ".join(sorted(self._role_map.get(name, ["default"]))) or "default"
            role_descriptions.append(f"{name}: {roles}")

        cli_available = ", ".join(self._cli_names) if self._cli_names else "(none configured)"
        default_text = (
            f" Default: {self._default_cli_name}."
            if self._default_cli_name and len(self._cli_names) <= 1
            else ""
        )

        return {
            "cli_names": self._cli_names,
            "role_map": self._role_map,
            "all_roles": self._all_roles,
            "default_cli": self._default_cli_name,
            "cli_description": (
                "Configured CLI client name (from conf/cli_clients). Available: "
                + cli_available
                + default_text
            ),
            "role_description": (
                "Optional role preset defined for the selected CLI (defaults to 'default'). Roles per CLI: "
                + "; ".join(role_descriptions)
            ),
        }


def create_clink_tool() -> CLinkTool:
    """
    Factory function to create a CLinkTool instance.
    """
    return CLinkTool()
