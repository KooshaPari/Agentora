"""
Enhanced OAuth Flow Adapters - Complete Coverage

This module extends the base flow adapters with support for:
- Microsoft Azure AD / Entra ID
- Auth0 Universal Login
- Magic Link flows (with email prompting)
- Passkey/WebAuthn flows (with Virtual Authenticator)
- SAML-based SSO
- Traditional form variations
- MFA/OTP prompting integration

Each adapter handles provider-specific workflows with automatic
fallback to user prompts when automation isn't possible.
"""

import asyncio

# Import base classes from existing module
import sys
from pathlib import Path
from typing import Awaitable, Callable, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from pheno.testing.mcp_qa.oauth.flow_adapters import (
        FlowConfig,
        OAuthFlowAdapter,
        OAuthFlowFactory,
    )
except ImportError:
    # Fallback if running from different location
    from flow_adapters import FlowConfig, OAuthFlowAdapter, OAuthFlowFactory


class MicrosoftOAuthFlow(OAuthFlowAdapter):
    """Microsoft Azure AD / Entra ID OAuth flow.

    Handles:
    - Personal Microsoft accounts
    - Work/School accounts
    - Azure AD Enterprise SSO
    """

    def get_config(self) -> FlowConfig:
        return FlowConfig(
            name="microsoft_oauth",
            selectors={
                "email": 'input[type="email"]',
                "email_next": 'input[type="submit"][value="Next"]',
                "password": 'input[name="passwd"]',
                "password_submit": 'input[type="submit"][value="Sign in"]',
                "stay_signed_in": 'input[type="submit"][value="Yes"]',
                "allow_button": 'input[type="submit"][value="Accept"]',
            },
            steps=[
                "fill_email",
                "click_email_next",
                "fill_password",
                "click_password_submit",
                "click_stay_signed_in",
                "click_allow",
            ],
        )

    async def _click_email_next(self, page, config: FlowConfig):
        """
        Click next after email.
        """
        selector = config.selectors["email_next"]
        if await self.wait_for_selector_safe(page, selector, step_name="microsoft_email_next"):
            await page.click(selector)
            await asyncio.sleep(2)

    async def _click_password_submit(self, page, config: FlowConfig):
        """
        Click sign in after password.
        """
        selector = config.selectors["password_submit"]
        if await self.wait_for_selector_safe(page, selector, step_name="microsoft_password_submit"):
            await page.click(selector)
            await page.wait_for_load_state("networkidle", timeout=10000)
            await asyncio.sleep(2)

    async def _click_stay_signed_in(self, page, config: FlowConfig):
        """
        Handle 'Stay signed in?' prompt.
        """
        selector = config.selectors["stay_signed_in"]
        # This prompt is optional
        try:
            await page.wait_for_selector(selector, timeout=5000)
            await page.click(selector)
            await asyncio.sleep(2)
        except Exception:
            # Prompt didn't appear, continue
            pass


class Auth0UniversalLoginFlow(OAuthFlowAdapter):
    """Auth0 Universal Login flow.

    Supports:
    - Username/password authentication
    - Social login integration
    - Passwordless (email/SMS)
    """

    def __init__(
        self, email: str, password: str, domain: Optional[str] = None, debug: bool = False
    ):
        super().__init__(email, password, debug)
        self.domain = domain

    def get_config(self) -> FlowConfig:
        return FlowConfig(
            name="auth0_universal",
            selectors={
                "email": 'input[name="email"]',
                "password": 'input[name="password"]',
                "submit": 'button[type="submit"]',
                "allow_button": 'button[value="accept"]',
            },
            steps=["fill_email", "fill_password", "click_submit", "click_allow"],
        )

    async def _click_submit(self, page, config: FlowConfig):
        """
        Click submit button.
        """
        selector = config.selectors["submit"]
        if await self.wait_for_selector_safe(page, selector, step_name="auth0_submit"):
            await page.click(selector)
            await page.wait_for_load_state("networkidle", timeout=10000)
            await asyncio.sleep(2)


