"""OAuth Flow Adapters - Concrete Implementations.

This module provides concrete OAuth flow adapters for various providers:
- AuthKit Standard (email/password)
- AuthKit Standalone Connect (3rd party auth)
- Google OAuth
- GitHub OAuth
- Custom provider support
"""

import asyncio
import json
from typing import Optional

from pheno.testing.mcp_qa.oauth.flow_adapters_core import (
    FlowConfig,
    InvalidCredentialsError,
    OAuthFlowAdapter,
)


class AuthKitStandardFlow(OAuthFlowAdapter):
    """AuthKit standard email/password flow."""

    def __init__(
        self,
        email: str,
        password: str,
        *,
        consent_mode: str = "optional",
        max_login_attempts: int = 2,
        login_field_selector: Optional[str] = None,
        post_signin_grace: float = 2.0,
        allow_optional_timeout: int = 7000,
        debug: bool = False,
    ):
        super().__init__(email, password, debug)
        mode = str(consent_mode).lower()
        if mode not in {"required", "optional", "skip"}:
            raise ValueError("consent_mode must be one of 'required', 'optional', or 'skip'")
        self.consent_mode = mode
        self.max_login_attempts = max(1, int(max_login_attempts))
        self.login_field_selector = login_field_selector or "#email"
        self.post_signin_grace = float(post_signin_grace)
        self.allow_optional_timeout = int(allow_optional_timeout)

    def get_config(self) -> FlowConfig:
        steps = [
            "fill_email",
            "click_continue_if_present",
            "fill_password",
            "click_signin",
            "verify_login_transition",
        ]
        if self.consent_mode != "skip":
            steps.append("click_allow")

        return FlowConfig(
            name="authkit_standard",
            selectors={
                "email": "#email",
                "password": "#password",
                "continue_button": "button:has-text('Continue'), button:has-text('Next')",
                "signin_button": 'button[type="submit"]',
                "allow_button": (
                    "button:has-text('Allow access'), "
                    "button:has-text('Allow Access'), "
                    "button:has-text('Allow'), button:has-text('Authorize'), "
                    "button:has-text('Continue'), button[value='approve'][type='submit']"
                ),
            },
            steps=steps,
            options={
                "consent_mode": self.consent_mode,
                "allow_optional_timeout": self.allow_optional_timeout,
                "max_login_attempts": self.max_login_attempts,
                "login_field_selector": self.login_field_selector,
                "post_signin_grace": self.post_signin_grace,
            },
        )

    async def _verify_login_transition(self, page, config: FlowConfig) -> bool:
        login_selector = config.options.get("login_field_selector") or config.selectors.get("email")
        post_signin_grace = float(config.options.get("post_signin_grace", 2.0))
        max_attempts = int(config.options.get("max_login_attempts", 1))

        if post_signin_grace > 0:
            await asyncio.sleep(post_signin_grace)

        if await self._login_transition_detected(page, login_selector):
            return True

        for attempt in range(2, max_attempts + 1):
            print(f"⚠️  AuthKit login did not advance; retrying {attempt}/{max_attempts}...")
            await self._fill_email(page, config)
            await self._fill_password(page, config)
            await self._click_signin(page, config)

            if post_signin_grace > 0:
                await asyncio.sleep(post_signin_grace)

            if await self._login_transition_detected(page, login_selector):
                return True

        print("❌ AuthKit login failed to progress after retries.")
        await self.dump_page_state(page, "authkit_login_retry_exhausted")
        return False

    async def _check_for_invalid_credentials(self, page) -> bool:
        """Check if invalid credentials error is displayed."""
        try:
            tree = await page.accessibility.snapshot()
            if tree:
                tree_str = json.dumps(tree)
                if (
                    "Invalid login credentials" in tree_str
                    or "invalid credentials" in tree_str.lower()
                ):
                    return True

            html = await page.content()
            if "Invalid login credentials" in html or "invalid credentials" in html.lower():
                return True

            error_selectors = [
                "[role='alert']",
                ".error-message",
                ".alert-error",
                "[data-testid='error']",
            ]

            for selector in error_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.inner_text()
                        if text and ("invalid" in text.lower() and "credential" in text.lower()):
                            return True
                except Exception:
                    continue

        except Exception as e:
            self.logger.debug("Error checking for invalid credentials", error=str(e))

        return False

    async def _login_transition_detected(
        self,
        page,
        login_selector: Optional[str],
    ) -> bool:
        """Determine if the AuthKit login page advanced after submitting credentials."""
        if await self._check_for_invalid_credentials(page):
            raise InvalidCredentialsError("Invalid login credentials detected")

        if self._last_url_before_signin and self._last_url_after_signin:
            if self._last_url_after_signin != self._last_url_before_signin:
                return True

        if not login_selector:
            return False

        try:
            element = await page.query_selector(login_selector)
        except Exception:
            return True

        if not element:
            return True

        try:
            is_visible = await element.is_visible()
        except Exception:
            return True

        return not is_visible


