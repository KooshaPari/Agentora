"""
Example GitHub OAuth flow for future expansion.
"""

from __future__ import annotations

from ..config import FlowStep, OAuthFlowConfig

GITHUB_FLOW = OAuthFlowConfig(
    provider="github",
    steps=[
        FlowStep(action="goto", description="Open GitHub OAuth consent page"),
        FlowStep(
            action="wait_for_selector",
            description="Wait for username field",
            selector="input#login_field",
            timeout=20,
        ),
        FlowStep(
            action="fill",
            description="Enter GitHub username",
            selector="input#login_field",
            credential_key="username",
        ),
        FlowStep(
            action="fill",
            description="Enter GitHub password",
            selector="input#password",
            credential_key="password",
        ),
        FlowStep(
            action="click",
            description="Submit GitHub credentials",
            selector="input[name='commit']",
            expect_navigation=True,
            timeout=30,
        ),
        FlowStep(
            action="click",
            description="Authorize OAuth application",
            selector="button[name='authorize']",
            optional=True,
            expect_navigation=True,
            timeout=20,
        ),
        FlowStep(action="sleep", description="Wait for GitHub redirect", value="2"),
        FlowStep(
            action="wait_for_url",
            description="Wait for GitHub callback",
            url_substring="callback",
            timeout=20,
        ),
        FlowStep(
            action="capture_url",
            description="Capture GitHub callback URL",
            store_key="callback_url",
            query_param="code",
        ),
    ],
)
