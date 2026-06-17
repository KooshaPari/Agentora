"""Enhanced Authentication Module for MCP Test Suites.

This module provides comprehensive authentication capabilities:
- Secure credential storage with AES-256 encryption
- Playwright state management and session reuse
- Multi-consumer token distribution (Playwright, MCP, API, CLI)
- MFA/TOTP automation
- Support for all major authentication flows and providers
"""

from .credential_manager import (
    Credential,
    CredentialManager,
    CredentialType,
    get_credential_manager,
)
from .mfa_handler import (
    MFAHandler,
    TOTPSimulator,
)
from .playwright_state_manager import (
    PlaywrightStateManager,
    StoredState,
)
from .token_broker import (
    AuthTokens,
    TokenBroker,
    get_token_broker,
)

__all__ = [
    # Credential Management
    "CredentialManager",
    "Credential",
    "CredentialType",
    "get_credential_manager",
    # MFA/OTP
    "MFAHandler",
    "TOTPSimulator",
    # Playwright State
    "PlaywrightStateManager",
    "StoredState",
    # Token Distribution
    "TokenBroker",
    "AuthTokens",
    "get_token_broker",
]