class MagicLinkFlow(OAuthFlowAdapter):
    """Magic Link authentication flow.

    Strategy:
    - Request magic link via email
    - Prompt user to click link
    - Wait for callback

    Future: Auto-fetch from email API
    """

    def __init__(
        self,
        email: str,
        password: str = "",  # Not needed for magic links
        email_fetcher: Optional[Callable[[], Awaitable[str]]] = None,
        debug: bool = False,
    ):
        super().__init__(email, password, debug)
        self.email_fetcher = email_fetcher

    def get_config(self) -> FlowConfig:
        return FlowConfig(
            name="magic_link",
            selectors={
                "email": 'input[type="email"]',
                "submit": 'button[type="submit"]',
            },
            steps=["fill_email", "click_submit", "wait_for_magic_link"],
        )

    async def _click_submit(self, page, config: FlowConfig):
        """
        Submit email for magic link.
        """
        selector = config.selectors["submit"]
        if await self.wait_for_selector_safe(page, selector, step_name="magic_link_submit"):
            await page.click(selector)
            await asyncio.sleep(2)

    async def _wait_for_magic_link(self, page, config: FlowConfig):
        """
        Wait for user to click magic link.
        """
        if self.email_fetcher:
            # Future: Auto-fetch magic link from email
            magic_link = await self.email_fetcher()
            await page.goto(magic_link)
        else:
            # Prompt user
            print(f"\n📧 Magic link sent to {self.email}")
            print("⏳ Please click the link in your email to continue...")
            print("   Waiting for authentication to complete...\n")

            # Wait for redirect back to OAuth callback
            # The page will automatically redirect when user clicks link
            await page.wait_for_url("**/oauth/callback*", timeout=300000)  # 5 min timeout


class PasskeyWebAuthnFlow(OAuthFlowAdapter):
    """Passkey / WebAuthn authentication flow.

    Strategy:
    - Detect WebAuthn challenge
    - Pause automation
    - Prompt user to complete passkey challenge

    For testing: Use Playwright's Virtual Authenticator
    """

    def __init__(
        self,
        email: str,
        password: str = "",  # Not needed for passkeys
        use_virtual_authenticator: bool = False,
        debug: bool = False,
    ):
        super().__init__(email, password, debug)
        self.use_virtual_authenticator = use_virtual_authenticator

    def get_config(self) -> FlowConfig:
        return FlowConfig(
            name="passkey_webauthn",
            selectors={
                "email": 'input[type="email"]',
                "passkey_button": 'button[data-action="passkey"]',
            },
            steps=["fill_email", "click_passkey_button", "handle_webauthn_challenge"],
        )

    async def _click_passkey_button(self, page, config: FlowConfig):
        """
        Click passkey/WebAuthn button.
        """
        selector = config.selectors["passkey_button"]
        if await self.wait_for_selector_safe(page, selector, step_name="passkey_button"):
            await page.click(selector)
            await asyncio.sleep(1)

    async def _handle_webauthn_challenge(self, page, config: FlowConfig):
        """
        Handle WebAuthn authentication challenge.
        """

        if self.use_virtual_authenticator:
            # Set up virtual authenticator for testing
            cdp = await page.context.new_cdp_session(page)
            await cdp.send("WebAuthn.enable")
            await cdp.send(
                "WebAuthn.addVirtualAuthenticator",
                {
                    "options": {
                        "protocol": "ctap2",
                        "transport": "usb",
                        "hasResidentKey": True,
                        "hasUserVerification": True,
                        "isUserVerified": True,
                    }
                },
            )

            # Wait for challenge to complete automatically
            await asyncio.sleep(3)
        else:
            # Real passkey - prompt user
            print("\n🔐 Passkey authentication required")
            print("⏳ Please complete the passkey challenge on your device...")
            print("   (Touch your security key, use biometrics, etc.)\n")

            # Wait for WebAuthn to complete
            # The page will navigate on success
            await page.wait_for_url("**/oauth/callback*", timeout=120000)  # 2 min timeout


