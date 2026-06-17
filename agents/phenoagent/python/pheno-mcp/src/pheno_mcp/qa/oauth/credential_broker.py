"""Simplified credential broker used by MCP QA tests.

The broker stores credential material in-memory and exposes a small API that mirrors the
original package.  It is intentionally lightweight; projects can extend it with
persistence if required.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable


@dataclass
class CapturedCredentials:
    identifier: str
    access_token: str
    refresh_token: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


class UnifiedCredentialBroker:
    """
    In-memory credential store.
    """

    def __init__(self) -> None:
        self._store: dict[str, CapturedCredentials] = {}

    def store(self, credentials: CapturedCredentials) -> None:
        self._store[credentials.identifier] = credentials

    def get(self, identifier: str) -> CapturedCredentials | None:
        return self._store.get(identifier)

    def delete(self, identifier: str) -> None:
        self._store.pop(identifier, None)

    def list(self) -> Iterable[CapturedCredentials]:
        return list(self._store.values())

    # Convenience helpers -------------------------------------------------
    def ensure(self, identifier: str, **metadata: str) -> CapturedCredentials:
        cred = self._store.get(identifier)
        if cred:
            cred.metadata.update(metadata)
            return cred
        cred = CapturedCredentials(identifier=identifier, access_token="", metadata=metadata)
        self.store(cred)
        return cred


__all__ = ["CapturedCredentials", "UnifiedCredentialBroker"]