class AuthKitAdaptiveFlow(AuthKitStandardFlow):
    """AuthKit flow that retries login and treats consent as optional by default."""

    def __init__(
        self,
        email: str,
        password: str,
        *,
        max_login_attempts: int = 3,
        post_signin_grace: float = 2.0,
        allow_optional_timeout: int = 7000,
        debug: bool = False,
    ):
        super().__init__(
            email,
            password,
            consent_mode="optional",
            max_login_attempts=max_login_attempts,
            post_signin_grace=post_signin_grace,
            allow_optional_timeout=allow_optional_timeout,
            debug=debug,
        )


class AuthKitStandaloneConnectFlow(OAuthFlowAdapter):
    """AuthKit standalone connect flow (3rd party providers)."""

    def __init__(
        self,
        email: str,
        password: str,
        provider: str = "google",
        *,
        consent_mode: str = "optional",
        debug: bool = False,
    ):
        super().__init__(email, password, debug)
        self.provider = provider
        mode = str(consent_mode).lower()
        if mode not in {"required", "optional", "skip"}:
            raise ValueError("consent_mode must be one of 'required', 'optional', or 'skip'")
        self.consent_mode = mode

    def get_config(self) -> FlowConfig:
        steps = ["third_party_auth"]
        if self.consent_mode != "skip":
            steps.append("click_allow")

        return FlowConfig(
            name=f"authkit_standalone_{self.provider}",
            selectors={
                "provider_button": f'button[data-provider="{self.provider}"]',
                "google_email": 'input[type="email"]',
                "google_password": 'input[type="password"]',
                "google_next": "#identifierNext",
                "google_submit": "#passwordNext",
            },
            steps=steps,
            options={
                "consent_mode": self.consent_mode,
                "allow_optional_timeout": 8000,
            },
        )

    async def _third_party_auth(self, page, config: FlowConfig):
        """Handle Google/GitHub/etc authentication."""
        if self.provider == "google":
            await self._google_auth(page, config)
        elif self.provider == "github":
            await self._github_auth(page, config)
        else:
            print(f"⚠️  Unsupported provider: {self.provider}")

    async def _google_auth(self, page, config: FlowConfig):
        """Google OAuth flow."""
        provider_btn = config.selectors["provider_button"]
        if await self.wait_for_selector_safe(page, provider_btn, step_name="google_provider"):
            await page.click(provider_btn)
            await asyncio.sleep(2)

        email_selector = config.selectors["google_email"]
        if await self.wait_for_selector_safe(page, email_selector, step_name="google_email"):
            await page.fill(email_selector, self.email)
            await page.click(config.selectors["google_next"])
            await asyncio.sleep(2)

        password_selector = config.selectors["google_password"]
        if await self.wait_for_selector_safe(page, password_selector, step_name="google_password"):
            await page.fill(password_selector, self.password)
            await page.click(config.selectors["google_submit"])
            await asyncio.sleep(3)

    async def _github_auth(self, page, config: FlowConfig):
        """GitHub OAuth flow."""
        provider_btn = 'button[data-provider="github"]'
        if await self.wait_for_selector_safe(page, provider_btn, step_name="github_provider"):
            await page.click(provider_btn)
            await asyncio.sleep(2)

        if await self.wait_for_selector_safe(page, "#login_field", step_name="github_login"):
            await page.fill("#login_field", self.email)
            await page.fill("#password", self.password)
            await page.click('input[type="submit"]')
            await asyncio.sleep(3)


