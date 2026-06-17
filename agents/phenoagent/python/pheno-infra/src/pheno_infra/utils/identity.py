"""Project identity utilities for KInfra.

Provides a stable project identifier and deterministic small offsets for deriving per-
project default ports.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path


def get_project_id(default: str | None = None) -> str:
    """Return a stable project identifier.

    Priority:
    1) KINFRA_PROJECT_ID env var
    2) Git repo root or working directory folder name
    3) Provided default or "default"
    """
    env_id = os.environ.get("KINFRA_PROJECT_ID")
    if env_id:
        return _sanitize(env_id)

    # Try repo root marker
    cwd = Path.cwd()
    for parent in [cwd, *list(cwd.parents)]:
        if (parent / ".git").exists():
            return _sanitize(parent.name)
    return _sanitize(default or cwd.name or "default")


def stable_offset(project_id: str, modulo: int = 50) -> int:
    """Compute a small, deterministic offset for the given project id.

    Defaults to modulo=50 to keep offsets in a compact range.
    """
    h = hashlib.sha1(project_id.encode("utf-8")).hexdigest()
    return int(h[:6], 16) % max(1, modulo)


def base_ports_from_env(default_fallback: int = 9000, default_proxy: int = 9100) -> tuple[int, int]:
    """
    Read base fallback/proxy ports from env if provided, else defaults.
    """
    fb = int(os.environ.get("KINFRA_BASE_FALLBACK_PORT", default_fallback))
    px = int(os.environ.get("KINFRA_BASE_PROXY_PORT", default_proxy))
    return fb, px


def _sanitize(text: str) -> str:
    return "".join(ch for ch in text.strip().lower() if ch.isalnum() or ch in ("-", "_"))[:64]
