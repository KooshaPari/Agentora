"""MCP-QA Testing Module.

Pytest-native testing utilities for MCP servers. Uses HTTP transport for 20x faster
testing and leverages pytest's built-in features.
"""

from .observable_client import (
    LiveProgressObserver,
    ObservableMCPClient,
    ProgressObserver,
    create_observable_client,
    observe_calls,
)
from .test_runner import (
    SmartTestRunner,
    TestRunner,
)
from .pytest_adapter import (
    HTTPMCPClient,
    mcp_auth_token,
    mcp_client,
    mcp_server_url,
    mcp_tool_caller,
)
from .session_manager import (
    SharedSessionManager,
    close_global_session_manager,
    get_session_manager,
)
from .unified_runner import (
    UnifiedMCPTestRunner,
    run_mcp_tests,
)

__all__ = [
    # HTTP Client & Fixtures
    "HTTPMCPClient",
    "mcp_client",
    "mcp_tool_caller",
    "mcp_server_url",
    "mcp_auth_token",
    # Session Management
    "SharedSessionManager",
    "get_session_manager",
    "close_global_session_manager",
    # Unified Test Runner
    "UnifiedMCPTestRunner",
    "run_mcp_tests",
    # Test Runner
    "TestRunner",
    "SmartTestRunner",
    # Observable Client
    "ObservableMCPClient",
    "ProgressObserver",
    "LiveProgressObserver",
    "create_observable_client",
    "observe_calls",
]

# Logging Configuration
from .logging_config import (
    QuietLogger,
    configure_test_logging,
    get_test_logger,
    print_test_header,
    print_test_summary,
    suppress_deprecation_warnings,
)

# Add to __all__
__all__.extend(
    [
        "configure_test_logging",
        "suppress_deprecation_warnings",
        "QuietLogger",
        "get_test_logger",
        "print_test_header",
        "print_test_summary",
    ]
)