class GoogleOAuthFlow(OAuthFlowAdapter):
    """Direct Google OAuth flow (not via AuthKit)."""

    def get_config(self) -> FlowConfig:
        return FlowConfig(
            name="google_direct",
            selectors={
                "email": 'input[type="email"]',
                "email_next": "#identifierNext",
                "password": 'input[type="password"]',
                "password_next": "#passwordNext",
                "allow_button": 'button[data-action="allow"]',
            },
            steps=[
                "fill_email",
                "click_next_email",
                "fill_password",
                "click_next_password",
                "click_allow",
            ],
        )

    async def _click_next_email(self, page, config: FlowConfig):
        """Click next after email."""
        await page.click(config.selectors["email_next"])
        await asyncio.sleep(2)

    async def _click_next_password(self, page, config: FlowConfig):
        """Click next after password."""
        await page.click(config.selectors["password_next"])
        await asyncio.sleep(3)


class GitHubOAuthFlow(OAuthFlowAdapter):
    """Direct GitHub OAuth flow."""

    def get_config(self) -> FlowConfig:
        return FlowConfig(
            name="github_direct",
            selectors={
                "email": "#login_field",
                "password": "#password",
                "signin_button": 'input[type="submit"]',
                "authorize_button": 'button[name="authorize"]',
            },
            steps=["fill_email", "fill_password", "click_signin", "click_authorize"],
        )

    async def _click_authorize(self, page, config: FlowConfig):
        """Click authorize button."""
        selector = config.selectors.get("authorize_button", 'button[name="authorize"]')
        if await self.wait_for_selector_safe(page, selector, step_name="github_authorize"):
            await page.click(selector)
            await asyncio.sleep(3)


class CustomOAuthFlow(OAuthFlowAdapter):
    """Custom OAuth flow with configurable selectors.

    Usage:
        config = FlowConfig(
            name="my_custom_flow",
            selectors={'email': '#username', 'password': '#pwd', ...},
            steps=["fill_email", "fill_password", "click_signin"]
        )
        adapter = CustomOAuthFlow(email, password, config)
    """

    def __init__(self, email: str, password: str, config: FlowConfig, debug: bool = False):
        super().__init__(email, password, debug)
        self.custom_config = config

    def get_config(self) -> FlowConfig:
        return self.custom_config


class OAuthFlowFactory:
    """Factory for creating OAuth flow adapters."""

    _adapters = {
        "authkit": AuthKitStandardFlow,
        "authkit_standard": AuthKitStandardFlow,
        "authkit_adaptive": AuthKitAdaptiveFlow,
        "authkit_connect": AuthKitStandaloneConnectFlow,
        "google": GoogleOAuthFlow,
        "github": GitHubOAuthFlow,
    }

    @classmethod
    def create(
        cls, provider: str, email: str, password: str, debug: bool = False, **kwargs
    ) -> OAuthFlowAdapter:
        """Create an OAuth flow adapter.

        Args:
            provider: Provider name (authkit, google, github, etc.)
            email: User email
            password: User password
            debug: Enable debug mode (HTML dumps on failures)
            **kwargs: Additional provider-specific arguments

        Returns:
            OAuthFlowAdapter instance

        Example:
            # AuthKit standard
            adapter = OAuthFlowFactory.create('authkit', email, password)

            # AuthKit with Google
            adapter = OAuthFlowFactory.create('authkit_connect', email, password, provider='google')

            # Direct Google
            adapter = OAuthFlowFactory.create('google', email, password, debug=True)
        """
        adapter_class = cls._adapters.get(provider.lower())

        if not adapter_class:
            raise ValueError(
                f"Unknown provider: {provider}. Available: {', '.join(cls._adapters.keys())}"
            )

        return adapter_class(email, password, debug=debug, **kwargs)

    @classmethod
    def register(cls, name: str, adapter_class: type):
        """Register a custom adapter."""
        cls._adapters[name] = adapter_class

    @classmethod
    def list_providers(cls) -> list[str]:
        """List available providers."""
        return list(cls._adapters.keys())


def create_oauth_adapter(
    provider: str = "authkit",
    email: str = "",
    password: str = "",
    debug: bool = False,
    **kwargs,
) -> OAuthFlowAdapter:
    """Convenience function to create OAuth adapter.

    Args:
        provider: Provider name (default: authkit)
        email: User email
        password: User password
        debug: Enable debug mode with HTML dumps
        **kwargs: Provider-specific arguments

    Returns:
        OAuthFlowAdapter instance
    """
    return OAuthFlowFactory.create(provider, email, password, debug, **kwargs)
