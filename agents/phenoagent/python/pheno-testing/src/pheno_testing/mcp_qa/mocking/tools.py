"""
Mock tool builders.
"""

from typing import Any, Callable, Dict


class MockTool:
    """
    Mock tool for testing.
    """

    def __init__(self, name: str, handler: Callable):
        self.name = name
        self.handler = handler

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the mock tool.
        """
        return await self.handler(args)
