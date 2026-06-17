"""
Supabase client utilities shared by Supabase adapters.
"""

from __future__ import annotations

import hashlib
import os
import time

from supabase import Client, create_client


class MissingSupabaseConfig(RuntimeError):
    """
    Raised when Supabase configuration is missing or invalid.
    """



_client_cache: dict[str, tuple[Client, float]] = {}
_CACHE_TTL = 300
_MAX_CACHE_SIZE = 100


def get_supabase(access_token: str | None = None) -> Client:
    """
    Return a cached Supabase client using the supplied access token.
    """
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        raise MissingSupabaseConfig("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")

    cache_key = hashlib.md5(access_token.encode()).hexdigest()[:16] if access_token else "service"
    now = time.time()
    if cache_key in _client_cache:
        client, created = _client_cache[cache_key]
        if now - created < _CACHE_TTL:
            return client
        del _client_cache[cache_key]

    client = create_client(url, key)
    if access_token:
        client.postgrest.auth(access_token)

    _client_cache[cache_key] = (client, now)
    if len(_client_cache) > _MAX_CACHE_SIZE:
        _client_cache.clear()

    return client
