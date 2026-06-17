"""
Azure Active Directory OAuth flow configuration with conditional prompts.
"""

from __future__ import annotations

from ..config import FlowStep, OAuthFlowConfig

AZURE_AD_FLOW = OAuthFlowConfig(
    provider="azure_ad",
    steps=[
        FlowStep(action="goto", description="Open Microsoft sign-in page"),
        FlowStep(
            action="wait_for_selector",
            description="Wait for Azure AD email field",
            selector="input#i0116, input[name='loginfmt']",
            timeout=20,
        ),
        FlowStep(
            action="fill",
            description="Enter Azure AD email",
            selector="input#i0116, input[name='loginfmt']",
            credential_key="email",
        ),
        FlowStep(
            action="click",
            description="Proceed to Azure AD password step",
            selector="input#idSIButton9, button:has-text('Next')",
            expect_navigation=True,
            timeout=20,
        ),
        FlowStep(
            action="wait_for_selector",
            description="Wait for Azure AD password field",
            selector="input#i0118, input[name='passwd']",
            timeout=20,
        ),
        FlowStep(
            action="fill",
            description="Enter Azure AD password",
            selector="input#i0118, input[name='passwd']",
            credential_key="password",
        ),
        FlowStep(
            action="click",
            description="Submit Azure AD credentials",
            selector="input#idSIButton9, button:has-text('Sign in')",
            expect_navigation=True,
            timeout=20,
        ),
        FlowStep(
            action="wait_for_selector",
            description="Check for Azure AD MFA prompt",
            selector="input[name='otc'], input[name='code'], input[type='tel'], input[aria-label*='code']",
            timeout=10,
            optional=True,
        ),
        FlowStep(
            action="fill",
            description="Enter Azure AD MFA code",
            selector="input[name='otc'], input[name='code'], input[type='tel'], input[aria-label*='code']",
            credential_key="mfa_code",
            optional=True,
        ),
        FlowStep(
            action="click",
            description="Submit Azure AD MFA",
            selector="input#idSubmit_SAOTCC_Continue, button:has-text('Verify'), button:has-text('Next')",
            expect_navigation=True,
            timeout=20,
            optional=True,
        ),
        FlowStep(
            action="wait_for_selector",
            description="Check for stay signed in prompt",
            selector="input#idSIButton9, button:has-text('Yes')",
            timeout=10,
            optional=True,
        ),
        FlowStep(
            action="click",
            description="Acknowledge stay signed in",
            selector="input#idSIButton9, button:has-text('Yes')",
            expect_navigation=True,
            timeout=15,
            optional=True,
        ),
        FlowStep(action="sleep", description="Wait for Azure AD redirect", value="3"),
        FlowStep(
            action="wait_for_url",
            description="Wait for Azure AD callback",
            url_substring="callback",
            timeout=25,
        ),
        FlowStep(
            action="capture_url",
            description="Capture Azure AD callback URL",
            store_key="callback_url",
            query_param="code",
        ),
    ],
)
