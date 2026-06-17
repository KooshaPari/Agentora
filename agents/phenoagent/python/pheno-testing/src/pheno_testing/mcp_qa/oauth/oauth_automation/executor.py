"""
Flow execution engine that drives Playwright using declarative configs.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, Optional
from urllib.parse import parse_qs, urlparse

from playwright.async_api import Page, TimeoutError

from .config import FlowStep, OAuthFlowConfig


@dataclass
class FlowResult:
    """
    Outcome information captured during a flow execution.
    """

    oauth_url: str
    success: bool = True
    callback_url: Optional[str] = None
    auth_code: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FlowContext:
    oauth_url: str
    credentials: Dict[str, str]
    mfa_code: Optional[str] = None
    mfa_provider: Optional[Callable[[], Awaitable[str]]] = None
    result: FlowResult = field(init=False)

    def __post_init__(self) -> None:
        self.result = FlowResult(oauth_url=self.oauth_url)


class FlowExecutor:
    """
    Execute configured Playwright steps with lightweight progress output.
    """

    def __init__(self, verbose: bool = True):
        self._verbose = verbose

    async def run(self, page: Page, config: OAuthFlowConfig, context: FlowContext) -> FlowResult:
        for index, step in enumerate(config.steps, start=1):
            try:
                await self._execute_step(page, step, context, index)
            except Exception as exc:  # noqa: BLE001 - we unwrap optional steps
                if step.optional:
                    if self._verbose:
                        print(f"⚠️  Optional step failed ({step.description or step.action}): {exc}")
                    continue
                context.result.success = False
                raise

        if config.post_flow_sleep:
            await asyncio.sleep(config.post_flow_sleep)

        return context.result

    async def _execute_step(
        self, page: Page, step: FlowStep, context: FlowContext, index: int
    ) -> None:
        description = step.description or step.action
        if self._verbose:
            print(f"[{index}] {description}")

        if step.action == "goto":
            await page.goto(step.value or context.oauth_url, wait_until="load")
            return

        if step.action == "sleep":
            await asyncio.sleep(float(step.value or 1))
            return

        if step.action == "wait_for_selector":
            assert step.selector, "wait_for_selector requires a selector"
            await page.wait_for_selector(step.selector, timeout=int(step.timeout * 1000))
            return

        if step.action == "fill":
            assert step.selector, "fill requires a selector"
            value = step.value
            if step.credential_key:
                value = context.credentials.get(step.credential_key)
            if value is None:
                raise KeyError(f"Missing value for credential '{step.credential_key}'")
            await page.fill(step.selector, value)
            return

        if step.action == "press":
            key = step.value
            if not key:
                raise ValueError("press action requires a value specifying the key combination")
            selector = step.selector or "body"
            await page.press(selector, key)
            return

        if step.action == "select_option":
            assert step.selector, "select_option requires a selector"
            options = step.options or ([] if step.value is None else [step.value])
            if not options:
                raise ValueError("select_option requires options or value")
            await page.select_option(step.selector, options)
            return

        if step.action == "upload_file":
            assert step.selector, "upload_file requires a selector"
            file_paths = step.file_paths or ([] if step.value is None else [step.value])
            if not file_paths:
                raise ValueError("upload_file requires file_paths or value")
            await page.set_input_files(step.selector, file_paths)
            return

        if step.action == "wait_for_url":
            if step.value:
                await page.wait_for_url(step.value, timeout=int(step.timeout * 1000))
                return
            if step.url_substring:
                await self._wait_for_url_substring(page, step.url_substring, step.timeout)
                return
            raise ValueError("wait_for_url requires 'value' or 'url_substring'")

        if step.action == "assert_url_contains":
            substring = step.value or step.url_substring
            if not substring:
                raise ValueError("assert_url_contains requires 'value' or 'url_substring'")
            if substring not in page.url:
                raise AssertionError(
                    f"Expected current URL to contain '{substring}', got '{page.url}'"
                )
            return

        if step.action == "evaluate":
            if step.javascript:
                await page.evaluate(step.javascript)
                return
            if step.selector and step.value:
                await page.eval_on_selector(step.selector, step.value)
                return
            raise ValueError("evaluate action requires 'javascript' or both 'selector' and 'value'")

        if step.action == "capture_url":
            await self._capture_url(page, step, context)
            return

        if step.action == "handle_mfa":
            await self._handle_mfa(page, step, context)
            return

        if step.action == "click":
            assert step.selector, "click requires a selector"
            try:
                await page.wait_for_selector(step.selector, timeout=int(step.timeout * 1000))
            except TimeoutError:
                if step.optional:
                    return
                raise

            if step.expect_navigation:
                await asyncio.gather(
                    page.wait_for_load_state("networkidle"),
                    page.click(step.selector),
                )
            else:
                await page.click(step.selector)

            if step.wait_for_selector:
                try:
                    await page.wait_for_selector(
                        step.wait_for_selector, timeout=int(step.timeout * 1000)
                    )
                except TimeoutError:
                    if not step.optional:
                        raise
            return

        raise ValueError(f"Unsupported action: {step.action}")

    async def _wait_for_url_substring(self, page: Page, substring: str, timeout: float) -> None:
        """
        Poll until the page URL contains the desired substring.
        """

        remaining = max(timeout, 0)
        poll_interval = 0.2
        while remaining > 0:
            if substring in page.url:
                return
            await asyncio.sleep(poll_interval)
            remaining -= poll_interval
        raise TimeoutError(f"Timed out waiting for URL to contain '{substring}'")

    async def _capture_url(self, page: Page, step: FlowStep, context: FlowContext) -> None:
        value = page.url
        if step.url_substring and step.url_substring not in value:
            raise AssertionError(
                f"Expected captured URL to contain '{step.url_substring}', got '{value}'"
            )

        key = step.store_key or "captured_url"
        context.result.metadata[key] = value

        parsed = urlparse(value)
        if parsed.scheme and parsed.netloc:
            context.result.callback_url = value

        if step.query_param:
            params = parse_qs(parsed.query)
            if step.query_param in params and params[step.query_param]:
                param_value = params[step.query_param][0]
                context.result.metadata[f"{key}_{step.query_param}"] = param_value
                if step.query_param == "code":
                    context.result.auth_code = param_value

    async def _handle_mfa(self, page: Page, step: FlowStep, context: FlowContext) -> None:
        code: Optional[str] = None
        if step.credential_key and step.credential_key in context.credentials:
            code = context.credentials[step.credential_key]
        if not code and context.mfa_code:
            code = context.mfa_code
        if not code and context.mfa_provider:
            code = await context.mfa_provider()
        if not code and step.value:
            code = step.value
        if not code:
            raise ValueError(
                "handle_mfa requires an MFA code via credential, context, or step value"
            )

        selector = step.selector or "input[type='text']"
        await page.fill(selector, code)
        if step.wait_for_selector:
            await page.wait_for_selector(step.wait_for_selector, timeout=int(step.timeout * 1000))
