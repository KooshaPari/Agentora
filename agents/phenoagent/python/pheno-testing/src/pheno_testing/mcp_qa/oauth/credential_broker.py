"""Unified Credential Broker for MCP Test Suites.

This module provides a single, consistent OAuth flow that:
1. Prompts for credentials interactively when missing
2. Uses Playwright to automate OAuth and capture auth tokens
3. Shows progress inline (single overwritten line)
4. Saves credentials to .env for reuse
5. Provides credentials for direct HTTP test calls

Usage:
    broker = UnifiedCredentialBroker()
    client, credentials = await broker.get_authenticated_client()

    # Use client for MCP calls
    tools = await client.list_tools()

    # Use credentials for direct HTTP calls
    response = requests.post(url, headers={"Authorization": f"Bearer {credentials.access_token}"})
"""

from pheno.testing.mcp_qa.oauth.broker_core import (
    CapturedCredentials,
    OAuthProgress,
    UnifiedCredentialBroker,
    get_authenticated_mcp_client,
)

__all__ = [
    "CapturedCredentials",
    "OAuthProgress",
    "UnifiedCredentialBroker",
    "get_authenticated_mcp_client",
]
