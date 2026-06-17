"""Secure Credential Manager with AES-256 Encryption.

Provides encrypted storage for all types of authentication credentials:
- Passwords
- TOTP secrets
- API tokens
- OAuth tokens
- Session cookies
- Passkey metadata

Storage: ~/.mcp_qa/credentials.enc (encrypted JSON)
Encryption: AES-256-GCM with PBKDF2 key derivation
"""

import getpass
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pheno.testing.mcp_qa.logging import get_logger

from ._env import EnvBootstrap
from ._storage import CredentialStorage, create_cipher, get_or_create_salt
from ._types import Credential, CredentialType


class CredentialManager:
    """Secure credential manager with encrypted storage.

    Features:
    - AES-256-GCM encryption
    - Master password protection
    - Multiple credential types
    - Automatic key derivation (PBKDF2)
    - Safe storage in ~/.mcp_qa/

    Usage:
        manager = CredentialManager()

        # Store password
        manager.store_credential(
            name="authkit_main",
            credential_type=CredentialType.PASSWORD,
            provider="authkit",
            value="my_password",
            email="user@example.com"
        )

        # Retrieve password
        cred = manager.get_credential("authkit_main")
        print(cred.value)  # Decrypted password

        # Store TOTP secret
        manager.store_credential(
            name="authkit_totp",
            credential_type=CredentialType.TOTP_SECRET,
            provider="authkit",
            value="JBSWY3DPEHPK3PXP"
        )
    """

    def __init__(self, master_password: Optional[str] = None, storage_dir: Optional[Path] = None):
        """Initialize credential manager.

        Args:
            master_password: Master password for encryption (prompts if not provided)
            storage_dir: Storage directory (default: ~/.mcp_qa/)
        """
        self.logger = get_logger(__name__)

        self.storage_dir = storage_dir or Path.home() / ".mcp_qa"
        self.storage_dir.mkdir(exist_ok=True, mode=0o700)

        self.salt_file = self.storage_dir / ".salt"

        self.master_password = master_password or self._get_master_password()
        self._cipher = create_cipher(self.master_password, get_or_create_salt(self.salt_file))

        self._storage = CredentialStorage(self.storage_dir, self._cipher)
        self._credentials: Dict[str, Credential] = self._load_credentials()

        self._env_bootstrap = EnvBootstrap(self._credentials)
        self._env_bootstrap.bootstrap_if_needed(self.store_credential, self.update_credential)

    def _get_master_password(self) -> str:
        """Get master password from env, keychain, or prompt."""
        logger = get_logger(__name__)

        env_password = os.getenv("MCP_QA_MASTER_PASSWORD")
        if env_password:
            logger.debug("Using master password from environment")
            return env_password

        keychain = self._get_keychain()
        if keychain:
            return self._get_password_from_keychain_or_prompt(keychain, logger)

        return self._get_password_fallback(logger)

    def _get_keychain(self):
        """Try to get keychain manager."""
        try:
            from pheno.testing.mcp_qa.auth.keychain_manager import get_keychain_manager

            keychain = get_keychain_manager()
            if keychain.is_keychain_available():
                return keychain
        except ImportError:
            self.logger.debug("Keychain manager not available")
        except Exception as e:
            self.logger.warning("Keychain initialization failed", error=str(e))
        return None

    def _get_password_from_keychain_or_prompt(self, keychain, logger) -> str:
        """Get password from keychain or prompt with keychain migration."""
        account = "mcp_qa_master_password"
        credentials_file = self.storage_dir / "credentials.enc"

        if credentials_file.exists():
            try:
                stored_password = keychain.get_password(account)
                if stored_password:
                    logger.info("Using master password from Keychain")
                    if self._verify_password(stored_password):
                        return stored_password
                    keychain.delete_password(account)
                    logger.warning("Keychain password doesn't match credential store", emoji="⚠️")
            except Exception as e:
                logger.debug("Keychain retrieval failed", error=str(e))

        return self._prompt_existing_password(keychain, logger, account)

    def _prompt_existing_password(self, keychain, logger, account: str) -> str:
        """Prompt for password when credentials file exists."""
        logger.info("Enter master password to unlock credentials")
        print("Tip: After successful login, your password will be saved to macOS Keychain\n")

        password = getpass.getpass("Master password: ")

        if not self._verify_password(password):
            raise RuntimeError("Failed to decrypt credentials. Wrong password?")

        self._save_to_keychain(keychain, account, password)
        return password

    def _get_password_fallback(self, logger) -> str:
        """Fallback password entry for non-macOS or keychain unavailable."""
        credentials_file = self.storage_dir / "credentials.enc"

        if credentials_file.exists():
            password = getpass.getpass("Enter master password: ")
            if not self._verify_password(password):
                raise RuntimeError("Failed to decrypt credentials. Wrong password?")
            return password

        return self._create_new_password(logger)

    def _create_new_password(self, logger) -> str:
        """Create new master password."""
        logger.info("Creating new credential store", emoji="🔐")
        print("\nCreate a master password to secure your credentials\n")

        password = getpass.getpass("Enter new master password: ")
        confirm = getpass.getpass("Confirm master password: ")

        if password != confirm:
            raise ValueError("Passwords do not match")
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")

        return password

    def _save_to_keychain(self, keychain, account: str, password: str):
        """Save password to keychain with biometric."""
        print("\nSaving password to macOS Keychain...")
        print("IMPORTANT: When the system prompt appears, click 'Always Allow'\n")

        if keychain.store_password(account, password, use_biometric=True):
            self.logger.info("Master password saved to Keychain")
            print("Password saved! If you clicked 'Always Allow', future access is automatic.\n")

    def _verify_password(self, password: str) -> bool:
        """Verify password works with encrypted credentials."""
        try:
            test_cipher = create_cipher(password, get_or_create_salt(self.salt_file))
            encrypted_data = (self.storage_dir / "credentials.enc").read_bytes()
            test_cipher.decrypt(encrypted_data)
            return True
        except Exception:
            return False

    def _load_credentials(self) -> Dict[str, Credential]:
        """Load credentials from storage."""
        data = self._storage.load()
        credentials = {}
        for name, cred_dict in data.items():
            credentials[name] = Credential.from_dict(cred_dict)
        return credentials

    def _save_credentials(self):
        """Save credentials to storage."""
        data = {name: cred.to_dict() for name, cred in self._credentials.items()}
        self._storage.save(data)

    def store_credential(
        self,
        name: str,
        credential_type: CredentialType,
        provider: str,
        value: str,
        username: Optional[str] = None,
        email: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Credential:
        """Store a credential securely."""
        now = datetime.now()

        credential = Credential(
            name=name,
            credential_type=credential_type,
            provider=provider,
            value=value,
            username=username,
            email=email,
            expires_at=expires_at,
            metadata=metadata or {},
            created_at=now,
            updated_at=now,
        )

        self._credentials[name] = credential
        self._save_credentials()

        self.logger.info(
            "Credential stored",
            name=name,
            provider=provider,
            credential_type=credential_type.value,
            emoji="🔐",
        )

        return credential

    def get_credential(self, name: str) -> Optional[Credential]:
        """Get a credential by name."""
        credential = self._credentials.get(name)
        if credential:
            self.logger.debug(
                "Credential retrieved", name=name, provider=credential.provider, emoji="🔓"
            )
        return credential

    def get_credentials_by_provider(self, provider: str) -> List[Credential]:
        """Get all credentials for a provider."""
        return [cred for cred in self._credentials.values() if cred.provider == provider]

    def get_credentials_by_type(self, credential_type: CredentialType) -> List[Credential]:
        """Get all credentials of a specific type."""
        return [
            cred for cred in self._credentials.values() if cred.credential_type == credential_type
        ]

    def update_credential(
        self,
        name: str,
        value: Optional[str] = None,
        username: Optional[str] = None,
        email: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Credential]:
        """Update an existing credential."""
        credential = self._credentials.get(name)
        if not credential:
            return None

        if value is not None:
            credential.value = value
        if username is not None:
            credential.username = username
        if email is not None:
            credential.email = email
        if expires_at is not None:
            credential.expires_at = expires_at
        if metadata is not None:
            credential.metadata = metadata

        credential.updated_at = datetime.now()

        self._save_credentials()

        self.logger.info("Credential updated", name=name, provider=credential.provider, emoji="♻️")

        return credential

    def delete_credential(self, name: str) -> bool:
        """Delete a credential."""
        if name in self._credentials:
            credential = self._credentials[name]
            del self._credentials[name]
            self._save_credentials()

            self.logger.info(
                "Credential deleted", name=name, provider=credential.provider, emoji="🗑️"
            )

            return True
        return False

    def list_credentials(self) -> List[str]:
        """List all credential names."""
        return list(self._credentials.keys())

    def clear_expired(self) -> int:
        """Remove all expired credentials."""
        expired = [name for name, cred in self._credentials.items() if cred.is_expired()]

        for name in expired:
            del self._credentials[name]

        if expired:
            self._save_credentials()
            self.logger.info("Expired credentials cleared", count=len(expired), emoji="🧹")

        return len(expired)

    def export_for_env(self, name: str) -> Optional[Dict[str, str]]:
        """Export credential as environment variables."""
        credential = self.get_credential(name)
        if not credential:
            return None

        env_vars = {}

        if credential.email:
            env_vars["AUTH_EMAIL"] = credential.email
        if credential.username:
            env_vars["AUTH_USERNAME"] = credential.username

        if credential.credential_type == CredentialType.PASSWORD:
            env_vars["AUTH_PASSWORD"] = credential.value
        elif credential.credential_type == CredentialType.API_TOKEN:
            env_vars["AUTH_TOKEN"] = credential.value
        elif credential.credential_type == CredentialType.OAUTH_TOKEN:
            env_vars["AUTH_OAUTH_TOKEN"] = credential.value
        elif credential.credential_type == CredentialType.TOTP_SECRET:
            env_vars["AUTH_TOTP_SECRET"] = credential.value

        return env_vars


_credential_manager: Optional[CredentialManager] = None


def get_credential_manager(
    master_password: Optional[str] = None, force_new: bool = False
) -> CredentialManager:
    """Get the global credential manager instance."""
    global _credential_manager

    if force_new or _credential_manager is None:
        _credential_manager = CredentialManager(master_password)

    return _credential_manager
