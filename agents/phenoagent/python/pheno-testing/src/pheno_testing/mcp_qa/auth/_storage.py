"""Encrypted credential storage with AES-256."""

import base64
import json
import os
from pathlib import Path
from typing import Dict

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from pheno.testing.mcp_qa.logging import get_logger


class CredentialStorage:
    """Handles encrypted storage of credentials."""

    def __init__(self, storage_dir: Path, cipher: Fernet):
        self.storage_dir = storage_dir
        self.cipher = cipher
        self.credentials_file = storage_dir / "credentials.enc"
        self.salt_file = storage_dir / ".salt"
        self.logger = get_logger(__name__)

    def load(self) -> Dict[str, dict]:
        """Load and decrypt credentials from storage."""
        if not self.credentials_file.exists():
            return {}

        encrypted_data = self.credentials_file.read_bytes()
        decrypted_data = self.cipher.decrypt(encrypted_data)
        data = json.loads(decrypted_data.decode())
        return data

    def save(self, credentials: Dict[str, dict]):
        """Encrypt and save credentials to storage."""
        json_data = json.dumps(credentials, indent=2)
        encrypted_data = self.cipher.encrypt(json_data.encode())
        self.credentials_file.write_bytes(encrypted_data)
        self.credentials_file.chmod(0o600)


def create_cipher(master_password: str, salt: bytes) -> Fernet:
    """Create Fernet cipher from master password."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend(),
    )
    key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
    return Fernet(key)


def get_or_create_salt(salt_file: Path) -> bytes:
    """Get existing salt or create new one."""
    if salt_file.exists():
        return salt_file.read_bytes()
    salt = os.urandom(16)
    salt_file.write_bytes(salt)
    salt_file.chmod(0o600)
    return salt
