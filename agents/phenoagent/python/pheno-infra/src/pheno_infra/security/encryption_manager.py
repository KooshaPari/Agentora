"""
Symmetric encryption utilities built on top of cryptography's Fernet.

The manager supports key rotation by leveraging MultiFernet and exposes a small
API surface that is simple to integrate with application services.
"""

from __future__ import annotations

import base64
import os
from typing import TYPE_CHECKING, Union

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

KeySource = Union[str, bytes]


class EncryptionError(RuntimeError):
    """Raised when encryption or decryption fails."""


class EncryptionManager:
    """
    Lightweight wrapper around Fernet with optional key rotation.

    Parameters
    ----------
    key:
        Primary key used for encryption. When omitted, attempts to read from
        the ``ENCRYPTION_KEY`` environment variable or automatically generates
        a new key.
    old_keys:
        Optional iterable of previous keys that should remain valid for
        decryption. This enables gradual credential rotation.
    ttl:
        Optional time-to-live in seconds for generated tokens. When provided
        the :meth:`decrypt` method will enforce freshness.
    """

    def __init__(
        self,
        key: KeySource | None = None,
        *,
        old_keys: Iterable[KeySource] | None = None,
        ttl: int | None = None,
    ) -> None:
        if ttl is not None and ttl <= 0:
            raise ValueError("ttl must be positive")

        active_key = self._normalise_key(key or os.getenv("ENCRYPTION_KEY"))
        if active_key is None:
            active_key = self.generate_key()

        additional_keys = [
            self._normalise_key(candidate)
            for candidate in old_keys or []
            if self._normalise_key(candidate) is not None
        ]
        self._keys: list[bytes] = [active_key, *filter(None, additional_keys)]
        self._fernet = MultiFernet([Fernet(k) for k in self._keys])
        self._primary_key = active_key
        self._ttl = ttl

    @staticmethod
    def generate_key() -> bytes:
        """Generate a fresh Fernet-compatible key."""

        return Fernet.generate_key()

    @property
    def primary_key(self) -> str:
        """Return the primary key in a URL-safe base64 encoded form."""

        return self._primary_key.decode("utf-8")

    def encrypt(self, data: str | bytes) -> str:
        """Encrypt a string or bytes payload. Returns a base64 encoded string."""

        payload = data.encode("utf-8") if isinstance(data, str) else data
        try:
            token = self._fernet.encrypt(payload)
        except Exception as exc:  # pragma: no cover - cryptography edge cases
            raise EncryptionError("failed to encrypt payload") from exc
        return token.decode("utf-8")

    def decrypt(self, token: str | bytes) -> bytes:
        """Decrypt a token and return the raw bytes."""

        payload = token.encode("utf-8") if isinstance(token, str) else token
        try:
            return self._fernet.decrypt(payload, ttl=self._ttl)
        except InvalidToken as exc:
            raise EncryptionError("invalid or expired encryption token") from exc
        except Exception as exc:  # pragma: no cover - unexpected library errors
            raise EncryptionError("failed to decrypt payload") from exc

    def decrypt_text(self, token: str | bytes, encoding: str = "utf-8") -> str:
        """Convenience wrapper around :meth:`decrypt` returning a decoded string."""

        return self.decrypt(token).decode(encoding)

    def rotate_key(self, new_key: KeySource | None = None) -> str:
        """
        Rotate the active encryption key while keeping historical keys valid.

        The newly generated key becomes primary while existing keys are retained
        for decryption, enabling seamless rotation without downtime.
        """

        rotated_key = self._normalise_key(new_key) or self.generate_key()
        self._keys.insert(0, rotated_key)
        self._fernet = MultiFernet([Fernet(k) for k in self._keys])
        self._primary_key = rotated_key
        return rotated_key.decode("utf-8")

    def export_keys(self) -> Sequence[str]:
        """Return all managed keys (primary first) as strings."""

        return [key.decode("utf-8") for key in self._keys]

    def _normalise_key(self, key: KeySource | None) -> bytes | None:
        if key is None:
            return None
        candidate = key if isinstance(key, bytes) else key.encode("utf-8")

        try:
            Fernet(candidate)  # Validate key format
        except ValueError:
            try:
                # Support keys that are raw 32-byte secrets but not yet base64 encoded.
                candidate = base64.urlsafe_b64encode(candidate)
                Fernet(candidate)
            except ValueError as exc:
                raise EncryptionError("invalid encryption key material") from exc
        return candidate


__all__ = ["EncryptionError", "EncryptionManager"]
