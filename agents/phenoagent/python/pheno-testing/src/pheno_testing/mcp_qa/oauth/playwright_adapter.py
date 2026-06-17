"""Unified Playwright OAuth Adapter.

Combines best features from both Zen and Atoms implementations:
- Clean OAuth automation with retry logic
- Flexible provider support with flow adapters
- MFA/TOTP integration
- Callback URL capture and triggering
- Debug mode with HTML dumps on failures
"""

import asyncio

# Import for type hints only (avoid circular import)
from typing import TYPE_CHECKING, Awaitable, Callable, Dict, Optional
from urllib.parse import parse_qs, urlparse

from fastmcp import Client
from fastmcp.client.auth import OAuth

from pheno.testing.mcp_qa.logging import get_logger

from .flow_adapters import InvalidCredentialsError, OAuthFlowAdapter, OAuthFlowFactory

if TYPE_CHECKING:
    from pheno.testing.mcp_qa.oauth.granular_progress import GranularOAuthProgress


class PlaywrightOAuthAdapter:
    """Unified adapter for Playwright-based OAuth automation.

    Features:
    - Automated OAuth login with retry on server errors
    - OAuth URL and callback port capture
    - MFA code/provider support
    - Integration with reusable automation engine
    """

    def __init__(
        self,
        email: str,
        password: str,
        *,
        provider: str = "authkit",
        credential_overrides: Optional[Dict[str, str]] = None,
        mfa_code: Optional[str] = None,
        mfa_provider: Optional[Callable[[], Awaitable[str]]] = None,
        debug: bool = False,
        flow_adapter: Optional[OAuthFlowAdapter] = None,
    ):
        """Initialize Playwright OAuth adapter.

        Args:
            email: User email
            password: User password
            provider: OAuth provider name (default: "authkit")
            credential_overrides: Optional credential overrides
            mfa_code: Static MFA code (if applicable)
            mfa_provider: Async function that returns MFA code
            debug: Enable debug mode (dumps HTML on failures)
            flow_adapter: Custom flow adapter (overrides provider)
        """
        self.email = email
        self.password = password
        self.provider = provider
        self.credential_overrides = dict(credential_overrides or {})
        self.oauth_url: Optional[str] = None
        self.callback_port: Optional[int] = None
        self.mfa_handler = None  # Can be set externally for TOTP
        self._mfa_code = mfa_code
        self._mfa_provider = mfa_provider
        self._last_flow_result = None
        self.debug = debug

        # Create or use provided flow adapter
        self.flow_adapter = flow_adapter or OAuthFlowFactory.create(
            provider=provider, email=email, password=password, debug=debug
        )
        self.logger = get_logger(__name__).bind(provider=provider, email=email)
        self._credential_reprompt_callback: Optional[Callable[[], tuple[str, str]]] = None
        self._invalid_credentials_detected = False
        self._progress_tracker: Optional["GranularOAuthProgress"] = None

    def set_credential_reprompt_callback(self, callback: Callable[[], tuple[str, str]]):
        """Set callback function to reprompt for credentials.

        Args:
            callback: Function that returns (email, password) tuple when called
        """
        self._credential_reprompt_callback = callback

    def set_progress_tracker(self, progress: "GranularOAuthProgress"):
        """Set progress tracker for granular step updates.

        Args:
            progress: GranularOAuthProgress instance
        """
        self._progress_tracker = progress
        # Also set on flow adapter
        if hasattr(self.flow_adapter, "set_progress_tracker"):
            self.flow_adapter.set_progress_tracker(progress)

    async def automate_login_with_retry(
        self, oauth_url: str, max_retries: int = 3, allow_credential_reprompt: bool = True
    ) -> bool:
        """Automate OAuth login with retry on server errors.

        Args:
            oauth_url: OAuth authorization URL
            max_retries: Maximum number of retry attempts
            allow_credential_reprompt: Allow reprompting for credentials on invalid credentials error

        Returns:
            True if successful, False otherwise
        """
        invalid_creds_count = 0

        for attempt in range(1, max_retries + 1):
            try:
                self.logger.debug(
                    "OAuth automation attempt", attempt=attempt, max_retries=max_retries
                )
                result = await self.automate_login(oauth_url)

                if result:
                    return True

                if attempt < max_retries:
                    wait_time = 2**attempt
                    self.logger.warning(
                        "OAuth failed, retrying", wait_time=wait_time, attempt=attempt
                    )
                    await asyncio.sleep(wait_time)

            except InvalidCredentialsError:
                invalid_creds_count += 1
                self._invalid_credentials_detected = True

                self.logger.warning(
                    "Invalid credentials detected",
                    attempt=attempt,
                    invalid_count=invalid_creds_count,
                    emoji="🚫",
                )

                # After max_retries with invalid credentials, offer to reprompt
                if invalid_creds_count >= max_retries and allow_credential_reprompt:
                    if self._credential_reprompt_callback:
                        self.logger.info(
                            "Reprompting for credentials after invalid login", emoji="🔄"
                        )

                        try:
                            new_email, new_password = self._credential_reprompt_callback()
                            if new_email and new_password:
                                # Update credentials
                                self.email = new_email
                                self.password = new_password
                                self.flow_adapter.email = new_email
                                self.flow_adapter.password = new_password

                                # Reset counter and try again with new credentials
                                invalid_creds_count = 0
                                self._invalid_credentials_detected = False

                                self.logger.info("Retrying with new credentials", emoji="🔑")

                                # Give one more set of retries with new credentials
                                for retry_attempt in range(1, max_retries + 1):
                                    try:
                                        result = await self.automate_login(oauth_url)
                                        if result:
                                            return True
                                    except InvalidCredentialsError:
                                        if retry_attempt < max_retries:
                                            await asyncio.sleep(2)
                                            continue
                                        else:
                                            self.logger.error(
                                                "New credentials also invalid", emoji="❌"
                                            )
                                            return False
                        except Exception as callback_error:
                            self.logger.error(
                                "Credential reprompt failed", error=str(callback_error), emoji="❌"
                            )
                    else:
                        self.logger.error(
                            "Invalid credentials but no reprompt callback set", emoji="❌"
                        )
                        return False
                else:
                    # Still have retries left with invalid credentials
                    if attempt < max_retries:
                        wait_time = 2**attempt
                        self.logger.warning(
                            "Retrying with same credentials", wait_time=wait_time, emoji="⏳"
                        )
                        await asyncio.sleep(wait_time)

            except Exception as e:
                error_msg = str(e)
                # Retry on server errors
                if "502" in error_msg or "503" in error_msg or "530" in error_msg:
                    if attempt < max_retries:
                        wait_time = 2**attempt
                        self.logger.warning(
                            "Server error, retrying",
                            error=error_msg[:100],
                            wait_time=wait_time,
                            attempt=attempt,
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        self.logger.error(
                            "OAuth failed after retries", max_retries=max_retries, emoji="❌"
                        )
                        return False
                else:
                    raise

        return False

    async def automate_login(self, oauth_url: str) -> bool:
        """Automate OAuth login using flow adapter.

        Args:
            oauth_url: OAuth authorization URL

        Returns:
            True if successful, False otherwise
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            self.logger.error(
                "Playwright not installed",
                help="Run: pip install playwright && playwright install chromium",
                emoji="⚠️",
            )
            return False

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                # Execute flow using adapter
                success = await self.flow_adapter.execute_flow(page, oauth_url)

                await browser.close()
                return success

        except Exception as e:
            self.logger.error("Playwright automation error", error=str(e), emoji="❌")
            if self.debug:
                import traceback

                traceback.print_exc()
            return False

    def create_oauth_client(self, mcp_url: str) -> tuple[Client, asyncio.Task]:
        """Create OAuth client and return client + auth task.

        Args:
            mcp_url: MCP server URL

        Returns:
            (Client, auth_task) tuple
        """

        class CaptureOAuth(OAuth):
            """
            Custom OAuth handler that captures URL and callback port.
            """

            def __init__(self, adapter: "PlaywrightOAuthAdapter", *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.adapter = adapter
                self.adapter.callback_port = self.redirect_port

            async def redirect_handler(self, authorization_url: str) -> None:
                """
                Called when OAuth URL is ready.
                """
                self.adapter.oauth_url = authorization_url

        oauth = CaptureOAuth(self, mcp_url=mcp_url, client_name="MCP Test Client")
        client = Client(mcp_url, auth=oauth)
        auth_task = asyncio.create_task(client.__aenter__())

        return client, auth_task

    async def wait_for_oauth_url(self, timeout_seconds: int = 10) -> Optional[str]:
        """Wait for OAuth URL to be captured.

        Args:
            timeout_seconds: Maximum time to wait

        Returns:
            OAuth URL if captured, None otherwise
        """
        for _ in range(timeout_seconds * 2):
            await asyncio.sleep(0.5)
            if self.oauth_url:
                return self.oauth_url
        return None

    async def _trigger_callback(self, callback_url: str) -> None:
        """Send the OAuth callback directly to the local handler.

        Args:
            callback_url: OAuth callback URL with authorization code
        """
        if not callback_url:
            raise ValueError("OAuth callback URL is empty")

        if not self.callback_port:
            raise RuntimeError("OAuth callback port unknown; cannot trigger callback")

        parsed = urlparse(callback_url)
        if not parsed.query:
            raise ValueError("OAuth callback URL missing query parameters")

        params = parse_qs(parsed.query)
        if "code" not in params:
            raise ValueError("OAuth callback URL missing authorization code")

        # Build localhost callback URL
        localhost_callback = f"http://localhost:{self.callback_port}{parsed.path}"
        if parsed.query:
            localhost_callback = f"{localhost_callback}?{parsed.query}"

        # Trigger callback
        try:
            import httpx
        except ImportError:
            raise RuntimeError("httpx is required to trigger OAuth callback")

        async with httpx.AsyncClient() as client:
            response = await client.get(localhost_callback, timeout=10.0)
            response.raise_for_status()

    @property
    def last_flow_result(self):
        """
        Return the most recent FlowResult from automation.
        """
        return self._last_flow_result
