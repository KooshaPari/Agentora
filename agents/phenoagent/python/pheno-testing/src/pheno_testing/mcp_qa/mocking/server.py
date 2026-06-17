"""
Mock MCP Server for unit testing.
"""

import asyncio
from typing import Any, Callable, Dict, List, Optional


class MockMCPServer:
    """
    Lightweight mock MCP server for unit testing.
    """

    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.resources: Dict[str, Dict[str, Any]] = {}
        self.prompts: Dict[str, Dict[str, Any]] = {}
        self.call_history: List[Dict[str, Any]] = []

    def register_tool(self, name: str, handler: Callable):
        """Register a tool handler.

        Args:
            name: Tool name
            handler: Callable that takes args dict and returns response dict

        Usage:
            mock_server.register_tool("chat", lambda args: {
                "success": True,
                "response": f"Mock response to: {args['prompt']}"
            })
        """
        self.tools[name] = handler

    def register_resource(self, uri: str, resource: Dict[str, Any]):
        """
        Register a mock resource.
        """
        self.resources[uri] = resource

    def register_prompt(self, name: str, prompt: Dict[str, Any]):
        """
        Register a mock prompt.
        """
        self.prompts[name] = prompt

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a registered tool.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool response dict

        Raises:
            ValueError: If tool not registered
        """
        # Record call in history
        self.call_history.append(
            {
                "type": "tool",
                "name": name,
                "arguments": arguments,
            }
        )

        if name not in self.tools:
            return {
                "success": False,
                "error": f"Tool not found: {name}",
                "error_code": "TOOL_NOT_FOUND",
            }

        handler = self.tools[name]
        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(arguments)
            else:
                result = handler(arguments)
            return result
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_code": "HANDLER_ERROR",
            }

    async def get_resource(self, uri: str) -> Optional[Dict[str, Any]]:
        """
        Get a registered resource.
        """
        self.call_history.append(
            {
                "type": "resource",
                "uri": uri,
            }
        )
        return self.resources.get(uri)

    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        List all registered tools.
        """
        return [{"name": name, "description": f"Mock tool: {name}"} for name in self.tools.keys()]

    async def list_resources(self) -> List[Dict[str, Any]]:
        """
        List all registered resources.
        """
        return [{"uri": uri, **resource} for uri, resource in self.resources.items()]

    async def list_prompts(self) -> List[Dict[str, Any]]:
        """
        List all registered prompts.
        """
        return list(self.prompts.values())

    def get_call_history(self) -> List[Dict[str, Any]]:
        """
        Get history of all calls made to this server.
        """
        return self.call_history.copy()

    def clear_history(self):
        """
        Clear call history.
        """
        self.call_history.clear()

    async def cleanup(self):
        """
        Cleanup server resources.
        """
        self.tools.clear()
        self.resources.clear()
        self.prompts.clear()
        self.call_history.clear()
