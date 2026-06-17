"""MCP QA Utilities Package.

Provides shared utilities for MCP testing including health checks, helpers, validators,
data generators, logging, configuration, database, auth, and metrics. Unified from Zen
and Atoms frameworks.
"""

from .auth_utils import (
    CredentialStore,
    SessionManager,
    TokenManager,
    TokenSet,
    decode_jwt,
    extract_user_from_jwt,
    is_token_expired,
)
from .config_utils import (
    AuthConfig,
    ConfigBase,
    ConfigManager,
    DatabaseConfig,
    ServerConfig,
    get_env,
    get_env_config,
    load_env_file,
    load_yaml,
    save_yaml,
)
from .database_utils import (
    DatabaseAdapter,
    QueryCache,
    QueryFilter,
    SupabaseDatabaseAdapter,
)

# Existing utilities
from .health_checks import HealthChecker, HealthCheckResult
from .helpers import (
    DataGenerator,
    FieldValidator,
    PerformanceTracker,
    ResponseValidator,
    TimeoutManager,
    WaitStrategy,
    is_connection_error,
    timeout_wrapper,
)

# New consolidated utilities
from .logging_utils import (
    LoggerContext,
    QuietLogger,
    configure_logging,
    get_logger,
    quiet_library_loggers,
    set_verbose_mode,
)
from .metrics_utils import (
    Counter,
    Gauge,
    Histogram,
    MetricsAggregator,
    MetricsCollector,
    MetricsReporter,
    MetricValue,
)

__all__ = [
    # Health Checks
    "HealthChecker",
    "HealthCheckResult",
    # Data Generation
    "DataGenerator",
    # Validation
    "ResponseValidator",
    "FieldValidator",
    # Timeout Management
    "TimeoutManager",
    "timeout_wrapper",
    # Retry Strategies
    "WaitStrategy",
    "is_connection_error",
    # Performance
    "PerformanceTracker",
    # Logging
    "configure_logging",
    "get_logger",
    "quiet_library_loggers",
    "set_verbose_mode",
    "LoggerContext",
    "QuietLogger",
    # Config
    "get_env",
    "get_env_config",
    "load_env_file",
    "load_yaml",
    "save_yaml",
    "ConfigBase",
    "ConfigManager",
    "DatabaseConfig",
    "ServerConfig",
    "AuthConfig",
    # Database
    "QueryFilter",
    "QueryCache",
    "DatabaseAdapter",
    "SupabaseDatabaseAdapter",
    # Auth
    "decode_jwt",
    "extract_user_from_jwt",
    "is_token_expired",
    "TokenSet",
    "TokenManager",
    "CredentialStore",
    "SessionManager",
    # Metrics
    "MetricValue",
    "Counter",
    "Gauge",
    "Histogram",
    "MetricsCollector",
    "MetricsAggregator",
    "MetricsReporter",
]

__version__ = "2.0.0"
