"""
Password management utilities for secure password hashing and verification.

The implementation prefers bcrypt when the optional dependency is available.
When bcrypt cannot be imported (e.g. minimal environments), the manager
automatically falls back to PBKDF2-HMAC using SHA-256.
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
from dataclasses import dataclass

try:
    import bcrypt  # type: ignore
except ImportError:  # pragma: no cover - fallback path exercised in tests
    bcrypt = None  # type: ignore


DEFAULT_BCRYPT_ROUNDS = 12
PBKDF2_ITERATIONS = 390_000  # Python's recommended default for SHA-256
PBKDF2_PREFIX = "pbkdf2_sha256"


@dataclass(frozen=True)
class PasswordHashMetadata:
    """Metadata describing the hashing strategy embedded in the stored value."""

    scheme: str
    rounds: int | None = None
    salt: str | None = None


class PasswordHashError(ValueError):
    """Raised when a password hash is malformed or unsupported."""


class PasswordManager:
    """Consistent interface for hashing and verifying passwords within the server."""

    def __init__(self, bcrypt_rounds: int = DEFAULT_BCRYPT_ROUNDS) -> None:
        if bcrypt_rounds < 4:
            raise ValueError("bcrypt_rounds must be >= 4")
        self._bcrypt_rounds = bcrypt_rounds

    @property
    def using_bcrypt(self) -> bool:
        """Return True when bcrypt is available and will be used."""

        return bcrypt is not None

    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt when possible, otherwise PBKDF2-HMAC.

        The returned value encodes the strategy so :meth:`verify_password`
        can route to the correct verifier automatically.
        """

        if not password:
            raise ValueError("password cannot be empty")

        if self.using_bcrypt:
            salt = bcrypt.gensalt(rounds=self._bcrypt_rounds)
            hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
            return hashed.decode("utf-8")

        return self._hash_with_pbkdf2(password)

    def verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify a plaintext password against a stored hash."""

        if not stored_hash:
            raise PasswordHashError("stored hash is empty")

        metadata = self._parse_hash_metadata(stored_hash)

        if metadata.scheme.startswith("$2"):
            if not self.using_bcrypt:
                raise PasswordHashError(
                    "bcrypt hash encountered but bcrypt library is unavailable",
                )
            return bool(
                bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8")),
            )

        if metadata.scheme == PBKDF2_PREFIX:
            assert metadata.salt is not None
            return self._verify_pbkdf2(password, stored_hash, metadata)

        raise PasswordHashError(f"Unsupported password hash scheme: {metadata.scheme}")

    def needs_rehash(self, stored_hash: str) -> bool:
        """
        Determine whether the stored hash should be regenerated.

        This occurs when bcrypt cost factors are lower than current defaults
        or when PBKDF2 is in use but bcrypt is now available.
        """

        metadata = self._parse_hash_metadata(stored_hash)

        if metadata.scheme.startswith("$2"):
            if not self.using_bcrypt:
                return False
            # bcrypt cost factor is encoded after the prefix, e.g. $2b$12$...
            try:
                factor = int(stored_hash.split("$")[2])
            except (IndexError, ValueError) as exc:
                raise PasswordHashError("invalid bcrypt hash format") from exc
            return factor < self._bcrypt_rounds

        if metadata.scheme == PBKDF2_PREFIX:
            # Prefer rehashing with bcrypt when available.
            return self.using_bcrypt or (
                metadata.rounds is not None and metadata.rounds < PBKDF2_ITERATIONS
            )

        raise PasswordHashError(f"Unsupported password hash scheme: {metadata.scheme}")

    def generate_salt(self, size: int = 16) -> str:
        """Generate a cryptographically secure salt encoded as URL-safe base64."""

        if size < 8:
            raise ValueError("salt size must be at least 8 bytes")
        return base64.urlsafe_b64encode(os.urandom(size)).decode("utf-8")

    def _hash_with_pbkdf2(self, password: str) -> str:
        salt_bytes = secrets.token_bytes(16)
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt_bytes,
            PBKDF2_ITERATIONS,
        )
        return "{}${}${}${}".format(
            PBKDF2_PREFIX,
            PBKDF2_ITERATIONS,
            base64.urlsafe_b64encode(salt_bytes).decode("utf-8"),
            base64.urlsafe_b64encode(dk).decode("utf-8"),
        )

    def _verify_pbkdf2(
        self, password: str, stored_hash: str, metadata: PasswordHashMetadata,
    ) -> bool:
        try:
            _, iterations, salt, digest = stored_hash.split("$", 3)
        except ValueError as exc:
            raise PasswordHashError("invalid PBKDF2 hash format") from exc

        expected = base64.urlsafe_b64decode(digest.encode("utf-8"))
        computed = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            base64.urlsafe_b64decode(salt.encode("utf-8")),
            int(iterations),
        )
        return secrets.compare_digest(expected, computed)

    def _parse_hash_metadata(self, stored_hash: str) -> PasswordHashMetadata:
        if stored_hash.startswith(f"{PBKDF2_PREFIX}$"):
            parts = stored_hash.split("$", 3)
            if len(parts) != 4:
                raise PasswordHashError("invalid PBKDF2 hash format")
            return PasswordHashMetadata(
                scheme=PBKDF2_PREFIX,
                rounds=int(parts[1]),
                salt=parts[2],
            )

        if stored_hash.startswith(("$2a$", "$2b$")):
            return PasswordHashMetadata(scheme=stored_hash[:4])

        return PasswordHashMetadata(scheme=stored_hash.split("$", 1)[0])


__all__ = ["PasswordHashError", "PasswordHashMetadata", "PasswordManager"]

