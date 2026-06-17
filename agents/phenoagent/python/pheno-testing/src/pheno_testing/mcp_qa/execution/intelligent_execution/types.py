"""Data types for intelligent test execution."""

from dataclasses import dataclass
from typing import Callable, List, Optional


@dataclass
class TestMetrics:
    """Historical metrics for a test."""

    test_id: str
    avg_duration: float
    run_count: int
    last_duration: float
    failure_count: int
    last_run: float
    dependencies: List[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class TestExecution:
    """Test execution request."""

    test_id: str
    test_func: Callable
    category: str
    tool: str
    estimated_duration: float = 0.0
    dependencies: List[str] = None
    shard_id: Optional[int] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
