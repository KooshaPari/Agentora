"""
Quality analysis configuration presets and management.
"""


from .core import QualityConfig

# Default configuration
DEFAULT_CONFIG = QualityConfig(
    enabled_tools=[],
    thresholds={
        "max_violations": 100,
        "max_warnings": 200,
        "max_errors": 50,
        "quality_score_threshold": 70.0,
    },
    filters={},
    output_format="json",
    output_path=None,
    include_metadata=True,
    parallel_analysis=True,
    max_workers=4,
    timeout_seconds=300,
)

# Pheno-SDK specific configuration
PHENO_SDK_CONFIG = QualityConfig(
    enabled_tools=[
        "pattern_detector",
        "architectural_validator",
        "performance_detector",
        "security_scanner",
        "code_smell_detector",
        "integration_gates",
        "atlas_health",
    ],
    thresholds={
        "max_violations": 50,
        "max_warnings": 100,
        "max_errors": 10,
        "quality_score_threshold": 80.0,
        "max_loop_iterations": 1000,
        "max_nested_loops": 3,
        "max_function_calls": 50,
        "max_memory_usage_mb": 100,
        "max_response_time_ms": 1000,
        "max_database_queries": 10,
        "max_file_operations": 5,
        "max_network_calls": 3,
        "long_method_lines": 50,
        "long_method_complexity": 15,
        "large_class_methods": 20,
        "large_class_lines": 500,
        "long_parameter_list": 5,
        "duplicate_code_lines": 10,
        "dead_code_unused_days": 30,
        "magic_number_count": 5,
        "deep_nesting": 4,
        "long_chain_calls": 5,
        "too_many_returns": 3,
        "cyclomatic_complexity": 10,
    },
    filters={
        "severity": ["high", "critical"],
        "impact": ["High", "Critical"],
        "file_patterns": ["*.py"],
        "exclude_patterns": ["__pycache__", "*.pyc", ".git", "node_modules"],
    },
    output_format="json",
    output_path="reports",
    include_metadata=True,
    parallel_analysis=True,
    max_workers=4,
    timeout_seconds=300,
)

# Zen-MCP-Server specific configuration
ZEN_MCP_CONFIG = QualityConfig(
    enabled_tools=[
        "pattern_detector",
        "architectural_validator",
        "performance_detector",
        "security_scanner",
        "code_smell_detector",
        "integration_gates",
    ],
    thresholds={
        "max_violations": 75,
        "max_warnings": 150,
        "max_errors": 15,
        "quality_score_threshold": 75.0,
        "max_loop_iterations": 2000,
        "max_nested_loops": 4,
        "max_function_calls": 75,
        "max_memory_usage_mb": 200,
        "max_response_time_ms": 2000,
        "max_database_queries": 15,
        "max_file_operations": 8,
        "max_network_calls": 5,
        "long_method_lines": 75,
        "long_method_complexity": 20,
        "large_class_methods": 30,
        "large_class_lines": 750,
        "long_parameter_list": 7,
        "duplicate_code_lines": 15,
        "dead_code_unused_days": 45,
        "magic_number_count": 8,
        "deep_nesting": 5,
        "long_chain_calls": 7,
        "too_many_returns": 4,
        "cyclomatic_complexity": 15,
    },
    filters={
        "severity": ["medium", "high", "critical"],
        "impact": ["Medium", "High", "Critical"],
        "file_patterns": ["*.py", "*.js", "*.ts"],
        "exclude_patterns": ["__pycache__", "*.pyc", ".git", "node_modules", "dist", "build"],
    },
    output_format="json",
    output_path="reports",
    include_metadata=True,
    parallel_analysis=True,
    max_workers=6,
    timeout_seconds=600,
)

# Atoms-MCP-Old specific configuration
ATOMS_MCP_CONFIG = QualityConfig(
    enabled_tools=[
        "pattern_detector",
        "architectural_validator",
        "performance_detector",
        "security_scanner",
        "code_smell_detector",
        "integration_gates",
    ],
    thresholds={
        "max_violations": 100,
        "max_warnings": 200,
        "max_errors": 25,
        "quality_score_threshold": 70.0,
        "max_loop_iterations": 3000,
        "max_nested_loops": 5,
        "max_function_calls": 100,
        "max_memory_usage_mb": 300,
        "max_response_time_ms": 3000,
        "max_database_queries": 20,
        "max_file_operations": 10,
        "max_network_calls": 8,
        "long_method_lines": 100,
        "long_method_complexity": 25,
        "large_class_methods": 40,
        "large_class_lines": 1000,
        "long_parameter_list": 10,
        "duplicate_code_lines": 20,
        "dead_code_unused_days": 60,
        "magic_number_count": 10,
        "deep_nesting": 6,
        "long_chain_calls": 10,
        "too_many_returns": 5,
        "cyclomatic_complexity": 20,
    },
    filters={
        "severity": ["low", "medium", "high", "critical"],
        "impact": ["Low", "Medium", "High", "Critical"],
        "file_patterns": ["*.py", "*.js", "*.ts", "*.go", "*.rs"],
        "exclude_patterns": [
            "__pycache__",
            "*.pyc",
            ".git",
            "node_modules",
            "dist",
            "build",
            "target",
        ],
    },
    output_format="json",
    output_path="reports",
    include_metadata=True,
    parallel_analysis=True,
    max_workers=8,
    timeout_seconds=900,
)

