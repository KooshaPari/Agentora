"""
Default AuthKit OAuth flow configuration.
"""

from __future__ import annotations

from ..config import FlowStep, OAuthFlowConfig

AUTHKIT_FLOW = OAuthFlowConfig(
    provider="authkit",
    steps=[
        FlowStep(action="goto", description="Open OAuth consent page"),
        FlowStep(
            action="wait_for_selector",
            description="Wait for email input",
            selector="input[name='email']",
            timeout=15,
        ),
        FlowStep(
            action="fill",
            description="Enter email",
            selector="input[name='email']",
            credential_key="email",
        ),
        FlowStep(
            action="fill",
            description="Enter password",
            selector="input[name='password']",
            credential_key="password",
        ),
        FlowStep(
            action="click",
            description="Submit login form",
            selector='button[type="submit"]',
            expect_navigation=True,
            timeout=20,
        ),
        FlowStep(
            action="click",
            description="Approve OAuth request",
            selector=(
                "button:has-text('Allow Access'), "
                "button:has-text('Allow'), button:has-text('Authorize'), "
                "button:has-text('Continue')"
            ),
            expect_navigation=True,
            optional=True,
            timeout=15,
        ),
        FlowStep(
            action="sleep",
            description="Wait for callback redirect",
            value="3",
        ),
        FlowStep(
            action="wait_for_url",
            description="Wait for OAuth callback",
            url_substring="callback",
            timeout=15,
        ),
        FlowStep(
            action="capture_url",
            description="Capture callback URL",
            store_key="callback_url",
            query_param="code",
        ),
    ],
)
