"""Unified Authentication Utilities for MCP Projects.

Provides OAuth token management, JWT handling, session management,
and credential storage patterns for MCP authentication flows.

Usage:
    from pheno.testing.mcp_qa.utils.auth_utils import TokenManager, decode_jwt

    manager = TokenManager()
    manager.set_token("access_token", "...")
    token = manager.get_token("access_token")
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Union

from pheno.testing.mcp_qa.utils.logging_utils import get_logger

logger = get_logger(__name__)


# ============================================================================
# JWT Utilities
# ============================================================================


def decode_jwt(
    token: str,
    verify_signature: bool = False,
    secret: Optional[str] = None,
    algorithms: Optional[list[str]] = None,
) -> Dict[str, Any]:
    """Decode JWT token and return claims.

    Args:
        token: JWT token string
        verify_signature: Whether to verify signature
        secret: Secret key for verification (required if verify_signature=True)
        algorithms: List of accepted algorithms (default: ["HS256", "RS256"])

    Returns:
        Dictionary of JWT claims

    Raises:
        ValueError: If token is invalid
        RuntimeError: If PyJWT not installed

    Example:
        claims = decode_jwt(token)
        user_id = claims.get("sub")
        email = claims.get("email")
    """
    try:
        import jwt
    except ImportError:
        raise RuntimeError(
            "PyJWT is required for JWT operations. " "Install it with 'pip install pyjwt'"
        )

    try:
        if verify_signature:
            if not secret:
                raise ValueError("Secret required for signature verification")

            algorithms = algorithms or ["HS256", "RS256"]
            decoded = jwt.decode(token, secret, algorithms=algorithms)
        else:
            # Decode without verification (useful for AuthKit tokens)
            decoded = jwt.decode(token, options={"verify_signature": False})

        return decoded

    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid JWT token: {e}")


def extract_user_from_jwt(token: str) -> Dict[str, Any]:
    """Extract user information from JWT token.

    Args:
        token: JWT token string

    Returns:
        Dictionary with user info (id, email, etc.)

    Example:
        user = extract_user_from_jwt(token)
        print(user["email"])
    """
    claims = decode_jwt(token, verify_signature=False)

    # Try different claim locations (AuthKit, Auth0, etc.)
    user = claims.get("user") or claims

    return {
        "id": claims.get("external_auth_id") or claims.get("sub") or user.get("id"),
        "email": user.get("email"),
        "name": user.get("name"),
        "picture": user.get("picture"),
        "claims": claims,
    }


def is_token_expired(token: str, buffer_seconds: int = 60) -> bool:
    """Check if JWT token is expired.

    Args:
        token: JWT token string
        buffer_seconds: Consider expired if expires within this time

    Returns:
        True if expired or expiring soon

    Example:
        if is_token_expired(access_token):
            # Refresh token
            pass
    """
    try:
        claims = decode_jwt(token, verify_signature=False)
        exp = claims.get("exp")

        if not exp:
            # No expiration claim
            return False

        # Check if expired (with buffer)
        return time.time() > (exp - buffer_seconds)

    except Exception:
        # Error decoding = consider expired
        return True


# ============================================================================
# Token Storage
# ============================================================================


@dataclass
class TokenSet:
    """Set of OAuth tokens.

    Attributes:
        access_token: Access token
        refresh_token: Optional refresh token
        id_token: Optional ID token
        expires_at: Expiration timestamp (Unix time)
        scopes: List of granted scopes
        metadata: Additional metadata
    """

    access_token: str
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None
    expires_at: Optional[int] = None
    scopes: Optional[list[str]] = None
    metadata: Optional[Dict[str, Any]] = None

    def is_expired(self, buffer_seconds: int = 60) -> bool:
        """
        Check if access token is expired.
        """
        if not self.expires_at:
            return False
        return time.time() > (self.expires_at - buffer_seconds)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        """
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "id_token": self.id_token,
            "expires_at": self.expires_at,
            "scopes": self.scopes,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TokenSet:
        """
        Create from dictionary.
        """
        return cls(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            id_token=data.get("id_token"),
            expires_at=data.get("expires_at"),
            scopes=data.get("scopes"),
            metadata=data.get("metadata"),
        )