# Strict configuration for high-quality codebases
STRICT_CONFIG = QualityConfig(
    enabled_tools=[
        "pattern_detector",
        "architectural_validator",
        "performance_detector",
        "security_scanner",
        "code_smell_detector",
        "integration_gates",
    ],
    thresholds={
        "max_violations": 25,
        "max_warnings": 50,
        "max_errors": 5,
        "quality_score_threshold": 90.0,
        "max_loop_iterations": 500,
        "max_nested_loops": 2,
        "max_function_calls": 25,
        "max_memory_usage_mb": 50,
        "max_response_time_ms": 500,
        "max_database_queries": 5,
        "max_file_operations": 3,
        "max_network_calls": 2,
        "long_method_lines": 25,
        "long_method_complexity": 8,
        "large_class_methods": 10,
        "large_class_lines": 250,
        "long_parameter_list": 3,
        "duplicate_code_lines": 5,
        "dead_code_unused_days": 14,
        "magic_number_count": 2,
        "deep_nesting": 2,
        "long_chain_calls": 3,
        "too_many_returns": 2,
        "cyclomatic_complexity": 5,
    },
    filters={
        "severity": ["high", "critical"],
        "impact": ["High", "Critical"],
        "file_patterns": ["*.py"],
        "exclude_patterns": ["__pycache__", "*.pyc", ".git", "node_modules", "test_*", "*_test.py"],
    },
    output_format="json",
    output_path="reports",
    include_metadata=True,
    parallel_analysis=True,
    max_workers=2,
    timeout_seconds=180,
)

# Lenient configuration for legacy codebases
LENIENT_CONFIG = QualityConfig(
    enabled_tools=[
        "pattern_detector",
        "architectural_validator",
        "performance_detector",
        "security_scanner",
        "code_smell_detector",
        "integration_gates",
    ],
    thresholds={
        "max_violations": 500,
        "max_warnings": 1000,
        "max_errors": 100,
        "quality_score_threshold": 50.0,
        "max_loop_iterations": 10000,
        "max_nested_loops": 10,
        "max_function_calls": 200,
        "max_memory_usage_mb": 1000,
        "max_response_time_ms": 10000,
        "max_database_queries": 50,
        "max_file_operations": 20,
        "max_network_calls": 20,
        "long_method_lines": 200,
        "long_method_complexity": 50,
        "large_class_methods": 100,
        "large_class_lines": 2000,
        "long_parameter_list": 20,
        "duplicate_code_lines": 50,
        "dead_code_unused_days": 180,
        "magic_number_count": 50,
        "deep_nesting": 10,
        "long_chain_calls": 20,
        "too_many_returns": 10,
        "cyclomatic_complexity": 50,
    },
    filters={
        "severity": ["critical"],
        "impact": ["Critical"],
        "file_patterns": ["*.py", "*.js", "*.ts", "*.go", "*.rs", "*.java", "*.cpp", "*.c"],
        "exclude_patterns": ["__pycache__", "*.pyc", ".git"],
    },
    output_format="json",
    output_path="reports",
    include_metadata=True,
    parallel_analysis=True,
    max_workers=12,
    timeout_seconds=1800,
)

# Configuration registry
CONFIG_REGISTRY = {
    "default": DEFAULT_CONFIG,
    "pheno-sdk": PHENO_SDK_CONFIG,
    "zen-mcp": ZEN_MCP_CONFIG,
    "atoms-mcp": ATOMS_MCP_CONFIG,
    "strict": STRICT_CONFIG,
    "lenient": LENIENT_CONFIG,
}


def get_config(preset: str) -> QualityConfig:
    """
    Get configuration by preset name.
    """
    return CONFIG_REGISTRY.get(preset, DEFAULT_CONFIG)


def list_configs() -> list[str]:
    """
    List available configuration presets.
    """
    return list(CONFIG_REGISTRY.keys())


def create_custom_config(base_preset: str = "default", **overrides) -> QualityConfig:
    """
    Create a custom configuration based on a preset.
    """
    base_config = get_config(base_preset)

    # Create new config with overrides
    config_dict = base_config.to_dict()
    config_dict.update(overrides)

    return QualityConfig.from_dict(config_dict)
