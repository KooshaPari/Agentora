"""Unified Session Token Manager.

Combines best features from both implementations:
- Encrypted token caching
- Session-scoped token management
- Context manager for ensuring tokens
- Disk and memory caching
"""

import asyncio
import json
import tempfile
import time
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Awaitable, Callable, Dict, Optional

from cryptography.fernet import Fernet


@dataclass
class OAuthTokens:
    """
    OAuth token set with metadata.
    """

    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[float] = None
    provider: str = "unknown"
    scope: Optional[str] = None
    token_type: str = "Bearer"

    @property
    def is_expired(self) -> bool:
        """
        Check if token is expired (with 5 minute buffer).
        """
        if not self.expires_at:
            return False
        return time.time() > (self.expires_at - 300)  # 5 min buffer

    @property
    def is_valid(self) -> bool:
        """
        Check if token is valid and not expired.
        """
        return bool(self.access_token and not self.is_expired)


class TokenCache:
    """Encrypted token cache for OAuth session persistence.

    Features:
    - Encrypted storage with Fernet
    - Per-provider token files
    - Automatic corruption recovery
    - Restricted file permissions
    """

    def __init__(self, cache_dir: Optional[Path] = None, encrypt: bool = True):
        """Initialize token cache.

        Args:
            cache_dir: Cache directory (default: temp directory)
            encrypt: Enable encryption (default: True)
        """
        self.cache_dir = cache_dir or Path(tempfile.gettempdir()) / "mcp_oauth"
        self.cache_dir.mkdir(exist_ok=True, parents=True)
        self.encrypt = encrypt
        self._key = self._get_or_create_key() if encrypt else None

    def _get_or_create_key(self) -> bytes:
        """
        Get or create encryption key.
        """
        key_file = self.cache_dir / ".key"
        if key_file.exists():
            return key_file.read_bytes()

        key = Fernet.generate_key()
        key_file.write_bytes(key)
        key_file.chmod(0o600)  # Restrict permissions
        return key

    def _cache_file(self, provider: str) -> Path:
        """
        Get cache file path for provider.
        """
        return self.cache_dir / f"{provider}_tokens.cache"

    def store(self, provider: str, tokens: OAuthTokens) -> None:
        """Store encrypted tokens for provider.

        Args:
            provider: Provider name
            tokens: OAuth tokens to store
        """
        cache_file = self._cache_file(provider)
        data = asdict(tokens)

        if self.encrypt and self._key:
            fernet = Fernet(self._key)
            encrypted_data = fernet.encrypt(json.dumps(data).encode())
            cache_file.write_bytes(encrypted_data)
        else:
            cache_file.write_text(json.dumps(data))

        cache_file.chmod(0o600)

    def load(self, provider: str) -> Optional[OAuthTokens]:
        """Load and decrypt tokens for provider.

        Args:
            provider: Provider name

        Returns:
            OAuthTokens if valid, None otherwise
        """
        cache_file = self._cache_file(provider)
        if not cache_file.exists():
            return None

        try:
            if self.encrypt and self._key:
                fernet = Fernet(self._key)
                encrypted_data = cache_file.read_bytes()
                decrypted_data = fernet.decrypt(encrypted_data)
                data = json.loads(decrypted_data.decode())
            else:
                data = json.loads(cache_file.read_text())

            tokens = OAuthTokens(**data)
            return tokens if tokens.is_valid else None

        except Exception:
            # Clear corrupted cache
            cache_file.unlink(missing_ok=True)
            return None

    def clear(self, provider: Optional[str] = None) -> None:
        """Clear cache for specific provider or all providers.

        Args:
            provider: Provider name (None clears all)
        """
        if provider:
            self._cache_file(provider).unlink(missing_ok=True)
        else:
            for file in self.cache_dir.glob("*_tokens.cache"):
                file.unlink(missing_ok=True)

    def list_cached_providers(self) -> list[str]:
        """List providers with cached tokens.

        Returns:
            List of provider names with valid cached tokens
        """
        providers = []
        for file in self.cache_dir.glob("*_tokens.cache"):
            provider = file.stem.replace("_tokens", "")
            if self.load(provider):  # Only valid tokens
                providers.append(provider)
        return providers


class SessionTokenManager:
    """Manages tokens for the current test session.

    Features:
    - Two-tier caching (session memory + disk)
    - Async locks to prevent concurrent OAuth
    - Context manager for token lifecycle
    - Automatic token refresh
    """

    def __init__(self, cache: Optional[TokenCache] = None):
        """Initialize session token manager.

        Args:
            cache: Token cache instance (default: creates new)
        """
        self.cache = cache or TokenCache()
        self._session_tokens: Dict[str, OAuthTokens] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

    async def get_tokens(self, provider: str) -> Optional[OAuthTokens]:
        """Get valid tokens for provider (session cache -> disk cache).

        Args:
            provider: Provider name

        Returns:
            Valid OAuthTokens or None
        """
        # Check session cache first
        if provider in self._session_tokens:
            tokens = self._session_tokens[provider]
            if tokens.is_valid:
                return tokens
            else:
                # Remove expired tokens from session
                del self._session_tokens[provider]

        # Check disk cache
        tokens = self.cache.load(provider)
        if tokens and tokens.is_valid:
            self._session_tokens[provider] = tokens
            return tokens

        return None

    async def store_tokens(self, provider: str, tokens: OAuthTokens) -> None:
        """Store tokens in both session and disk cache.

        Args:
            provider: Provider name
            tokens: OAuth tokens to store
        """
        self._session_tokens[provider] = tokens
        self.cache.store(provider, tokens)

    async def get_lock(self, provider: str) -> asyncio.Lock:
        """Get asyncio lock for provider to prevent concurrent OAuth.

        Args:
            provider: Provider name

        Returns:
            Asyncio lock for provider
        """
        if provider not in self._locks:
            self._locks[provider] = asyncio.Lock()
        return self._locks[provider]

    @asynccontextmanager
    async def ensure_tokens(
        self, provider: str, oauth_callback: Callable[[str], Awaitable[OAuthTokens]]
    ):
        """Context manager that ensures valid tokens exist.

        Usage:
            async with manager.ensure_tokens("authkit", perform_oauth) as tokens:
                # Use tokens

        Args:
            provider: Provider name
            oauth_callback: Async function that performs OAuth and returns tokens

        Yields:
            Valid OAuthTokens
        """
        async with await self.get_lock(provider):
            tokens = await self.get_tokens(provider)
            if tokens:
                yield tokens
                return

            # Need to authenticate
            new_tokens = await oauth_callback(provider)
            if new_tokens:
                await self.store_tokens(provider, new_tokens)
                yield new_tokens
            else:
                raise RuntimeError(f"OAuth failed for provider: {provider}")

    def clear_session(self) -> None:
        """
        Clear all session tokens (keep disk cache).
        """
        self._session_tokens.clear()

    def clear_all(self) -> None:
        """
        Clear session and disk cache.
        """
        self._session_tokens.clear()
        self.cache.clear()


# Global session manager
_session_manager: Optional[SessionTokenManager] = None


def get_session_manager() -> SessionTokenManager:
    """
    Get global session token manager.
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionTokenManager()
    return _session_manager


def clear_oauth_cache():
    """
    Clear all OAuth cache (for CLI/debugging).
    """
    manager = get_session_manager()
    manager.clear_all()
    print("OAuth cache cleared")