class TokenManager:
    """Manage OAuth tokens with in-memory and file storage.

    Example:
        manager = TokenManager()

        # Store tokens
        tokens = TokenSet(access_token="...", refresh_token="...")
        manager.set_tokens("user123", tokens)

        # Retrieve tokens
        tokens = manager.get_tokens("user123")

        # Persist to disk
        manager.save_to_file("tokens.json")

        # Load from disk
        manager = TokenManager.from_file("tokens.json")
    """

    def __init__(self):
        """
        Initialize token manager.
        """
        self._tokens: Dict[str, TokenSet] = {}

    def set_tokens(self, key: str, tokens: TokenSet):
        """Store tokens for a key.

        Args:
            key: Storage key (e.g. user ID)
            tokens: Token set to store
        """
        self._tokens[key] = tokens
        logger.debug(f"Stored tokens for {key}")

    def get_tokens(self, key: str) -> Optional[TokenSet]:
        """Retrieve tokens for a key.

        Args:
            key: Storage key

        Returns:
            Token set or None if not found
        """
        return self._tokens.get(key)

    def remove_tokens(self, key: str):
        """Remove tokens for a key.

        Args:
            key: Storage key
        """
        if key in self._tokens:
            del self._tokens[key]
            logger.debug(f"Removed tokens for {key}")

    def clear(self):
        """
        Clear all stored tokens.
        """
        self._tokens.clear()
        logger.debug("Cleared all tokens")

    def save_to_file(self, path: Union[str, Path]):
        """Save tokens to JSON file.

        Args:
            path: File path
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {key: tokens.to_dict() for key, tokens in self._tokens.items()}

        with path.open("w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved tokens to {path}")

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> TokenManager:
        """Load tokens from JSON file.

        Args:
            path: File path

        Returns:
            TokenManager with loaded tokens
        """
        path = Path(path)

        if not path.exists():
            logger.warning(f"Token file not found: {path}")
            return cls()

        with path.open("r") as f:
            data = json.load(f)

        manager = cls()
        for key, token_data in data.items():
            manager._tokens[key] = TokenSet.from_dict(token_data)

        logger.info(f"Loaded tokens from {path}")
        return manager


# ============================================================================
# Credential Storage
# ============================================================================


class CredentialStore:
    """Secure credential storage for OAuth flows.

    Stores credentials in memory with optional file persistence.
    For production, use a proper secret manager (e.g. AWS Secrets Manager).

    Example:
        store = CredentialStore()

        # Store credentials
        store.set("username", "user@example.com")
        store.set("password", "secret123", sensitive=True)

        # Retrieve credentials
        username = store.get("username")
        password = store.get("password")

        # Persist (WARNING: credentials in plaintext)
        store.save_to_file(".credentials")
    """

    def __init__(self):
        """
        Initialize credential store.
        """
        self._credentials: Dict[str, Any] = {}
        self._sensitive_keys: set[str] = set()

    def set(self, key: str, value: Any, sensitive: bool = False):
        """Store a credential.

        Args:
            key: Credential key
            value: Credential value
            sensitive: Mark as sensitive (won't be logged)
        """
        self._credentials[key] = value
        if sensitive:
            self._sensitive_keys.add(key)

        log_value = "***" if sensitive else value
        logger.debug(f"Stored credential '{key}': {log_value}")

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a credential.

        Args:
            key: Credential key
            default: Default value if not found

        Returns:
            Credential value or default
        """
        return self._credentials.get(key, default)

    def has(self, key: str) -> bool:
        """
        Check if credential exists.
        """
        return key in self._credentials

    def remove(self, key: str):
        """
        Remove a credential.
        """
        if key in self._credentials:
            del self._credentials[key]
            self._sensitive_keys.discard(key)
            logger.debug(f"Removed credential '{key}'")

    def clear(self):
        """
        Clear all credentials.
        """
        self._credentials.clear()
        self._sensitive_keys.clear()
        logger.debug("Cleared all credentials")

    def save_to_file(self, path: Union[str, Path]):
        """Save credentials to JSON file.

        WARNING: Credentials are stored in plaintext!
        Only use for local development/testing.

        Args:
            path: File path
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w") as f:
            json.dump(self._credentials, f, indent=2)

        # Set restrictive permissions (Unix only)
        try:
            path.chmod(0o600)
        except Exception:
            pass

        logger.warning(f"Saved credentials to {path} (PLAINTEXT)")

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> CredentialStore:
        """Load credentials from JSON file.

        Args:
            path: File path

        Returns:
            CredentialStore with loaded credentials
        """
        path = Path(path)

        if not path.exists():
            logger.warning(f"Credential file not found: {path}")
            return cls()

        with path.open("r") as f:
            data = json.load(f)

        store = cls()
        store._credentials = data

        logger.info(f"Loaded credentials from {path}")
        return store


# ============================================================================
# Session Management
# ============================================================================


class SessionManager:
    """Manage user sessions with token and credential storage.

    Combines TokenManager and CredentialStore for complete session management.

    Example:
        session = SessionManager()

        # Store session
        session.create_session(
            "user123",
            tokens=TokenSet(access_token="..."),
            credentials={"email": "user@example.com"}
        )

        # Get session
        tokens = session.get_tokens("user123")
        email = session.get_credential("user123", "email")

        # End session
        session.end_session("user123")
    """

    def __init__(self):
        """
        Initialize session manager.
        """
        self.token_manager = TokenManager()
        self._credentials: Dict[str, CredentialStore] = {}

    def create_session(
        self,
        session_id: str,
        tokens: TokenSet,
        credentials: Optional[Dict[str, Any]] = None,
    ):
        """Create a new session.

        Args:
            session_id: Session identifier
            tokens: OAuth tokens
            credentials: Optional credentials
        """
        self.token_manager.set_tokens(session_id, tokens)

        if credentials:
            store = CredentialStore()
            for key, value in credentials.items():
                store.set(key, value)
            self._credentials[session_id] = store

        logger.info(f"Created session {session_id}")

    def get_tokens(self, session_id: str) -> Optional[TokenSet]:
        """
        Get tokens for session.
        """
        return self.token_manager.get_tokens(session_id)

    def get_credential(self, session_id: str, key: str) -> Optional[Any]:
        """
        Get credential for session.
        """
        store = self._credentials.get(session_id)
        if store:
            return store.get(key)
        return None

    def end_session(self, session_id: str):
        """
        End a session and clean up.
        """
        self.token_manager.remove_tokens(session_id)
        if session_id in self._credentials:
            del self._credentials[session_id]
        logger.info(f"Ended session {session_id}")

    def clear_all(self):
        """
        Clear all sessions.
        """
        self.token_manager.clear()
        self._credentials.clear()
        logger.info("Cleared all sessions")


__all__ = [
    "decode_jwt",
    "extract_user_from_jwt",
    "is_token_expired",
    "TokenSet",
    "TokenManager",
    "CredentialStore",
    "SessionManager",
]
