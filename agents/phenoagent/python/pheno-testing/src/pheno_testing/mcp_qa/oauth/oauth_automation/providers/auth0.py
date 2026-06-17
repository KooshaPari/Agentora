"""
Auth0 universal login OAuth flow configuration with optional MFA.
"""

from __future__ import annotations

from ..config import FlowStep, OAuthFlowConfig

AUTH0_FLOW = OAuthFlowConfig(
    provider="auth0",
    steps=[
        FlowStep(action="goto", description="Open Auth0 Universal Login"),
        FlowStep(
            action="wait_for_selector",
            description="Wait for Auth0 email/username field",
            selector="input#username, input[name='username'], input[type='email']",
            timeout=15,
        ),
        FlowStep(
            action="fill",
            description="Enter Auth0 username or email",
            selector="input#username, input[name='username'], input[type='email']",
            credential_key="username",
        ),
        FlowStep(
            action="wait_for_selector",
            description="Wait for Auth0 password field",
            selector="input#password, input[name='password']",
            timeout=15,
        ),
        FlowStep(
            action="fill",
            description="Enter Auth0 password",
            selector="input#password, input[name='password']",
            credential_key="password",
        ),
        FlowStep(
            action="click",
            description="Submit Auth0 credentials",
            selector="button[type='submit'], button[name='action'], button:has-text('Continue')",
            expect_navigation=True,
            timeout=20,
        ),
        FlowStep(
            action="wait_for_selector",
            description="Check for Auth0 MFA prompt",
            selector="input[name='code'], input[type='tel'], input[aria-label*='code']",
            timeout=8,
            optional=True,
        ),
        FlowStep(
            action="fill",
            description="Enter Auth0 MFA code",
            selector="input[name='code'], input[type='tel'], input[aria-label*='code']",
            credential_key="mfa_code",
            optional=True,
        ),
        FlowStep(
            action="click",
            description="Verify Auth0 MFA",
            selector="button:has-text('Continue'), button:has-text('Verify')",
            expect_navigation=True,
            timeout=20,
            optional=True,
        ),
        FlowStep(
            action="click",
            description="Approve Auth0 consent",
            selector="button:has-text('Accept'), button:has-text('Allow'), button:has-text('Authorize')",
            expect_navigation=True,
            timeout=15,
            optional=True,
        ),
        FlowStep(action="sleep", description="Wait for Auth0 redirect", value="3"),
    ],
)
