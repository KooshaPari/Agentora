"""
Mock prompt builders.
"""

from typing import Any, Dict, List


class MockPrompt:
    """
    Mock prompt for testing.
    """

    def __init__(self, name: str, description: str, arguments: List[Dict[str, Any]]):
        self.name = name
        self.description = description
        self.arguments = arguments

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dict representation.
        """
        return {"name": self.name, "description": self.description, "arguments": self.arguments}
