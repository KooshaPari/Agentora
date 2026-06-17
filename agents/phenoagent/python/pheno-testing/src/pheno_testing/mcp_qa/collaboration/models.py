"""
Data models for collaboration features.
"""

import json
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass
class TestEvent:
    """
    Test event for broadcasting.
    """

    event_type: str  # started, completed, failed, etc.
    test_name: str
    endpoint: str
    user: str
    timestamp: float
    data: Dict[str, Any]

    def to_json(self) -> str:
        """
        Convert to JSON string.
        """
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, json_str: str) -> "TestEvent":
        """
        Create from JSON string.
        """
        data = json.loads(json_str)
        return cls(**data)


@dataclass
class PresenceInfo:
    """
    User presence information.
    """

    user: str
    endpoint: str
    test_name: Optional[str]
    status: str  # testing, idle, offline
    last_seen: float

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        """
        return asdict(self)


@dataclass
class TestResult:
    """
    Test result for comparison.
    """

    test_name: str
    endpoint: str
    success: bool
    duration: float
    timestamp: float
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        """
        return asdict(self)
