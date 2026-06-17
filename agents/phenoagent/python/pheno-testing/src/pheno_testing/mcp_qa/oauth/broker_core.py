"""Unified Credential Broker Core.

Provides the main UnifiedCredentialBroker class and CapturedCredentials dataclass.
"""

import asyncio
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from fastmcp import Client

from pheno.testing.mcp_qa.auth.credential_manager import (
    CredentialManager,
    CredentialType,
    get_credential_manager,
)
from pheno.testing.mcp_qa.logging import get_logger
from pheno.testing.mcp_qa.oauth.granular_progress import (
    GranularOAuthProgress,
    OAuthSteps,
)
from pheno.testing.mcp_qa.oauth.broker_providers import (
    CaptureOAuth,
)
from pheno.testing.mcp_qa.oauth.broker_cache import (
    BrokerCache,
    SessionState,
)

try:
    from rich.console import Console

    HAS_RICH = True
except ImportError:
    HAS_RICH = False


@dataclass
class CapturedCredentials:
    """Credentials captured during OAuth flow."""

    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    email: Optional[str] = None
    password: Optional[str] = None
    session_id: Optional[str] = None
    provider: str = "authkit"
    mcp_endpoint: str = ""

    def is_valid(self) -> bool:
        """Check if credentials are still valid."""
        if not self.access_token:
            return False
        if self.access_token in ("captured_from_oauth", "placeholder", "TODO"):
            return False
        if self.expires_at and datetime.now() >= self.expires_at:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for serialization."""
        data = asdict(self)
        if self.expires_at:
            data["expires_at"] = self.expires_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CapturedCredentials":
        """Create from dict."""
        if "expires_at" in data and data["expires_at"]:
            data["expires_at"] = datetime.fromisoformat(data["expires_at"])
        return cls(**data)


class OAuthProgress:
    """DEPRECATED: Legacy OAuth progress wrapper.

    This class is maintained for backward compatibility but uses the new
    GranularOAuthProgress internally.
    """

    def __init__(self):
        self.granular_progress = GranularOAuthProgress()
        self._started = False

    def update(self, message: str, step: Optional[int] = None):
        """Update progress with message."""
        if not self._started:
            self.granular_progress.start()
            self._started = True
        if self.granular_progress.steps:
            last_step = self.granular_progress.steps[-1]
            self.granular_progress.update_step_description(last_step.id, message)
        else:
            step_id = f"step_{len(self.granular_progress.steps)}"
            self.granular_progress.add_step(step_id, message)
            self.granular_progress.start_step(step_id)

    def advance(self, message: str):
        """Advance to next step."""
        if not self._started:
            self.granular_progress.start()
            self._started = True
        if self.granular_progress.steps:
            last_step = self.granular_progress.steps[-1]
            if last_step.status.value == "in_progress":
                self.granular_progress.complete_step(last_step.id)
        step_id = f"step_{len(self.granular_progress.steps)}"
        self.granular_progress.add_step(step_id, message)
        self.granular_progress.start_step(step_id)

    def complete(self, message: str):
        """Complete progress with success message."""
        if self.granular_progress.steps:
            last_step = self.granular_progress.steps[-1]
            if last_step.status.value == "in_progress":
                self.granular_progress.complete_step(last_step.id)
        self.granular_progress.complete(message)

    def error(self, message: str):
        """Show error and stop progress."""
        self.granular_progress.error(message)

    def stop(self):
        """Stop progress display."""
        if self.granular_progress.live:
            self.granular_progress.live.stop()


class UnifiedCredentialBroker:
    """Unified credential broker that handles the complete OAuth flow.

    Features:
    - Interactive credential prompts
    - Playwright OAuth automation
    - Inline progress display
    - Credential caching in .env
    - Token capture for direct HTTP calls
    - Session-wide authentication (one auth per endpoint per session)
    """

    _session_authenticated: Dict[str, bool] = {}
    _session_credentials: Dict[str, CapturedCredentials] = {}
    _session_lock = asyncio.Lock()

    def __init__(
        self,
        mcp_endpoint: Optional[str] = None,
        provider: str = "authkit",
        debug: bool = False,
    ):
        self.mcp_endpoint = mcp_endpoint or os.getenv(
            "MCP_ENDPOINT", "https://mcp.atoms.tech/api/mcp"
        )
        self.provider = provider
        self.debug = debug or os.getenv("OAUTH_DEBUG", "").lower() in ("1", "true", "yes")
        self.env_file = Path.cwd() / ".env"
        self.cache_file = Path.home() / ".atoms_mcp_test_cache" / "credentials.json"
        self.cache_file.parent.mkdir(exist_ok=True)

        self._credentials: Optional[CapturedCredentials] = None
        self._client: Optional[Client] = None
        self._oauth_url: Optional[str] = None
        self._callback_port: Optional[int] = None
        self._credential_manager: Optional[CredentialManager] = None
        self._cache: Optional[BrokerCache] = None
        self._session_state: Optional[SessionState] = None
        self.logger = get_logger(__name__).bind(provider=provider)

    @property
    def cache(self) -> BrokerCache:
        """Lazy-load the broker cache."""
        if self._cache is None:
            self._cache = BrokerCache(self.cache_file)
        return self._cache

    @property
    def session_state(self) -> SessionState:
        """Lazy-load session state."""
        if self._session_state is None:
            self._session_state = SessionState()
        return self._session_state

    def _load_credentials_from_env(self) -> Optional[Dict[str, str]]:
        """Load credentials from .env file."""
        if not self.env_file.exists():
            alternate_env = Path.home() / ".mcp_qa" / ".env"
            if alternate_env.exists():
                self.env_file = alternate_env
            else:
                return None

        creds = {}
        with open(self.env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    creds[key] = value

        for key, value in creds.items():
            if key not in os.environ:
                os.environ[key] = value

        return creds

    def _get_credential_manager(self) -> Optional[CredentialManager]:
        """Lazy-load the shared credential manager."""
        if self._credential_manager is not None:
            return self._credential_manager

        try:
            self._credential_manager = get_credential_manager()
        except Exception as exc:
            self.logger.warning("Credential manager unavailable", error=str(exc))
            self._credential_manager = None

        return self._credential_manager

    def _load_from_secret_manager(
        self,
        manager: CredentialManager,
    ) -> Optional[Tuple[str, str]]:
        """Attempt to fetch provider credentials from the secure store."""
        credentials = manager.get_credentials_by_provider(self.provider)

        prioritized = []
        fallbacks = []
        for credential in credentials:
            if credential.credential_type != CredentialType.PASSWORD:
                continue
            if not credential.value:
                continue
            metadata = credential.metadata or {}
            source = metadata.get("source")
            if credential.email and source in {"env", "oauth_broker"}:
                prioritized.append(credential)
            else:
                fallbacks.append(credential)

        for credential in prioritized + fallbacks:
            email = credential.email
            if not email:
                continue
            self.logger.info(
                "Using credentials from secure store",
                credential_name=credential.name,
                emoji="🔐",
            )
            return email, credential.value

        return None

    def _persist_to_secret_manager(
        self,
        manager: CredentialManager,
        email: str,
        password: str,
    ) -> None:
        """Store or update credentials in the secure manager for future runs."""
        name = f"{self.provider}_{self._sanitize_identifier(email)}_login"
        metadata = {"source": "oauth_broker", "provider": self.provider}

        existing = manager.get_credential(name)
        if existing:
            update_kwargs: Dict[str, Any] = {}
            if existing.value != password:
                update_kwargs["value"] = password
            if email and existing.email != email:
                update_kwargs["email"] = email

            combined_metadata = existing.metadata.copy() if existing.metadata else {}
            metadata_changed = False
            for key, value in metadata.items():
                if combined_metadata.get(key) != value:
                    combined_metadata[key] = value
                    metadata_changed = True
            if metadata_changed:
                update_kwargs["metadata"] = combined_metadata

            if update_kwargs:
                manager.update_credential(name, **update_kwargs)
        else:
            manager.store_credential(
                name=name,
                credential_type=CredentialType.PASSWORD,
                provider=self.provider,
                value=password,
                email=email,
                metadata=metadata,
            )

    @staticmethod
    def _sanitize_identifier(value: Optional[str]) -> str:
        """Sanitize user-provided identifiers for credential naming."""
        if not value:
            return "default"
        return "".join(ch.lower() if ch.isalnum() else "_" for ch in value)

    def _save_credentials_to_env(self, email: str, password: str):
        """Save credentials to .env file."""
        existing_lines = []
        if self.env_file.exists():
            with open(self.env_file, "r") as f:
                existing_lines = f.readlines()

        updated = False
        password_updated = False
        new_lines = []

        for line in existing_lines:
            stripped = line.strip()
            if stripped.startswith("ATOMS_TEST_EMAIL=") or stripped.startswith("ZEN_TEST_EMAIL="):
                new_lines.append(f"ATOMS_TEST_EMAIL={email}\n")
                updated = True
            elif stripped.startswith("ATOMS_TEST_PASSWORD=") or stripped.startswith(
                "ZEN_TEST_PASSWORD="
            ):
                new_lines.append(f"ATOMS_TEST_PASSWORD={password}\n")
                password_updated = True
            else:
                new_lines.append(line)

        if not updated:
            new_lines.append(f"ATOMS_TEST_EMAIL={email}\n")
        if not password_updated:
            new_lines.append(f"ATOMS_TEST_PASSWORD={password}\n")

        with open(self.env_file, "w") as f:
            f.writelines(new_lines)

        self.logger.info("Credentials saved to .env", env_file=str(self.env_file), emoji="✅")

    def _prompt_for_credentials(self) -> Tuple[str, str]:
        """Retrieve credentials from secure store, environment, or prompt."""
        env_creds = self._load_credentials_from_env() or {}
        manager = self._get_credential_manager()

        if manager:
            stored = self._load_from_secret_manager(manager)
            if stored:
                return stored

        email_keys = ["ATOMS_TEST_EMAIL", "ZEN_TEST_EMAIL", "TEST_EMAIL", "MCP_EMAIL"]
        password_keys = [
            "ATOMS_TEST_PASSWORD",
            "ZEN_TEST_PASSWORD",
            "TEST_PASSWORD",
            "MCP_PASSWORD",
        ]

        email = None
        password = None

        if env_creds:
            for key in email_keys:
                value = env_creds.get(key)
                if value:
                    email = value
                    self.logger.info("Using email from .env", key=key, email=value, emoji="📧")
                    break

        if not email:
            email = input("📧 Enter email: ").strip()

        if env_creds:
            for key in password_keys:
                value = env_creds.get(key)
                if value:
                    password = value
                    self.logger.info("Using password from .env", key=key, emoji="🔑")
                    break

        if manager and email and password:
            self._persist_to_secret_manager(manager, email, password)
            return email, password

        if not password:
            import getpass

            password = getpass.getpass("🔑 Enter password: ").strip()

        if not env_creds or not any(key in env_creds for key in email_keys):
            save = input("💾 Save credentials to .env? (y/n): ").strip().lower()
            if save in ["y", "yes"]:
                self._save_credentials_to_env(email, password)

        if manager:
            self._persist_to_secret_manager(manager, email, password)

        return email, password

    def _prompt_for_new_credentials(self) -> Tuple[str, str]:
        """Prompt user for new credentials (after invalid credentials detected)."""
        import getpass

        print("")
        print("❌ Invalid credentials detected. Please enter new credentials:")
        print("")

        email = input("📧 Enter email: ").strip()
        password = getpass.getpass("🔑 Enter password: ").strip()

        manager = self._get_credential_manager()
        if manager and email and password:
            self._persist_to_secret_manager(manager, email, password)

        return email, password

    async def _automate_oauth_with_playwright(
        self,
        oauth_url: str,
        email: str,
        password: str,
        progress: Optional[GranularOAuthProgress] = None,
    ) -> bool:
        """Automate OAuth flow using Playwright."""
        try:
            from .playwright_adapter import PlaywrightOAuthAdapter

            adapter = PlaywrightOAuthAdapter(
                email=email, password=password, provider=self.provider, debug=self.debug
            )

            adapter.set_credential_reprompt_callback(self._prompt_for_new_credentials)

            if progress:
                adapter.set_progress_tracker(progress)

            success = await adapter.automate_login_with_retry(
                oauth_url, allow_credential_reprompt=True
            )

            if success:
                if adapter.email != email or adapter.password != password:
                    manager = self._get_credential_manager()
                    if manager:
                        self._persist_to_secret_manager(manager, adapter.email, adapter.password)
                return True
            else:
                return False

        except Exception as e:
            self.logger.error("OAuth automation error", error=str(e))
            if progress:
                progress.error(f"OAuth automation error: {e}")
            return False

    async def ensure_session_authenticated(self, force_reauth: bool = False) -> CapturedCredentials:
        """Ensure authentication happens once per endpoint per session."""
        async with self._session_lock:
            endpoint_key = self.mcp_endpoint

            if not force_reauth and endpoint_key in self._session_authenticated:
                if self._session_authenticated[endpoint_key]:
                    credentials = self._session_credentials.get(endpoint_key)
                    if credentials and credentials.is_valid():
                        self.logger.info(
                            "Using existing session authentication",
                            endpoint=endpoint_key,
                            email=credentials.email,
                            emoji="✅",
                        )
                        return credentials
                    else:
                        self.logger.warning(
                            "Session credentials expired or invalid, re-authenticating",
                            endpoint=endpoint_key,
                            emoji="⚠️",
                        )

            progress = GranularOAuthProgress()
            progress.start()

            progress.add_step(*OAuthSteps.PULL_CREDENTIALS)
            progress.start_step("pull_credentials")

            cached_creds = self.cache.load()
            if cached_creds and cached_creds.is_valid():
                progress.complete_step("pull_credentials")
                self._session_credentials[endpoint_key] = cached_creds
                self._session_authenticated[endpoint_key] = True

                if HAS_RICH:
                    console = Console()
                    expires_str = (
                        cached_creds.expires_at.strftime("%Y-%m-%d %H:%M:%S")
                        if cached_creds.expires_at
                        else "unknown"
                    )
                    console.print(
                        f"\n[bold green]✅ Authentication complete[/bold green]\n"
                        f"   [cyan]User:[/cyan] {cached_creds.email or 'unknown'}\n"
                        f"   [cyan]Expires:[/cyan] {expires_str}\n"
                        f"   [cyan]Endpoint:[/cyan] {endpoint_key}\n"
                    )

                progress.complete("Authentication complete (using cached credentials)")
                return cached_creds
            else:
                reason = "Cached credentials expired" if cached_creds else "No cache file found"
                progress.skip_step("pull_credentials", reason)

            progress.add_step("launch_browser", "Launching browser for OAuth")
            progress.start_step("launch_browser")

            try:
                client, credentials = await self.get_authenticated_client()

                self._session_credentials[endpoint_key] = credentials
                self._session_authenticated[endpoint_key] = True

                if HAS_RICH:
                    console = Console()
                    expires_str = (
                        credentials.expires_at.strftime("%Y-%m-%d %H:%M:%S")
                        if credentials.expires_at
                        else "unknown"
                    )
                    console.print(
                        f"\n[bold green]✅ Authentication complete[/bold green]\n"
                        f"   [cyan]User:[/cyan] {credentials.email or 'unknown'}\n"
                        f"   [cyan]Expires:[/cyan] {expires_str}\n"
                        f"   [cyan]Endpoint:[/cyan] {endpoint_key}\n"
                    )

                progress.complete_step("launch_browser")
                progress.complete("Authentication complete")

                return credentials

            except Exception as e:
                self.logger.error(
                    "Session authentication failed",
                    endpoint=endpoint_key,
                    error=str(e),
                    emoji="❌",
                )
                progress.error(f"Authentication failed: {e}")
                self._session_authenticated[endpoint_key] = False
                raise RuntimeError(f"Authentication failed: {e}") from e

    async def get_authenticated_client(self) -> tuple[Client, CapturedCredentials]:
        """Get authenticated MCP client and captured credentials."""
        progress = GranularOAuthProgress()
        progress.start()

        progress.add_step(*OAuthSteps.PULL_CREDENTIALS)
        progress.start_step("pull_credentials")

        cached_creds = self.cache.load()
        if cached_creds and cached_creds.is_valid():
            progress.complete_step("pull_credentials")
            self.logger.info(
                "Cached tokens found but token-based auth not implemented, using OAuth",
                emoji="⚠️",
            )
        else:
            reason = "Cached credentials expired" if cached_creds else "No cache file found"
            progress.skip_step("pull_credentials", reason)

        progress.add_step(*OAuthSteps.LOAD_ENV_CREDENTIALS)
        progress.start_step("load_env_credentials")

        email, password = self._prompt_for_credentials()
        progress.complete_step("load_env_credentials")

        progress.add_step(*OAuthSteps.INIT_OAUTH)
        progress.start_step("init_oauth")

        oauth_url_captured = asyncio.Event()

        oauth = CaptureOAuth(self, mcp_url=self.mcp_endpoint, client_name="MCP Test Suite")
        client = Client(self.mcp_endpoint, auth=oauth)
        progress.complete_step("init_oauth")

        progress.add_step(*OAuthSteps.FETCH_OAUTH_URL)
        progress.start_step("fetch_oauth_url")

        self.logger.debug("Starting OAuth flow...")
        self.logger.debug(f"OAuth redirect handler: {oauth.redirect_handler}")
        self.logger.debug(f"OAuth launch_browser: {oauth.launch_browser}")
        auth_task = asyncio.create_task(client.__aenter__())

        self.logger.debug("Waiting for OAuth URL or immediate auth completion...")

        oauth_url_task = asyncio.create_task(oauth_url_captured.wait())

        start_time = asyncio.get_event_loop().time()
        timeout = 30.0
        poll_interval = 2.0
        new_done: set = set()
        pending = {auth_task, oauth_url_task}

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                break

            if elapsed < 5:
                progress.update_step_description("fetch_oauth_url", "Contacting MCP server")
            elif elapsed < 10:
                progress.update_step_description("fetch_oauth_url", "Fetching OAuth configuration")
            elif elapsed < 15:
                progress.update_step_description(
                    "fetch_oauth_url", "Preparing authorization request"
                )
            elif elapsed < 20:
                progress.update_step_description("fetch_oauth_url", "Awaiting OAuth response")
            else:
                progress.update_step_description(
                    "fetch_oauth_url", f"Still waiting ({int(timeout - elapsed)}s left)"
                )

            new_done, pending = await asyncio.wait(
                pending, timeout=poll_interval, return_when=asyncio.FIRST_COMPLETED
            )

            if new_done:
                break

        done = new_done if new_done else set()

        if auth_task in done:
            oauth_url_task.cancel()
            try:
                await oauth_url_task
            except asyncio.CancelledError:
                pass

            progress.complete_step("fetch_oauth_url")

            try:
                exception = auth_task.exception()
                if exception:
                    self.logger.error(f"Authentication failed: {exception}", emoji="❌")
                    progress.error(f"Authentication failed: {exception}")
                    raise exception
            except asyncio.InvalidStateError:
                self.logger.error("Auth task in invalid state")
                progress.error("Authentication in invalid state")
                raise RuntimeError("Auth task completed but is in invalid state")

            self.logger.info("Authentication completed immediately (cached session)", emoji="✅")
            progress.complete("Authentication complete (cached session)")
        elif oauth_url_task in done:
            self.logger.debug(f"OAuth URL captured: {self._oauth_url}")
            progress.complete_step("fetch_oauth_url")

            if not self._oauth_url:
                progress.error("OAuth URL not captured")
                raise RuntimeError("OAuth URL was not captured")
            success = await self._automate_oauth_with_playwright(
                self._oauth_url, email, password, progress
            )
            if not success:
                progress.error("OAuth automation failed")
                raise RuntimeError("OAuth automation failed")

            progress.add_step(*OAuthSteps.EXCHANGE_TOKEN)
            progress.start_step("exchange_token")

            start_time = asyncio.get_event_loop().time()
            timeout = 60.0

            try:
                while not auth_task.done():
                    elapsed = asyncio.get_event_loop().time() - start_time
                    if elapsed > timeout:
                        raise asyncio.TimeoutError()

                    if elapsed < 10:
                        progress.update_step_description(
                            "exchange_token", "Processing OAuth callback"
                        )
                    elif elapsed < 20:
                        progress.update_step_description(
                            "exchange_token", "Validating access token"
                        )
                    elif elapsed < 30:
                        progress.update_step_description("exchange_token", "Verifying credentials")
                    elif elapsed < 40:
                        progress.update_step_description(
                            "exchange_token", "Waiting for server response"
                        )
                    else:
                        progress.update_step_description(
                            "exchange_token", f"Still waiting ({int(timeout - elapsed)}s left)"
                        )

                    try:
                        await asyncio.wait_for(auth_task, timeout=poll_interval)
                        break
                    except asyncio.TimeoutError:
                        continue

                progress.complete_step("exchange_token")
            except asyncio.CancelledError:
                self.logger.debug("Auth task was cancelled (OAuth likely completed)")
                progress.complete_step("exchange_token")
            except asyncio.TimeoutError:
                if auth_task.done():
                    try:
                        auth_task.result()
                        self.logger.info("Auth task completed despite timeout")
                        progress.complete_step("exchange_token")
                    except asyncio.CancelledError:
                        self.logger.debug("Auth task was cancelled (OAuth completed)")
                        progress.complete_step("exchange_token")
                    except Exception as e:
                        progress.error(f"Authentication failed: {e}")
                        raise
                else:
                    progress.error("Authentication timeout after OAuth")
                    raise RuntimeError("Authentication timed out after OAuth automation")
            except Exception as e:
                progress.error(f"Authentication failed: {e}")
                raise
        else:
            self.logger.error("Timeout waiting for OAuth URL or auth completion")
            self.logger.error(f"Auth task done: {auth_task.done()}")
            self.logger.error(f"OAuth URL captured: {oauth_url_captured.is_set()}")

            if auth_task.done():
                try:
                    exc = auth_task.exception()
                    if exc:
                        self.logger.error(f"Auth task exception: {exc}")
                except Exception as e:
                    self.logger.error(f"Could not check auth task exception: {e}")
            else:
                self.logger.error(
                    "Possible causes: 1) FastMCP OAuth not responding, "
                    "2) MCP server not initiating OAuth flow, 3) Network/firewall issue"
                )

            progress.error("Timeout waiting for authentication")
            raise RuntimeError(
                "OAuth URL not received and auth did not complete - MCP server may be down or slow"
            )

        progress.add_step(*OAuthSteps.SAVE_SESSION)
        progress.start_step("save_session")

        access_token = None
        expires_at = None
        refresh_token = None

        try:
            self.logger.debug(f"Client type: {type(client)}")
            self.logger.debug(f"Has transport: {hasattr(client, 'transport')}")

            if hasattr(client, "transport") and hasattr(client.transport, "auth"):
                auth_obj = client.transport.auth
                self.logger.debug(f"Auth type: {type(auth_obj)}")
                self.logger.debug(f"Has context: {hasattr(auth_obj, 'context')}")

                if hasattr(auth_obj, "context"):
                    context = auth_obj.context
                    self.logger.debug(f"Context type: {type(context)}")
                    self.logger.debug(f"Has current_tokens: {hasattr(context, 'current_tokens')}")
                    self.logger.debug(
                        f"current_tokens value: {context.current_tokens if hasattr(context, 'current_tokens') else 'N/A'}"
                    )

                    if hasattr(context, "current_tokens"):
                        current_tokens = context.current_tokens
                        if current_tokens:
                            access_token = current_tokens.access_token
                            refresh_token = current_tokens.refresh_token
                            if hasattr(current_tokens, "expires_in") and current_tokens.expires_in:
                                expires_at = datetime.now() + timedelta(
                                    seconds=current_tokens.expires_in
                                )
                            self.logger.info(
                                "Successfully captured access token from OAuth flow",
                                token_length=len(access_token) if access_token else 0,
                                has_refresh=bool(refresh_token),
                                expires_at=expires_at.isoformat() if expires_at else None,
                                emoji="🔑",
                            )
                        else:
                            self.logger.warning("current_tokens is None", emoji="⚠️")
                    else:
                        self.logger.warning("context has no current_tokens attribute", emoji="⚠️")
                else:
                    self.logger.warning("auth has no context attribute", emoji="⚠️")
            else:
                self.logger.warning("client has no transport.auth", emoji="⚠️")
        except Exception as e:
            self.logger.warning(
                "Failed to extract access token from OAuth context", error=str(e), emoji="⚠️"
            )
            import traceback

            self.logger.debug(f"Token extraction traceback: {traceback.format_exc()}")

        if not access_token:
            self.logger.warning(
                "Access token not found in OAuth context, using placeholder", emoji="⚠️"
            )
            access_token = "captured_from_oauth"
            expires_at = datetime.now() + timedelta(hours=24)

        credentials = CapturedCredentials(
            access_token=access_token,
            refresh_token=refresh_token,
            email=email,
            password=password,
            provider=self.provider,
            mcp_endpoint=self.mcp_endpoint,
            expires_at=expires_at,
        )

        self.cache.save(credentials)

        progress.complete_step("save_session")

        self._client = client
        self._credentials = credentials

        progress.complete("Authentication complete")

        return client, credentials

    async def close(self):
        """Clean up resources."""
        if self._client:
            try:
                await self._client.__aexit__(None, None, None)
            except RuntimeError as e:
                if "not holding this lock" not in str(e):
                    raise
                self.logger.debug("Ignoring lock cleanup error during client close", error=str(e))


async def get_authenticated_mcp_client(
    mcp_endpoint: Optional[str] = None, provider: str = "authkit"
) -> tuple[Client, CapturedCredentials]:
    """Convenience function to get authenticated client and credentials.

    Usage:
        client, creds = await get_authenticated_mcp_client()

        # Use client for MCP calls
        tools = await client.list_tools()

        # Use creds for direct HTTP
        response = httpx.post(url, headers={"Authorization": f"Bearer {creds.access_token}"})
    """
    broker = UnifiedCredentialBroker(mcp_endpoint, provider)
    return await broker.get_authenticated_client()