class TraditionalFormFlow(OAuthFlowAdapter):
    """Traditional username/password form with smart selector detection.

    Handles variations like:
    - #username, #login, #user, input[name="username"]
    - #password, #pass, input[type="password"]
    - button[type="submit"], #login-button, input[value="Login"]
    """

    def get_config(self) -> FlowConfig:
        return FlowConfig(
            name="traditional_form",
            selectors={
                "username": "#username",  # Will try alternates
                "password": "#password",  # Will try alternates
                "submit": 'button[type="submit"]',  # Will try alternates
            },
            steps=["fill_username", "fill_password", "click_submit"],
        )

    async def _fill_username(self, page, config: FlowConfig):
        """
        Fill username with smart selector fallback.
        """
        selectors = [
            "#username",
            "#login",
            "#user",
            'input[name="username"]',
            'input[name="login"]',
            'input[name="user"]',
            'input[type="text"]',
            'input[type="email"]',
        ]

        for selector in selectors:
            try:
                await page.wait_for_selector(selector, timeout=2000)
                await page.fill(selector, self.email)
                await asyncio.sleep(0.3)
                return
            except Exception:
                continue

        print("⚠️  Could not find username field")
        await self.dump_page_state(page, "username_not_found")

    async def _fill_password(self, page, config: FlowConfig):
        """
        Fill password with smart selector fallback.
        """
        selectors = [
            "#password",
            "#pass",
            "#pwd",
            'input[name="password"]',
            'input[name="pass"]',
            'input[type="password"]',
        ]

        for selector in selectors:
            try:
                await page.wait_for_selector(selector, timeout=2000)
                await page.fill(selector, self.password)
                await asyncio.sleep(0.3)
                return
            except Exception:
                continue

        print("⚠️  Could not find password field")
        await self.dump_page_state(page, "password_not_found")

    async def _click_submit(self, page, config: FlowConfig):
        """
        Click submit with smart selector fallback.
        """
        selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            "#login-button",
            "#submit",
            'button:has-text("Log in")',
            'button:has-text("Sign in")',
            'input[value="Login"]',
            'input[value="Sign In"]',
        ]

        for selector in selectors:
            try:
                await page.wait_for_selector(selector, timeout=2000)
                await page.click(selector)
                await page.wait_for_load_state("networkidle", timeout=10000)
                await asyncio.sleep(2)
                return
            except Exception:
                continue

        print("⚠️  Could not find submit button")
        await self.dump_page_state(page, "submit_not_found")


class SAMLSSOFlow(OAuthFlowAdapter):
    """SAML-based SSO flow.

    Handles:
    - Enterprise SAML IdP authentication
    - Redirect-based SAML flows
    - Post-SAML callback handling
    """

    def __init__(
        self, email: str, password: str, idp_domain: Optional[str] = None, debug: bool = False
    ):
        super().__init__(email, password, debug)
        self.idp_domain = idp_domain

    def get_config(self) -> FlowConfig:
        return FlowConfig(
            name="saml_sso",
            selectors={
                "email": 'input[type="email"]',
                "continue_button": 'button:has-text("Continue")',
                "password": 'input[type="password"]',
                "signin_button": 'button[type="submit"]',
            },
            steps=[
                "fill_email",
                "click_continue",
                "wait_for_idp_redirect",
                "fill_password",
                "click_signin",
            ],
        )

    async def _click_continue(self, page, config: FlowConfig):
        """
        Click continue to redirect to IdP.
        """
        selector = config.selectors["continue_button"]
        if await self.wait_for_selector_safe(page, selector, step_name="saml_continue"):
            await page.click(selector)
            await asyncio.sleep(2)

    async def _wait_for_idp_redirect(self, page, config: FlowConfig):
        """
        Wait for redirect to SAML IdP.
        """
        # Wait for navigation to IdP domain
        await page.wait_for_load_state("networkidle", timeout=10000)
        await asyncio.sleep(2)

        if self.debug:
            await self.dump_page_state(page, "saml_idp_page")


# Register all new adapters with factory
OAuthFlowFactory.register("microsoft", MicrosoftOAuthFlow)
OAuthFlowFactory.register("azure", MicrosoftOAuthFlow)
OAuthFlowFactory.register("auth0", Auth0UniversalLoginFlow)
OAuthFlowFactory.register("magic_link", MagicLinkFlow)
OAuthFlowFactory.register("passkey", PasskeyWebAuthnFlow)
OAuthFlowFactory.register("webauthn", PasskeyWebAuthnFlow)
OAuthFlowFactory.register("traditional", TraditionalFormFlow)
OAuthFlowFactory.register("saml", SAMLSSOFlow)


__all__ = [
    "MicrosoftOAuthFlow",
    "Auth0UniversalLoginFlow",
    "MagicLinkFlow",
    "PasskeyWebAuthnFlow",
    "TraditionalFormFlow",
    "SAMLSSOFlow",
]
