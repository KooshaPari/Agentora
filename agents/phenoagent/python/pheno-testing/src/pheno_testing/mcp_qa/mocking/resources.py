"""
Mock resource builders.
"""

from typing import Any, Dict


class MockResource:
    """
    Mock resource for testing.
    """

    def __init__(self, uri: str, content: str):
        self.uri = uri
        self.content = content

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dict representation.
        """
        return {"uri": self.uri, "content": self.content}
