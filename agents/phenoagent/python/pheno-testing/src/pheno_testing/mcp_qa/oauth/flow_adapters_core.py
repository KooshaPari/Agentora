"""OAuth Flow Adapters - Core Module.

This module provides the base classes and configuration for OAuth flows.
"""

import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

from pheno.testing.mcp_qa.logging import get_logger

if TYPE_CHECKING:
    from pheno.testing.mcp_qa.oauth.granular_progress import GranularOAuthProgress


class InvalidCredentialsError(Exception):
    """Raised when invalid login credentials are detected."""

    pass


@dataclass
class FlowConfig:
    """Configuration for an OAuth flow."""

    name: str
    selectors: Dict[str, str]
    steps: list[str]
    timing: Dict[str, float] = None
    options: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.timing is None:
            self.timing = {
                "page_load": 2.0,
                "input_fill": 0.3,
                "button_click": 1.0,
                "navigation": 3.0,
                "allow_enable": 1.0,
            }


class OAuthFlowAdapter(ABC):
    """Base class for OAuth flow adapters."""

    def __init__(self, email: str, password: str, debug: bool = False):
        self.email = email
        self.password = password
        self.debug = debug
        self.debug_dir = Path.cwd() / ".oauth_debug"
        if debug:
            self.debug_dir.mkdir(exist_ok=True)
        self._last_url_before_signin: Optional[str] = None
        self._last_url_after_signin: Optional[str] = None
        self.logger = get_logger(__name__).bind(email=email, debug=debug)
        self._progress_tracker: Optional["GranularOAuthProgress"] = None

    def set_progress_tracker(self, progress: "GranularOAuthProgress"):
        """Set progress tracker for granular step updates."""
        self._progress_tracker = progress

    @abstractmethod
    def get_config(self) -> FlowConfig:
        """Return the flow configuration."""
        pass

    def _sanitize_text(self, text: Optional[str]) -> Optional[str]:
        """Mask sensitive values such as email/password before logging."""
        if not text:
            return text
        sanitized = text
        if self.email:
            sanitized = sanitized.replace(self.email, "***EMAIL***")
        if self.password:
            sanitized = sanitized.replace(self.password, "***PASSWORD***")
        return sanitized

    async def dump_page_state(self, page, step_name: str, error: Optional[Exception] = None):
        """Dump page HTML, accessibility tree, and optional screenshot for debugging."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = f"{step_name}_{timestamp}"

        html_content: Optional[str] = None
        sanitized_html: Optional[str] = None
        accessibility_snapshot: Optional[str] = None

        try:
            html_content = await page.content()
            sanitized_html = self._sanitize_text(html_content)
        except Exception as exc:
            self.logger.warning("Unable to capture HTML content", error=str(exc), emoji="⚠️")

        try:
            tree = await page.accessibility.snapshot()
            if tree:
                accessibility_snapshot = self._sanitize_text(json.dumps(tree, indent=2))
        except Exception as exc:
            self.logger.debug("Accessibility snapshot failed", error=str(exc), emoji="⚠️")

        dump_dir = self.debug_dir
        dump_dir.mkdir(exist_ok=True)

        if sanitized_html:
            html_file = dump_dir / f"{prefix}.html"
            try:
                html_file.write_text(sanitized_html)
                self.logger.debug("OAuth HTML dump saved", file=str(html_file), emoji="📄")
            except Exception as exc:
                self.logger.debug("Failed to write HTML dump", error=str(exc), emoji="⚠️")

            preview = sanitized_html[:2000]
            if preview:
                self.logger.debug("HTML preview (first 2000 chars)", preview=preview, emoji="📄")

        if accessibility_snapshot:
            tree_file = dump_dir / f"{prefix}_tree.json"
            try:
                tree_file.write_text(accessibility_snapshot)
                self.logger.debug("Accessibility tree saved", file=str(tree_file), emoji="🌳")
            except Exception as exc:
                self.logger.debug("Failed to write accessibility tree", error=str(exc), emoji="⚠️")

            tree_preview = accessibility_snapshot[:2000]
            if tree_preview:
                self.logger.debug(
                    "Accessibility preview (first 2000 chars)",
                    preview=tree_preview,
                    emoji="🌳",
                )

        try:
            info_lines = [f"URL: {page.url}"]
            if error:
                info_lines.append(f"Error: {self._sanitize_text(str(error))}")
            info_file = dump_dir / f"{prefix}_info.txt"
            info_file.write_text("\n".join(info_lines))
            self.logger.debug("Context saved", file=str(info_file), emoji="🔗")
        except Exception as exc:
            self.logger.debug("Failed to write context info", error=str(exc), emoji="⚠️")

        if self.debug:
            try:
                screenshot_file = dump_dir / f"{prefix}.png"
                await page.screenshot(path=str(screenshot_file))
                self.logger.debug("Screenshot saved", file=str(screenshot_file), emoji="📸")
            except Exception as exc:
                self.logger.debug("Screenshot capture failed", error=str(exc), emoji="⚠️")

    async def wait_for_selector_safe(
        self, page, selector: str, timeout: float = 5000, step_name: str = "unknown"
    ) -> bool:
        """Wait for selector with debug dumping on failure.

        Returns:
            True if selector found, False otherwise
        """
        try:
            await page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception as e:
            self.logger.debug("Selector not found", selector=selector, step=step_name, emoji="⚠️")
            await self.dump_page_state(page, f"selector_not_found_{step_name}", e)
            return False

    async def execute_flow(self, page, oauth_url: str) -> bool:
        """Execute the OAuth flow.

        Args:
            page: Playwright page object
            oauth_url: OAuth authorization URL

        Returns:
            True if successful, False otherwise
        """
        config = self.get_config()

        if self._progress_tracker:
            from pheno.testing.mcp_qa.oauth.granular_progress import OAuthSteps

            self._progress_tracker.add_step(*OAuthSteps.NAVIGATE_LOGIN)
            self._progress_tracker.start_step("navigate_login")

        await page.goto(oauth_url, wait_until="networkidle")
        await asyncio.sleep(config.timing["page_load"])

        if self._progress_tracker:
            self._progress_tracker.complete_step("navigate_login")

        if self.debug:
            await self.dump_page_state(page, "initial_load")

        for step in config.steps:
            try:
                if self._progress_tracker:
                    step_description = self._get_step_description(step)
                    if step_description:
                        step_id, desc = step_description
                        self._progress_tracker.add_step(step_id, desc)
                        self._progress_tracker.start_step(step_id)

                if step == "fill_email":
                    await self._fill_email(page, config)
                elif step == "click_continue_if_present":
                    await self._click_continue_if_present(page, config)
                elif step == "fill_password":
                    await self._fill_password(page, config)
                elif step == "click_signin":
                    await self._click_signin(page, config)
                elif step == "verify_login_transition":
                    if not await self._verify_login_transition(page, config):
                        if self._progress_tracker:
                            step_description = self._get_step_description(step)
                            if step_description:
                                self._progress_tracker.complete_step(
                                    step_description[0],
                                    error="Login verification failed",
                                )
                        return False
                elif step == "click_allow":
                    await self._click_allow(page, config)
                elif step == "third_party_auth":
                    await self._third_party_auth(page, config)
                else:
                    self.logger.warning("Unknown step", step=step, emoji="⚠️")

                if self._progress_tracker:
                    step_description = self._get_step_description(step)
                    if step_description:
                        self._progress_tracker.complete_step(step_description[0])

            except Exception as e:
                self.logger.error("Step failed", step=step, error=str(e), emoji="❌")
                await self.dump_page_state(page, f"step_failed_{step}", e)

                if self._progress_tracker:
                    step_description = self._get_step_description(step)
                    if step_description:
                        self._progress_tracker.complete_step(step_description[0], error=str(e))
                return False

        return True

    def _get_step_description(self, step: str) -> Optional[tuple[str, str]]:
        """Get progress step ID and description for a flow step."""
        from pheno.testing.mcp_qa.oauth.granular_progress import OAuthSteps

        step_map = {
            "fill_email": OAuthSteps.ENTER_EMAIL,
            "fill_password": OAuthSteps.ENTER_PASSWORD,
            "click_continue": OAuthSteps.CLICK_CONTINUE,
            "click_continue_if_present": OAuthSteps.CLICK_CONTINUE,
            "click_signin": OAuthSteps.CLICK_SIGNIN,
            "click_allow": OAuthSteps.CLICK_ALLOW,
            "verify_login_transition": ("verify_login", "Verifying login transition"),
            "third_party_auth": (
                "third_party_auth",
                "Completing third-party authentication",
            ),
        }
        return step_map.get(step)

    async def _fill_email(self, page, config: FlowConfig):
        """Fill email field."""
        selector = config.selectors.get("email", "#email")

        if await self.wait_for_selector_safe(page, selector, timeout=2000, step_name="fill_email"):
            await page.fill(selector, self.email)
            await asyncio.sleep(config.timing["input_fill"])
            return

        fallback_selectors = [
            'input[type="email"]',
            'input[name="email"]',
            'input[placeholder*="email" i]',
            'input[aria-label*="email" i]',
        ]

        for fallback in fallback_selectors:
            try:
                element = await page.query_selector(fallback)
                if element and await element.is_visible():
                    await page.fill(fallback, self.email)
                    await asyncio.sleep(config.timing["input_fill"])
                    self.logger.debug(f"Filled email using fallback selector: {fallback}")
                    return
            except Exception:
                continue

        self.logger.warning("Could not find email field with any selector", emoji="⚠️")

    async def _fill_password(self, page, config: FlowConfig):
        """Fill password field."""
        selector = config.selectors.get("password", "#password")

        if await self.wait_for_selector_safe(
            page, selector, timeout=2000, step_name="fill_password"
        ):
            await page.fill(selector, self.password)
            await asyncio.sleep(config.timing["input_fill"])
            return

        fallback_selectors = [
            'input[type="password"]',
            'input[name="password"]',
            'input[placeholder*="password" i]',
            'input[aria-label*="password" i]',
        ]

        for fallback in fallback_selectors:
            try:
                element = await page.query_selector(fallback)
                if element and await element.is_visible():
                    await page.fill(fallback, self.password)
                    await asyncio.sleep(config.timing["input_fill"])
                    self.logger.debug(f"Filled password using fallback selector: {fallback}")
                    return
            except Exception:
                continue

        self.logger.warning("Could not find password field with any selector", emoji="⚠️")

    async def _click_signin(self, page, config: FlowConfig):
        """Click sign in button."""
        selector = config.selectors.get("signin_button", 'button[type="submit"]')
        if await self.wait_for_selector_safe(page, selector, step_name="click_signin"):
            self._last_url_before_signin = page.url
            await page.click(selector)
            await page.wait_for_load_state("networkidle", timeout=10000)
            await asyncio.sleep(config.timing["navigation"])
            self._last_url_after_signin = page.url

    async def _verify_login_transition(self, page, config: FlowConfig) -> bool:
        """Allow adapters to verify that the login submit advanced the flow."""
        return True

    async def _click_allow(self, page, config: FlowConfig):
        """Click allow/consent button."""
        selector = config.selectors.get(
            "allow_button",
            (
                "button:has-text('Allow access'), "
                "button:has-text('Allow Access'), "
                "button:has-text('Allow'), button:has-text('Authorize'), "
                "button:has-text('Continue'), button[value='approve'][type='submit']"
            ),
        )
        options = config.options or {}
        consent_mode = str(options.get("consent_mode", "required")).lower()
        optional_timeout = int(options.get("allow_optional_timeout", 5000))
        enabled_timeout = int(options.get("allow_enabled_timeout", max(optional_timeout, 10000)))

        if consent_mode == "skip":
            if self.debug:
                print("Skipping consent step (consent_mode=skip).")
            return

        if consent_mode == "optional":
            try:
                await page.wait_for_selector(selector, timeout=optional_timeout)
            except Exception:
                if self.debug:
                    print("Consent button not found; continuing because consent is optional.")
                return
        else:
            if not await self.wait_for_selector_safe(
                page,
                selector,
                timeout=max(optional_timeout, 15000),
                step_name="click_allow_wait",
            ):
                return

        enabled_selector = f"{selector}:not([disabled])"
        await asyncio.sleep(config.timing["allow_enable"])

        if consent_mode == "optional":
            try:
                await page.wait_for_selector(enabled_selector, timeout=enabled_timeout)
            except Exception:
                if self.debug:
                    print("Consent button never enabled; continuing because consent is optional.")
                return
        else:
            if not await self.wait_for_selector_safe(
                page,
                enabled_selector,
                timeout=enabled_timeout,
                step_name="click_allow_enabled",
            ):
                return

        await page.click(selector)
        await asyncio.sleep(config.timing["navigation"] + 2)

    async def _click_continue_if_present(self, page, config: FlowConfig):
        """Click 'Continue' button if present (for two-step login forms)."""
        selector = config.selectors.get("continue_button", "button:has-text('Continue')")

        try:
            element = await page.wait_for_selector(selector, timeout=2000)
            if element and await element.is_visible():
                self.logger.debug("Found Continue button, clicking...", emoji="👆")
                await page.click(selector)
                await asyncio.sleep(config.timing.get("navigation", 2.0))
                self.logger.debug("Clicked Continue, waiting for password field")
        except Exception:
            self.logger.debug("No Continue button found, proceeding...")

    async def _third_party_auth(self, page, config: FlowConfig):
        """Handle third-party authentication (Google, GitHub, etc.)."""
        pass
