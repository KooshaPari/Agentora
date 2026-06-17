"""OAuth Flow Adapters for Different Providers and User Flows.

This module provides specialized adapters for various OAuth flows:
- AuthKit Standard (email/password)
- AuthKit Standalone Connect (3rd party auth)
- Google OAuth
- GitHub OAuth
- Custom provider support

Each adapter handles provider-specific selectors and workflows.

Backward compatibility: This module re-exports all items from the decomposed modules.
For new code, prefer importing directly from the submodules:
    from pheno.testing.mcp_qa.oauth.flow_adapters_core import OAuthFlowAdapter, FlowConfig
    from pheno.testing.mcp_qa.oauth.flow_adapters_handlers import AuthKitStandardFlow
"""

from pheno.testing.mcp_qa.oauth.flow_adapters_core import (
    FlowConfig,
    InvalidCredentialsError,
    OAuthFlowAdapter,
)
from pheno.testing.mcp_qa.oauth.flow_adapters_handlers import (
    AuthKitAdaptiveFlow,
    AuthKitStandaloneConnectFlow,
    AuthKitStandardFlow,
    CustomOAuthFlow,
    GitHubOAuthFlow,
    GoogleOAuthFlow,
    OAuthFlowFactory,
    create_oauth_adapter,
)

__all__ = [
    "FlowConfig",
    "InvalidCredentialsError",
    "OAuthFlowAdapter",
    "AuthKitStandardFlow",
    "AuthKitAdaptiveFlow",
    "AuthKitStandaloneConnectFlow",
    "GoogleOAuthFlow",
    "GitHubOAuthFlow",
    "CustomOAuthFlow",
    "OAuthFlowFactory",
    "create_oauth_adapter",
]
