"""
Reusable OAuth automation helpers for Playwright-based tests.
"""

from .automator import OAuthAutomator, create_default_automator
from .config import (
    FlowStep,
    OAuthFlowConfig,
    flow_config_from_dict,
    load_flow_config_from_yaml,
)
from .executor import FlowResult
from .registry import ProviderRegistry

__all__ = [
    "OAuthAutomator",
    "create_default_automator",
    "FlowStep",
    "OAuthFlowConfig",
    "FlowResult",
    "ProviderRegistry",
    "flow_config_from_dict",
    "load_flow_config_from_yaml",
]
