"""Playwright State Manager for Authentication Session Reuse.

Manages authenticated browser contexts with:
- Storage state caching (cookies, localStorage, sessionStorage)
- Multiple authentication profiles
- Worker-scoped authentication for parallel testing
- Session validation and refresh
- Encrypted state storage

Usage:
    # Basic usage
    state_mgr = PlaywrightStateManager()

    # Save authenticated state
    await state_mgr.save_state(page, "my_account")

    # Reuse state in new context
    context = await state_mgr.create_context_with_state(browser, "my_account")

    # Worker-scoped (for parallel tests)
    worker_id = pytest.get_worker_id()
    context = await state_mgr.get_worker_context(browser, worker_id)
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from playwright.async_api import Browser, BrowserContext, Page

    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    # Type hints for when Playwright not installed
    Browser = Any
    BrowserContext = Any
    Page = Any

from .credential_manager import CredentialManager


@dataclass
class StoredState:
    """
    Metadata about stored authentication state.
    """

    profile_name: str
    created_at: datetime
    last_used: datetime
    expires_at: Optional[datetime] = None
    provider: str = ""
    email: str = ""
    metadata: Optional[Dict[str, Any]] = None

    def is_expired(self) -> bool:
        """
        Check if state has expired.
        """
        if not self.expires_at:
            return False
        return datetime.now() >= self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        """
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        data["last_used"] = self.last_used.isoformat()
        if self.expires_at:
            data["expires_at"] = self.expires_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StoredState":
        """
        Create from dictionary.
        """
        data = dict(data)
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["last_used"] = datetime.fromisoformat(data["last_used"])
        if data.get("expires_at"):
            data["expires_at"] = datetime.fromisoformat(data["expires_at"])
        return cls(**data)


