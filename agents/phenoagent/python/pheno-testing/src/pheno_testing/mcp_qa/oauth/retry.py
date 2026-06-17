"""Retry-aware OAuth helpers for MCP QA workflows.

Provides:
- `RetryConfig` tuning for exponential backoff behaviour
- `EnhancedCredentialBroker` for resilient credential acquisition
- `RetryOAuthAdapter` drop-in wrapper around Playwright automation
- `create_retry_oauth_client` convenience coroutine

Designed to be project-agnostic so Zen MCP and other apps can import
these utilities from `mcp_qa.oauth.retry`.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Optional, Tuple

import httpx
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from ..logging import get_logger
from .playwright_adapter import PlaywrightOAuthAdapter

logger = get_logger("mcp_qa.oauth.retry")


@dataclass
class RetryConfig:
    """Configuration values controlling retry behaviour.

    Note: This is maintained for backward compatibility.
    Consider using mcp_qa.utils.http_retry.HTTPRetryConfig for new code.
    """

    max_retries: int = 5
    initial_backoff: float = 2.0
    max_backoff: float = 60.0
    backoff_multiplier: float = 2.0
    server_startup_wait: float = 120.0
    retryable_status_codes: tuple[int, ...] = (500, 502, 503, 504, 530)  # Added 500
    retryable_exceptions: tuple[type[Exception], ...] = (
        httpx.ConnectError,
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
        httpx.RemoteProtocolError,
        httpx.NetworkError,  # Added NetworkError
    )


class EnhancedCredentialBroker:
    """
    Credential broker that adds exponential backoff retry semantics.
    """

    def __init__(
        self,
        endpoint: str,
        *,
        provider: str = "authkit",
        retry_config: Optional[RetryConfig] = None,
        verbose: bool = True,
    ) -> None:
        self.endpoint = endpoint
        self.provider = provider
        self.retry_config = retry_config or RetryConfig()
        self.verbose = verbose
        self._client: Optional[httpx.AsyncClient] = None

    async def get_authenticated_client(self) -> Any:
        """
        Run the authentication flow with retries and return the client.
        """

        async def attempt() -> Any:
            raise NotImplementedError("Subclass must implement _attempt_authentication")

        return await self._retry_with_backoff(attempt, operation="authentication")

    async def _retry_with_backoff(
        self,
        operation_func,
        *,
        operation: str = "operation",
        **kwargs,
    ) -> Any:
        """
        Execute `operation_func` with exponential backoff.
        """

        last_error: Optional[Exception] = None
        backoff = self.retry_config.initial_backoff

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            transient=True,
        ) as progress:
            task = progress.add_task(
                f"⏳ Waiting for {operation}...",
                total=self.retry_config.max_retries,
            )

            for attempt in range(1, self.retry_config.max_retries + 1):
                try:
                    if self.verbose:
                        logger.info(
                            "%s attempt %s/%s",
                            operation.capitalize(),
                            attempt,
                            self.retry_config.max_retries,
                        )

                    result = await operation_func(**kwargs)

                    if self.verbose:
                        logger.info("%s successful", operation.capitalize())

                    progress.update(task, completed=self.retry_config.max_retries)
                    return result

                except httpx.HTTPStatusError as err:
                    last_error = err
                    status = err.response.status_code

                    if (
                        status in self.retry_config.retryable_status_codes
                        and attempt < self.retry_config.max_retries
                    ):
                        wait_time = min(backoff, self.retry_config.max_backoff)

                        # Special messaging for CloudFlare 530 errors
                        if status == 530:
                            if self.verbose:
                                logger.warning(
                                    "CloudFlare tunnel unreachable (530): %s",
                                    err.response.text[:100],
                                )
                                logger.info(
                                    "CloudFlare tunnel unreachable, retrying in %.1fs (attempt %s/%s)",
                                    wait_time,
                                    attempt,
                                    self.retry_config.max_retries,
                                )
                            progress.update(
                                task,
                                description=f"⏳ CloudFlare tunnel unreachable (530), retrying in {wait_time:.1f}s...",
                                completed=attempt,
                            )
                        else:
                            if self.verbose:
                                logger.warning(
                                    "Server error %s: %s", status, err.response.text[:100]
                                )
                                logger.info(
                                    "Retrying in %.1fs (attempt %s/%s)",
                                    wait_time,
                                    attempt,
                                    self.retry_config.max_retries,
                                )
                            progress.update(
                                task,
                                description=f"⏳ Server error {status}, retrying in {wait_time:.1f}s...",
                                completed=attempt,
                            )

                        await asyncio.sleep(wait_time)
                        backoff *= self.retry_config.backoff_multiplier
                        continue

                    if self.verbose:
                        logger.error("%s failed with status %s", operation.capitalize(), status)
                    raise

                except self.retry_config.retryable_exceptions as err:
                    last_error = err
                    if attempt < self.retry_config.max_retries:
                        wait_time = min(backoff, self.retry_config.max_backoff)
                        if self.verbose:
                            logger.warning("Connection error: %s", type(err).__name__)
                            logger.info(
                                "Retrying in %.1fs (attempt %s/%s)",
                                wait_time,
                                attempt,
                                self.retry_config.max_retries,
                            )
                        progress.update(
                            task,
                            description=f"⏳ Connection error, retrying in {wait_time:.1f}s...",
                            completed=attempt,
                        )
                        await asyncio.sleep(wait_time)
                        backoff *= self.retry_config.backoff_multiplier
                        continue

                    if self.verbose:
                        logger.error(
                            "%s failed after %s attempts",
                            operation.capitalize(),
                            self.retry_config.max_retries,
                        )
                    raise

                except Exception as err:  # pylint: disable=broad-except
                    last_error = err
                    if self.verbose:
                        logger.error("%s failed: %s", operation.capitalize(), err)
                    raise

                finally:
                    progress.update(task, completed=attempt)

            progress.update(
                task,
                description=f"✗ {operation.capitalize()} failed after {self.retry_config.max_retries} attempts",
            )

            if last_error:
                raise last_error
            raise RuntimeError(
                f"{operation.capitalize()} failed after {self.retry_config.max_retries} attempts"
            )

    async def wait_for_server_ready(
        self,
        *,
        health_endpoint: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> bool:
        """
        Poll the server health endpoint until ready or timeout.
        """

        health_url = health_endpoint or f"{self.endpoint.rstrip('/mcp')}/healthz"
        timeout = timeout or self.retry_config.server_startup_wait

        if self.verbose:
            logger.info("Waiting for server at %s", health_url)

        start_time = asyncio.get_event_loop().time()
        check_interval = 2.0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            transient=True,
        ) as progress:
            task = progress.add_task(
                "⏳ Waiting for server to start...",
                total=int(timeout / check_interval) if timeout else None,
            )

            attempt = 0
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        response = await client.get(health_url)
                        if response.status_code < 500:
                            if self.verbose:
                                logger.info("Server is ready (status %s)", response.status_code)
                            progress.update(task, description="✅ Server ready!")
                            return True
                except (httpx.ConnectError, httpx.ConnectTimeout):
                    pass
                except Exception as err:  # pylint: disable=broad-except
                    if self.verbose:
                        logger.debug("Health check error: %s", err)

                attempt += 1
                elapsed = asyncio.get_event_loop().time() - start_time
                progress.update(
                    task,
                    description=f"⏳ Waiting for server... ({elapsed:.0f}s / {timeout:.0f}s)",
                    completed=attempt,
                )
                await asyncio.sleep(check_interval)

            if self.verbose:
                logger.warning("Server did not respond after %.0fs", timeout)
            progress.update(task, description=f"⚠️  Server not ready after {timeout}s")
            return False

    async def close(self) -> None:
        """
        Close any cached HTTP client.
        """
        if self._client:
            await self._client.aclose()
            self._client = None


class RetryOAuthAdapter:
    """
    Wrapper around `PlaywrightOAuthAdapter` adding retry semantics.
    """

    def __init__(
        self,
        *,
        email: str,
        password: str,
        max_retries: int = 5,
        initial_backoff: float = 2.0,
        server_startup_wait: float = 120.0,
        verbose: bool = True,
    ) -> None:
        self.email = email
        self.password = password
        self.verbose = verbose
        self.retry_config = RetryConfig(
            max_retries=max_retries,
            initial_backoff=initial_backoff,
            server_startup_wait=server_startup_wait,
        )
        self.base_adapter = PlaywrightOAuthAdapter(email, password)

    def create_oauth_client(
        self,
        endpoint: str,
        *,
        wait_for_server: bool = True,
    ) -> Tuple[Any, asyncio.Task]:
        """
        Create client and authentication task with retry handling.
        """

        client, base_auth_task = self.base_adapter.create_oauth_client(endpoint)

        enhanced_auth_task = asyncio.create_task(
            self._enhanced_auth_flow(
                endpoint=endpoint,
                base_auth_task=base_auth_task,
                wait_for_server=wait_for_server,
            )
        )

        return client, enhanced_auth_task

    async def _enhanced_auth_flow(
        self,
        *,
        endpoint: str,
        base_auth_task: asyncio.Task,
        wait_for_server: bool,
    ) -> None:
        broker = EnhancedCredentialBroker(
            endpoint=endpoint,
            retry_config=self.retry_config,
            verbose=self.verbose,
        )

        try:
            if wait_for_server:
                if self.verbose:
                    logger.info("Checking if server is ready before authentication")
                server_ready = await broker.wait_for_server_ready()
                if not server_ready:
                    logger.warning("Server may not be fully ready; continuing regardless")

            await self._retry_auth_task(auth_task=base_auth_task, broker=broker)

            if self.verbose:
                logger.info("OAuth authentication successful")
        finally:
            await broker.close()

    async def _retry_auth_task(
        self, *, auth_task: asyncio.Task, broker: EnhancedCredentialBroker
    ) -> None:
        last_error: Optional[Exception] = None
        backoff = broker.retry_config.initial_backoff

        for attempt in range(1, broker.retry_config.max_retries + 1):
            try:
                if self.verbose and attempt > 1:
                    logger.info(
                        "Authentication attempt %s/%s",
                        attempt,
                        broker.retry_config.max_retries,
                    )

                await auth_task
                return

            except Exception as err:  # pylint: disable=broad-except
                last_error = err
                error_msg = str(err)
                is_retryable = any(code in error_msg for code in ("502", "503", "504", "530"))

                if is_retryable and attempt < broker.retry_config.max_retries:
                    wait_time = min(backoff, broker.retry_config.max_backoff)
                    if self.verbose:
                        logger.warning("Server error during auth: %s", error_msg[:100])
                        logger.info(
                            "Retrying in %.1fs (attempt %s/%s)",
                            wait_time,
                            attempt,
                            broker.retry_config.max_retries,
                        )
                    await asyncio.sleep(wait_time)
                    backoff *= broker.retry_config.backoff_multiplier

                    _, auth_task = self.base_adapter.create_oauth_client(broker.endpoint)
                    continue

                if self.verbose:
                    logger.error("Authentication failed: %s", error_msg)
                raise

        if last_error:
            raise last_error
        raise RuntimeError(
            f"Authentication failed after {broker.retry_config.max_retries} attempts"
        )


def create_retry_oauth_client(
    *,
    endpoint: str,
    email: str,
    password: str,
    max_retries: int = 5,
    wait_for_server: bool = True,
    verbose: bool = True,
) -> Tuple[Any, asyncio.Task]:
    """
    Convenience helper returning client plus retry-aware auth task.
    """

    adapter = RetryOAuthAdapter(
        email=email,
        password=password,
        max_retries=max_retries,
        verbose=verbose,
    )

    return adapter.create_oauth_client(endpoint=endpoint, wait_for_server=wait_for_server)


__all__ = [
    "RetryConfig",
    "EnhancedCredentialBroker",
    "RetryOAuthAdapter",
    "create_retry_oauth_client",
]
