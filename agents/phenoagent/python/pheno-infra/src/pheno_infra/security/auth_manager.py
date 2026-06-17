"""
JWT authentication helpers wrapping PyJWT with opinionated defaults.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import jwt
from jwt import InvalidTokenError

if TYPE_CHECKING:
    from collections.abc import Mapping, MutableMapping, Sequence


class JWTAuthError(RuntimeError):
    """Raised when JWT operations fail or tokens are unusable."""


class JWTAuthManager:
    """
    Manage JWT access and refresh tokens with lightweight state tracking.

    Parameters
    ----------
    secret:
        Symmetric signing secret used for HMAC algorithms. When omitted the
        manager attempts to load ``JWT_SECRET`` from the environment.
    public_key:
        Optional public key for asymmetric verification (e.g. RS256). When not
        supplied the secret is reused as the verification key.
    algorithm:
        JWT signing algorithm. Defaults to HS256.
    access_ttl:
        Time delta controlling access token lifetime.
    refresh_ttl:
        Time delta controlling refresh token lifetime.
    issuer / audience:
        Optional claims validated and embedded into every token.
    clock_skew:
        Allowed leeway (seconds) when validating token timestamps.
    """

    def __init__(
        self,
        *,
        secret: str | None = None,
        public_key: str | None = None,
        algorithm: str = "HS256",
        access_ttl: timedelta = timedelta(minutes=15),
        refresh_ttl: timedelta = timedelta(days=30),
        issuer: str | None = None,
        audience: str | None = None,
        clock_skew: int = 60,
    ) -> None:
        self._secret = secret or os.getenv("JWT_SECRET")
        if not self._secret:
            raise JWTAuthError(
                "JWT secret not configured. Provide `secret` or set JWT_SECRET env var.",
            )

        self._verify_key = public_key or os.getenv("JWT_PUBLIC_KEY") or self._secret
        self._algorithm = algorithm
        self._access_ttl = access_ttl
        self._refresh_ttl = refresh_ttl
        self._issuer = issuer or os.getenv("JWT_ISSUER")
        self._audience = audience or os.getenv("JWT_AUDIENCE")
        self._clock_skew = clock_skew

        # Track revoked token identifiers and active refresh tokens.
        self._revoked_tokens: set[str] = set()
        self._refresh_store: MutableMapping[str, tuple[str, datetime]] = {}

    # ------------------------------------------------------------------ helpers
    def generate_tokens(
        self,
        subject: str,
        *,
        claims: Mapping[str, Any] | None = None,
        include_refresh: bool = True,
    ) -> dict[str, str]:
        """Generate a new access token (and refresh token when requested)."""

        access_token = self._encode_token(
            subject=subject,
            ttl=self._access_ttl,
            token_type="access",
            extra_claims=claims,
        )

        if not include_refresh:
            return {"access_token": access_token}

        refresh_token = self._encode_token(
            subject=subject,
            ttl=self._refresh_ttl,
            token_type="refresh",
            extra_claims=claims,
        )

        refresh_payload = self.decode_token(refresh_token, verify_exp=False)
        self._refresh_store[refresh_payload["jti"]] = (
            refresh_token,
            datetime.fromtimestamp(refresh_payload["exp"], tz=UTC),
        )

        return {"access_token": access_token, "refresh_token": refresh_token}

    def create_access_token(
        self, subject: str, *, claims: Mapping[str, Any] | None = None,
    ) -> str:
        """Generate a standalone access token (no refresh)."""

        return self._encode_token(
            subject=subject,
            ttl=self._access_ttl,
            token_type="access",
            extra_claims=claims,
        )

    def refresh_access_token(self, refresh_token: str) -> dict[str, str]:
        """Exchange a refresh token for a new pair of tokens with rotation."""

        payload = self.decode_token(refresh_token)
        if payload.get("typ") != "refresh":
            raise JWTAuthError("provided token is not a refresh token")

        jti = payload["jti"]
        stored = self._refresh_store.get(jti)
        if not stored or stored[0] != refresh_token:
            raise JWTAuthError("refresh token is no longer valid (rotated or revoked)")

        # Rotate refresh token to mitigate replay attacks.
        self.revoke_token(refresh_token)
        return self.generate_tokens(payload["sub"], claims=self._filter_claims(payload))

    def decode_token(
        self,
        token: str,
        *,
        verify_exp: bool = True,
        required_claims: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        """Decode and validate a token, returning its payload."""

        options = {"verify_exp": verify_exp}
        try:
            payload = jwt.decode(
                token,
                self._verify_key,
                algorithms=[self._algorithm],
                audience=self._audience,
                issuer=self._issuer,
                leeway=self._clock_skew,
                options=options,
            )
        except InvalidTokenError as exc:
            raise JWTAuthError("invalid JWT token") from exc

        if payload.get("jti") in self._revoked_tokens:
            raise JWTAuthError("token has been revoked")

        for claim in required_claims or []:
            if claim not in payload:
                raise JWTAuthError(f"missing required claim: {claim}")

        return payload

    def revoke_token(self, token: str) -> None:
        """Invalidate a token immediately."""

        try:
            payload = self.decode_token(token, verify_exp=False)
        except JWTAuthError:
            # When a token cannot be decoded, revocation is a no-op.
            return

        jti = payload.get("jti")
        if jti:
            self._revoked_tokens.add(jti)
            self._refresh_store.pop(jti, None)

    def is_token_revoked(self, token: str) -> bool:
        """Check whether a token has already been revoked."""

        try:
            payload = self.decode_token(token, verify_exp=False)
        except JWTAuthError:
            return True
        return payload.get("jti") in self._revoked_tokens

    # ------------------------------------------------------------ internal utils
    def _encode_token(
        self,
        *,
        subject: str,
        ttl: timedelta,
        token_type: str,
        extra_claims: Mapping[str, Any] | None = None,
    ) -> str:
        now = datetime.now(tz=UTC)
        exp = now + ttl
        payload: dict[str, Any] = {
            "iss": self._issuer,
            "aud": self._audience,
            "sub": subject,
            "iat": int(now.timestamp()),
            "nbf": int((now - timedelta(seconds=self._clock_skew)).timestamp()),
            "exp": int(exp.timestamp()),
            "jti": uuid.uuid4().hex,
            "typ": token_type,
        }

        # Remove optional claims that are None to avoid validation issues.
        payload = {key: value for key, value in payload.items() if value is not None}

        if extra_claims:
            payload.update(extra_claims)

        try:
            token = jwt.encode(payload, self._secret, algorithm=self._algorithm)
        except Exception as exc:  # pragma: no cover - PyJWT edge cases
            raise JWTAuthError("failed to encode JWT token") from exc
        return token

    def _filter_claims(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Filter standard claims from payload so custom ones can be reused."""

        exclusions = {"iss", "aud", "sub", "iat", "nbf", "exp", "jti", "typ"}
        return {key: value for key, value in payload.items() if key not in exclusions}


__all__ = ["JWTAuthError", "JWTAuthManager"]