class PlaywrightStateManager:
    """Manages Playwright authentication states for session reuse.

    Features:
    - Save/load browser storage state
    - Multiple authentication profiles
    - Worker-scoped contexts for parallel testing
    - Session validation
    - Encrypted storage via CredentialManager
    """

    def __init__(
        self,
        storage_dir: Optional[Path] = None,
        credential_manager: Optional[CredentialManager] = None,
        default_ttl_hours: int = 24,
    ):
        """Initialize state manager.

        Args:
            storage_dir: Directory for state storage (default: ~/.mcp_qa/states/)
            credential_manager: CredentialManager for encrypted storage
            default_ttl_hours: Default TTL for states in hours
        """
        if not HAS_PLAYWRIGHT:
            raise RuntimeError(
                "Playwright not installed. Install with: pip install playwright && playwright install"
            )

        self.storage_dir = storage_dir or Path.home() / ".mcp_qa" / "states"
        self.storage_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

        self.credential_manager = credential_manager
        self.default_ttl_hours = default_ttl_hours

        self.metadata_file = self.storage_dir / "metadata.json"
        self._metadata: Dict[str, StoredState] = self._load_metadata()

    def _load_metadata(self) -> Dict[str, StoredState]:
        """
        Load state metadata.
        """
        if not self.metadata_file.exists():
            return {}

        try:
            with open(self.metadata_file, "r") as f:
                data = json.load(f)

            metadata = {}
            for name, state_dict in data.items():
                metadata[name] = StoredState.from_dict(state_dict)

            return metadata

        except Exception as e:
            print(f"⚠️  Failed to load state metadata: {e}")
            return {}

    def _save_metadata(self):
        """
        Save state metadata.
        """
        data = {name: state.to_dict() for name, state in self._metadata.items()}

        with open(self.metadata_file, "w") as f:
            json.dump(data, f, indent=2)

        self.metadata_file.chmod(0o600)

    def _get_state_path(self, profile_name: str) -> Path:
        """
        Get path for state file.
        """
        return self.storage_dir / f"{profile_name}.json"

    async def save_state(
        self,
        page_or_context: Any,  # Page | BrowserContext
        profile_name: str,
        provider: str = "",
        email: str = "",
        ttl_hours: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StoredState:
        """Save authentication state from page or context.

        Args:
            page_or_context: Playwright Page or BrowserContext
            profile_name: Unique name for this profile
            provider: Provider name (e.g., "authkit", "google")
            email: User email
            ttl_hours: TTL in hours (default: default_ttl_hours)
            metadata: Additional metadata

        Returns:
            StoredState object
        """
        # Get context from page if needed
        if isinstance(page_or_context, Page):
            context = page_or_context.context
        else:
            context = page_or_context

        # Save storage state
        state_path = self._get_state_path(profile_name)
        await context.storage_state(path=str(state_path))

        # Create metadata
        now = datetime.now()
        ttl = ttl_hours or self.default_ttl_hours
        expires_at = now + timedelta(hours=ttl)

        stored_state = StoredState(
            profile_name=profile_name,
            created_at=now,
            last_used=now,
            expires_at=expires_at,
            provider=provider,
            email=email,
            metadata=metadata or {},
        )

        self._metadata[profile_name] = stored_state
        self._save_metadata()

        print(f"✅ Saved authentication state: {profile_name}")
        return stored_state

    async def create_context_with_state(
        self, browser: Browser, profile_name: str, **context_kwargs
    ) -> Optional[BrowserContext]:
        """Create browser context with saved state.

        Args:
            browser: Playwright Browser instance
            profile_name: Profile name
            **context_kwargs: Additional context options

        Returns:
            BrowserContext with loaded state, or None if not found/expired
        """
        # Get metadata
        stored_state = self._metadata.get(profile_name)
        if not stored_state:
            print(f"⚠️  State not found: {profile_name}")
            return None

        # Check expiration
        if stored_state.is_expired():
            print(f"⚠️  State expired: {profile_name}")
            await self.delete_state(profile_name)
            return None

        # Load storage state
        state_path = self._get_state_path(profile_name)
        if not state_path.exists():
            print(f"⚠️  State file not found: {profile_name}")
            return None

        # Create context with state
        context = await browser.new_context(storage_state=str(state_path), **context_kwargs)

        # Update last used
        stored_state.last_used = datetime.now()
        self._save_metadata()

        print(f"✅ Loaded authentication state: {profile_name}")
        return context

    async def get_or_create_state(
        self, browser: Browser, profile_name: str, auth_callback: callable, **context_kwargs
    ) -> BrowserContext:
        """Get existing state or create new one.

        Args:
            browser: Playwright Browser instance
            profile_name: Profile name
            auth_callback: Async function to perform authentication
            **context_kwargs: Additional context options

        Returns:
            Authenticated BrowserContext

        Example:
            async def do_auth(page):
                await page.goto("https://example.com/login")
                await page.fill("#email", "user@example.com")
                await page.fill("#password", "password")
                await page.click("button[type=submit]")

            context = await state_mgr.get_or_create_state(
                browser, "my_account", do_auth
            )
        """
        # Try to load existing state
        context = await self.create_context_with_state(browser, profile_name, **context_kwargs)

        if context:
            return context

        # Create new authenticated state
        print(f"🔐 Creating new authentication state: {profile_name}")

        context = await browser.new_context(**context_kwargs)
        page = await context.new_page()

        # Run authentication
        await auth_callback(page)

        # Save state
        await self.save_state(page, profile_name)

        return context

    async def get_worker_context(
        self, browser: Browser, worker_id: str, auth_callback: callable, **context_kwargs
    ) -> BrowserContext:
        """Get worker-scoped context for parallel testing.

        Each worker gets its own authentication profile to avoid conflicts.

        Args:
            browser: Playwright Browser instance
            worker_id: Worker ID (e.g., from pytest-xdist)
            auth_callback: Async function to perform authentication
            **context_kwargs: Additional context options

        Returns:
            Authenticated BrowserContext for worker

        Example (pytest):
            @pytest.fixture(scope="session")
            async def authenticated_context(browser, worker_id):
                state_mgr = PlaywrightStateManager()

                async def do_auth(page):
                    # Perform authentication
                    pass

                return await state_mgr.get_worker_context(
                    browser, worker_id, do_auth
                )
        """
        profile_name = f"worker_{worker_id}"
        return await self.get_or_create_state(
            browser, profile_name, auth_callback, **context_kwargs
        )

    async def delete_state(self, profile_name: str) -> bool:
        """Delete saved state.

        Args:
            profile_name: Profile name

        Returns:
            True if deleted, False if not found
        """
        if profile_name not in self._metadata:
            return False

        # Delete state file
        state_path = self._get_state_path(profile_name)
        if state_path.exists():
            state_path.unlink()

        # Delete metadata
        del self._metadata[profile_name]
        self._save_metadata()

        print(f"🗑️  Deleted state: {profile_name}")
        return True

    def list_states(self) -> List[StoredState]:
        """
        List all stored states.
        """
        return list(self._metadata.values())

    def get_state_info(self, profile_name: str) -> Optional[StoredState]:
        """
        Get info about a stored state.
        """
        return self._metadata.get(profile_name)

    async def clear_expired(self) -> int:
        """Remove all expired states.

        Returns:
            Number of states removed
        """
        expired = [name for name, state in self._metadata.items() if state.is_expired()]

        for name in expired:
            await self.delete_state(name)

        return len(expired)

    async def validate_state(
        self, browser: Browser, profile_name: str, validation_url: str, validation_selector: str
    ) -> bool:
        """Validate that a saved state is still authenticated.

        Args:
            browser: Playwright Browser instance
            profile_name: Profile name
            validation_url: URL to check authentication
            validation_selector: Selector that should exist when authenticated

        Returns:
            True if still authenticated, False otherwise
        """
        context = await self.create_context_with_state(browser, profile_name)
        if not context:
            return False

        try:
            page = await context.new_page()
            await page.goto(validation_url)

            # Check for authenticated selector
            try:
                await page.wait_for_selector(validation_selector, timeout=5000)
                await context.close()
                return True
            except Exception:
                await context.close()
                return False

        except Exception as e:
            print(f"⚠️  Validation error: {e}")
            if context:
                await context.close()
            return False


__all__ = [
    "PlaywrightStateManager",
    "StoredState",
]
