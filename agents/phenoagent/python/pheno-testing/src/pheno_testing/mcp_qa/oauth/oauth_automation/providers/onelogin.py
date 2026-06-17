"""
OneLogin OAuth flow configuration covering MFA and consent prompts.
"""

from __future__ import annotations

from ..config import FlowStep, OAuthFlowConfig

ONELOGIN_FLOW = OAuthFlowConfig(
    provider="onelogin",
    steps=[
        FlowStep(action="goto", description="Open OneLogin sign-in page"),
        FlowStep(
            action="wait_for_selector",
            description="Wait for OneLogin username field",
            selector="input#username, input[name='email']",
            timeout=15,
        ),
        FlowStep(
            action="fill",
            description="Enter OneLogin username",
            selector="input#username, input[name='email']",
            credential_key="email",
        ),
        FlowStep(
            action="wait_for_selector",
            description="Wait for OneLogin password field",
            selector="input#password, input[type='password']",
            timeout=15,
        ),
        FlowStep(
            action="fill",
            description="Enter OneLogin password",
            selector="input#password, input[type='password']",
            credential_key="password",
        ),
        FlowStep(
            action="click",
            description="Submit OneLogin credentials",
            selector="button#loginButton, button[type='submit'], input[type='submit']",
            expect_navigation=True,
            timeout=20,
        ),
        FlowStep(
            action="wait_for_selector",
            description="Check for OneLogin MFA",
            selector="input#mfa-code, input[name='otp'], input[type='tel'], input[aria-label*='code']",
            timeout=8,
            optional=True,
        ),
        FlowStep(
            action="fill",
            description="Enter OneLogin MFA code",
            selector="input#mfa-code, input[name='otp'], input[type='tel'], input[aria-label*='code']",
            credential_key="mfa_code",
            optional=True,
        ),
        FlowStep(
            action="click",
            description="Verify OneLogin MFA",
            selector="button#verifyButton, button:has-text('Verify'), input[type='submit']",
            expect_navigation=True,
            timeout=20,
            optional=True,
        ),
        FlowStep(
            action="click",
            description="Approve OneLogin consent",
            selector="button:has-text('Allow'), button:has-text('Accept'), button:has-text('Continue')",
            expect_navigation=True,
            timeout=15,
            optional=True,
        ),
        FlowStep(action="sleep", description="Wait for OneLogin redirect", value="3"),
    ],
)
