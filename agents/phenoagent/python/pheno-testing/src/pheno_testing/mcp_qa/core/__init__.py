"""
MCP QA Core - Unified Testing Framework Components

Provides shared testing infrastructure for MCP servers:
- Test registration and discovery
- Test execution (parallel/sequential)
- Live event-driven execution
- Client adapters
- Result caching
- Health checks
"""

# Reporters (re-exported from reporters package for backward compatibility)
from pheno.testing.mcp_qa.reporters import (
    ConsoleReporter,
    DetailedErrorReporter,
    FunctionalityMatrixReporter,
    JSONReporter,
    MarkdownReporter,
    TestReporter,
)

# Adapters
from .adapters import MCPClientAdapter

# Test Runners
from .base.test_runner import BaseTestRunner as TestRunner

# Cache
from .cache import TestCache

# Parallel Execution
from .client_pool import WorkerClientPool
from .connection_manager import ConnectionManager, ConnectionState, WaitStrategy

# Data Generators
from .data_generators import DataGenerator

# Decorators
from .decorators import cache_result
from .enhanced_adapter import EnhancedMCPAdapter, create_enhanced_adapter

# Health Checks
from .health_checks import HealthChecker
from .live_runner import LiveTestRunner
from .parallel_clients import ParallelClientManager

# Progress Display
from .progress_display import ComprehensiveProgressDisplay

# Test Registry
from .test_registry import (
    TestRegistry,
    get_test_registry,
    mcp_test,
    require_auth,
    retry,
    skip_if,
    timeout,
)

# Streaming
try:
    from .streaming import (
        InstantFeedbackMode,
        ParallelStreamCollector,
        SmartBatchingBuffer,
        StreamingResultDisplay,
        TestResult,
    )

    HAS_STREAMING = True
except ImportError:
    HAS_STREAMING = False

__all__ = [
    # Registry
    "TestRegistry",
    "get_test_registry",
    "mcp_test",
    "require_auth",
    "skip_if",
    "timeout",
    "retry",
    "cache_result",
    # Adapters
    "MCPClientAdapter",
    "EnhancedMCPAdapter",
    "create_enhanced_adapter",
    # Cache
    "TestCache",
    # Runners
    "TestRunner",
    "LiveTestRunner",
    # Health
    "HealthChecker",
    # Reporters
    "TestReporter",
    "ConsoleReporter",
    "JSONReporter",
    "MarkdownReporter",
    "FunctionalityMatrixReporter",
    "DetailedErrorReporter",
    # Progress
    "ComprehensiveProgressDisplay",
    # Data
    "DataGenerator",
    # Parallel
    "WorkerClientPool",
    "ParallelClientManager",
    "ConnectionManager",
    "ConnectionState",
    "WaitStrategy",
    # Streaming
    "TestResult",
    "ParallelStreamCollector",
    "SmartBatchingBuffer",
    "InstantFeedbackMode",
    "StreamingResultDisplay",
]

if HAS_STREAMING:
    __all__.extend(
        [
            "TestResult",
            "ParallelStreamCollector",
            "SmartBatchingBuffer",
            "InstantFeedbackMode",
            "StreamingResultDisplay",
        ]
    )


__version__ = "0.1.0"
