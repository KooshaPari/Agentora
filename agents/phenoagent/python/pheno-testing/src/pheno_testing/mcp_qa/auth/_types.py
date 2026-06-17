"""Credential type definitions and data structures."""

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class CredentialType(Enum):
    """Types of credentials that can be stored."""

    PASSWORD = "password"
    TOTP_SECRET = "totp_secret"
    API_TOKEN = "api_token"
    OAUTH_TOKEN = "oauth_token"
    SESSION_COOKIE = "session_cookie"
    PASSKEY_METADATA = "passkey_metadata"
    CUSTOM = "custom"


ENV_IMPORT_RULES: list[Dict[str, Any]] = [
    {
        "name": "authkit_env_login",
        "provider": "authkit",
        "credential_type": CredentialType.PASSWORD,
        "value_keys": [
            "ATOMS_TEST_PASSWORD",
            "ZEN_TEST_PASSWORD",
            "OAUTH_AUTHKIT_PASSWORD",
            "OAUTH_PASSWORD",
            "AUTHKIT_TEST_PASSWORD",
        ],
        "email_keys": [
            "ATOMS_TEST_EMAIL",
            "ZEN_TEST_EMAIL",
            "OAUTH_AUTHKIT_EMAIL",
            "OAUTH_EMAIL",
            "AUTHKIT_TEST_EMAIL",
        ],
        "username_keys": [
            "ATOMS_TEST_USERNAME",
            "ZEN_TEST_USERNAME",
            "AUTHKIT_TEST_USERNAME",
        ],
        "metadata_keys": {
            "mcp_endpoint": [
                "MCP_ENDPOINT",
                "ATOMS_FASTMCP_BASE_URL",
                "FASTMCP_BASE_URL",
            ]
        },
    },
    {
        "name": "authkit_env_totp",
        "provider": "authkit",
        "credential_type": CredentialType.TOTP_SECRET,
        "value_keys": [
            "ATOMS_TEST_MFA_CODE",
            "ATOMS_TEST_MFA_SECRET",
            "ZEN_TEST_MFA_CODE",
            "ZEN_TEST_MFA_SECRET",
            "OAUTH_AUTHKIT_MFA_SECRET",
            "AUTHKIT_TOTP_SECRET",
            "TOTP_SECRET",
        ],
    },
    {
        "name": "github_env_login",
        "provider": "github",
        "credential_type": CredentialType.PASSWORD,
        "value_keys": [
            "GITHUB_PASSWORD",
            "GITHUB_TOKEN",
            "OAUTH_GITHUB_PASSWORD",
        ],
        "username_keys": [
            "GITHUB_USERNAME",
            "OAUTH_GITHUB_USERNAME",
        ],
        "metadata_keys": {
            "token_type": ["GITHUB_TOKEN_TYPE"],
        },
    },
    {
        "name": "github_env_totp",
        "provider": "github",
        "credential_type": CredentialType.TOTP_SECRET,
        "value_keys": [
            "GITHUB_MFA_SECRET",
            "GITHUB_TOTP_SECRET",
        ],
    },
    {
        "name": "google_env_login",
        "provider": "google",
        "credential_type": CredentialType.PASSWORD,
        "value_keys": [
            "GOOGLE_PASSWORD",
            "OAUTH_GOOGLE_PASSWORD",
        ],
        "email_keys": [
            "GOOGLE_EMAIL",
            "OAUTH_GOOGLE_EMAIL",
        ],
    },
    {
        "name": "google_env_totp",
        "provider": "google",
        "credential_type": CredentialType.TOTP_SECRET,
        "value_keys": [
            "GOOGLE_MFA_SECRET",
            "GOOGLE_TOTP_SECRET",
        ],
    },
    {
        "name": "supabase_service_role",
        "provider": "supabase",
        "credential_type": CredentialType.API_TOKEN,
        "value_keys": [
            "SUPABASE_SERVICE_ROLE_KEY",
            "SUPABASE_KEY",
        ],
        "metadata_keys": {
            "url": ["SUPABASE_URL"],
            "anon_key": ["SUPABASE_ANON_KEY"],
        },
    },
]


@dataclass
class Credential:
    """A stored credential."""

    name: str
    credential_type: CredentialType
    provider: str
    value: str
    username: Optional[str] = None
    email: Optional[str] = None
    expires_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def is_expired(self) -> bool:
        """Check if credential has expired."""
        if not self.expires_at:
            return False
        return datetime.now() >= self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["credential_type"] = self.credential_type.value
        if self.expires_at:
            data["expires_at"] = self.expires_at.isoformat()
        if self.created_at:
            data["created_at"] = self.created_at.isoformat()
        if self.updated_at:
            data["updated_at"] = self.updated_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Credential":
        """Create from dictionary."""
        data = dict(data)
        data["credential_type"] = CredentialType(data["credential_type"])
        if data.get("expires_at"):
            data["expires_at"] = datetime.fromisoformat(data["expires_at"])
        if data.get("created_at"):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return cls(**data)
