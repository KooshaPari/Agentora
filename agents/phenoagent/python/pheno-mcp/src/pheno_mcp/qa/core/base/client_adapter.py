"""Client adapter abstractions used by the MCP QA tooling.

Historically each MCP project implemented its own adapter that exposed a
consistent interface to the test runner.  For the consolidated implementation
we provide a lightweight base class and a concrete ``MCPClientAdapter`` that
wraps an arbitrary client object.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class BaseClientAdapter:
    """Minimal adapter wrapper.

    ``BaseClientAdapter`` places no requirements on the wrapped client beyond
    exposing it via the ``client`` attribute.  Projects typically subclass this
    to add helpers for domain-specific tooling.
    """

    client: Any


class MCPClientAdapter(BaseClientAdapter):
    """Convenience adapter for generic MCP clients.

    The adapter normalises a couple of frequently accessed attributes so the test runner
    can display friendly information without knowing the concrete client type.
    """

    @property
    def endpoint(self) -> str:
        client = self.client
        return getattr(client, "endpoint", getattr(client, "url", ""))

    async def list_tools(self) -> list[str]:
        if hasattr(self.client, "list_tools"):
            tools = await self.client.list_tools()  # type: ignore[func-returns-value]
            if isinstance(tools, list):
                return [
                    tool["name"] if isinstance(tool, dict) and "name" in tool else str(tool)
                    for tool in tools
                ]
        return []


__all__ = ["BaseClientAdapter", "MCPClientAdapter"]
