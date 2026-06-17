"""
High-level OAuth automation orchestrator.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Awaitable, Callable, Dict, Optional

try:
    from playwright.async_api import async_playwright

    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    async_playwright = None

from .config import OAuthFlowConfig
from .credentials import DEFAULT_CREDENTIAL_HINTS, CredentialResolver
from .executor import FlowContext, FlowExecutor, FlowResult
from .providers import (
    AUTHKIT_FLOW,
    AZURE_AD_FLOW,
    GITHUB_FLOW,
    GOOGLE_FLOW,
    GOOGLE_WORKSPACE_FLOW,
)
from .registry import ProviderRegistry


class OAuthAutomator:
    """
    Launch Playwright and execute configured OAuth flows.
    """

    def __init__(
        self,
        registry: ProviderRegistry,
        credential_resolver: Optional[CredentialResolver] = None,
        verbose: bool = True,
    ) -> None:
        self._registry = registry
        self._credential_resolver = credential_resolver or CredentialResolver()
        self._executor = FlowExecutor(verbose=verbose)

    async def authenticate(
        self,
        oauth_url: str,
        provider: str = "authkit",
        credential_overrides: Optional[Dict[str, str]] = None,
        mfa_code: Optional[str] = None,
        mfa_provider: Optional[Callable[[], Awaitable[str]]] = None,
    ) -> FlowResult:
        config = self._registry.get(provider)
        credentials = self._resolve_credentials(config, credential_overrides)

        async with self._launch_browser(config) as page:
            context = FlowContext(
                oauth_url=oauth_url,
                credentials=credentials,
                mfa_code=mfa_code,
                mfa_provider=mfa_provider,
            )
            result = await self._executor.run(page, config, context)
        return result

    def _resolve_credentials(
        self,
        config: OAuthFlowConfig,
        overrides: Optional[Dict[str, str]] = None,
    ):
        required = {
            key: DEFAULT_CREDENTIAL_HINTS.get(config.provider, {}).get(key)
            for key in config.required_credentials()
        }
        return self._credential_resolver.resolve(config.provider, required, overrides)

    @asynccontextmanager
    async def _launch_browser(self, config: OAuthFlowConfig):
        if not HAS_PLAYWRIGHT:
            raise RuntimeError("Playwright not available")
        async with async_playwright() as p:
            browser_kwargs: Dict[str, Any] = {"headless": True, **config.browser_kwargs}
            browser = await p.chromium.launch(**browser_kwargs)
            try:
                page_kwargs: Dict[str, Any] = {
                    "viewport": {"width": 1280, "height": 720},
                    **config.page_kwargs,
                }
                page = await (await browser.new_context(**page_kwargs)).new_page()
                yield page
            finally:
                await browser.close()


def build_default_registry() -> ProviderRegistry:
    """
    Return a registry pre-populated with common providers.
    """
    return ProviderRegistry(
        [
            AUTHKIT_FLOW,
            GITHUB_FLOW,
            GOOGLE_FLOW,
            GOOGLE_WORKSPACE_FLOW,
            AZURE_AD_FLOW,
        ]
    )


def create_default_automator(verbose: bool = True) -> OAuthAutomator:
    """
    Convenience helper that returns an automator with default providers.
    """
    if not HAS_PLAYWRIGHT:
        raise RuntimeError(
            "Playwright is required for OAuth automation. Install with: "
            "pip install playwright && playwright install chromium"
        )
    return OAuthAutomator(registry=build_default_registry(), verbose=verbose)
