"""Intelligent test execution optimizer for maximizing test suite performance.

Features:
- Pre-warming connections and fixtures
- Predictive execution based on historical data
- Dependency-aware scheduling
- Fail-fast optimization
- Test sharding for parallel execution
"""

from .dependency_analyzer import DependencyAnalyzer
from .failfast import FailFastOptimizer
from .orchestrator import IntelligentExecutionOrchestrator
from .predictive_engine import PredictiveExecutionEngine
from .prewarmer import TestPreWarmer
from .sharding import TestSharding
from .types import TestExecution, TestMetrics

__all__ = [
    "TestMetrics",
    "TestExecution",
    "TestPreWarmer",
    "PredictiveExecutionEngine",
    "DependencyAnalyzer",
    "FailFastOptimizer",
    "TestSharding",
    "IntelligentExecutionOrchestrator",
]
