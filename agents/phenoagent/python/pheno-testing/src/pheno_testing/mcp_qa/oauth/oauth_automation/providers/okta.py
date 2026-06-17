"""
Okta OAuth flow configuration with adaptive MFA handling.
"""

from __future__ import annotations

from ..config import FlowStep, OAuthFlowConfig

OKTA_FLOW = OAuthFlowConfig(
    provider="okta",
    steps=[
        FlowStep(action="goto", description="Open Okta sign-in page"),
        FlowStep(
            action="wait_for_selector",
            description="Wait for Okta username field",
            selector="input#okta-signin-username, input[name='username']",
            timeout=15,
        ),
        FlowStep(
            action="fill",
            description="Enter Okta username",
            selector="input#okta-signin-username, input[name='username']",
            credential_key="username",
        ),
        FlowStep(
            action="wait_for_selector",
            description="Wait for Okta password field",
            selector="input#okta-signin-password, input[name='password']",
            timeout=15,
        ),
        FlowStep(
            action="fill",
            description="Enter Okta password",
            selector="input#okta-signin-password, input[name='password']",
            credential_key="password",
        ),
        FlowStep(
            action="click",
            description="Submit Okta credentials",
            selector="input#okta-signin-submit, button[data-type='save'], button[type='submit']",
            expect_navigation=True,
            timeout=20,
        ),
        FlowStep(
            action="wait_for_selector",
            description="Check for MFA challenge",
            selector="input[name='answer'], input[name='otp'], input[type='tel'], input[aria-label*='code']",
            timeout=8,
            optional=True,
        ),
        FlowStep(
            action="fill",
            description="Enter Okta MFA code",
            selector="input[name='answer'], input[name='otp'], input[type='tel'], input[aria-label*='code']",
            credential_key="mfa_code",
            optional=True,
        ),
        FlowStep(
            action="click",
            description="Verify Okta MFA",
            selector="button[data-se='verify-button'], button[type='submit'], input[type='submit']",
            expect_navigation=True,
            timeout=20,
            optional=True,
        ),
        FlowStep(
            action="click",
            description="Grant Okta consent",
            selector="button[data-se='allow-access'], button:has-text('Allow'), button:has-text('Accept')",
            expect_navigation=True,
            timeout=15,
            optional=True,
        ),
        FlowStep(action="sleep", description="Wait for Okta redirect", value="3"),
    ],
)
