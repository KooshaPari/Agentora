"""
Google OAuth flow configuration with enterprise support.
"""

from __future__ import annotations

from ..config import FlowStep, OAuthFlowConfig

GOOGLE_FLOW = OAuthFlowConfig(
    provider="google",
    steps=[
        FlowStep(action="goto", description="Open Google OAuth consent page"),
        FlowStep(
            action="wait_for_selector",
            description="Wait for email input",
            selector='input[type="email"]',
            timeout=15,
        ),
        FlowStep(
            action="fill",
            description="Enter Google email",
            selector='input[type="email"]',
            credential_key="email",
        ),
        FlowStep(
            action="click",
            description="Click Next button",
            selector='button:has-text("Next"), #identifierNext',
            expect_navigation=True,
            timeout=10,
        ),
        FlowStep(
            action="wait_for_selector",
            description="Wait for password input",
            selector='input[type="password"]',
            timeout=15,
        ),
        FlowStep(
            action="fill",
            description="Enter Google password",
            selector='input[type="password"]',
            credential_key="password",
        ),
        FlowStep(
            action="click",
            description="Click Next/Sign in",
            selector='button:has-text("Next"), #passwordNext',
            expect_navigation=True,
            timeout=20,
        ),
        # 2FA/MFA steps (conditional)
        FlowStep(
            action="wait_for_selector",
            description="Check for 2FA prompt",
            selector='input[type="tel"], input[aria-label*="code"]',
            timeout=5,
            optional=True,
        ),
        FlowStep(
            action="fill",
            description="Enter 2FA code",
            selector='input[type="tel"], input[aria-label*="code"]',
            credential_key="mfa_code",
            optional=True,
        ),
        FlowStep(
            action="click",
            description="Submit 2FA",
            selector='button:has-text("Next"), button:has-text("Verify")',
            expect_navigation=True,
            timeout=15,
            optional=True,
        ),
        # Consent screen
        FlowStep(
            action="wait_for_selector",
            description="Wait for consent screen",
            selector='button:has-text("Continue"), button:has-text("Allow")',
            timeout=10,
            optional=True,
        ),
        FlowStep(
            action="click",
            description="Grant consent",
            selector='button:has-text("Continue"), button:has-text("Allow")',
            expect_navigation=True,
            optional=True,
            timeout=15,
        ),
        FlowStep(action="sleep", description="Wait for redirect", value="3"),
        FlowStep(
            action="wait_for_url",
            description="Wait for Google callback",
            url_substring="callback",
            timeout=20,
        ),
        FlowStep(
            action="capture_url",
            description="Capture Google callback URL",
            store_key="callback_url",
            query_param="code",
        ),
    ],
)

# Google Workspace/Enterprise SSO
GOOGLE_WORKSPACE_FLOW = OAuthFlowConfig(
    provider="google_workspace",
    steps=[
        FlowStep(action="goto", description="Open Google Workspace OAuth"),
        FlowStep(
            action="wait_for_selector",
            description="Wait for workspace domain input",
            selector='input[type="email"], input[placeholder*="domain"]',
            timeout=15,
        ),
        FlowStep(
            action="fill",
            description="Enter workspace email",
            selector='input[type="email"], input[placeholder*="domain"]',
            credential_key="email",
        ),
        FlowStep(
            action="click",
            description="Continue to SSO",
            selector='button:has-text("Next"), button:has-text("Continue")',
            expect_navigation=True,
        ),
        FlowStep(
            action="sleep",
            description="Wait for SSO provider",
            value="5",
        ),
        FlowStep(
            action="wait_for_url",
            description="Wait for workspace callback",
            url_substring="callback",
            timeout=25,
            optional=True,
        ),
        FlowStep(
            action="capture_url",
            description="Capture workspace callback URL",
            store_key="callback_url",
            query_param="code",
            optional=True,
        ),
        # SSO provider-specific steps would be added dynamically
    ],
)
