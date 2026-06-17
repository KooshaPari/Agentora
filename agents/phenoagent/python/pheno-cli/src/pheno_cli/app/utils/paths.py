"""
Path utilities for Pheno-CLI.
"""

import os
from pathlib import Path


def get_user_config_dir() -> Path:
    """
    Get user configuration directory.
    """
    if os.name == "nt":  # Windows
        config_dir = Path(os.environ.get("APPDATA", "~")) / "pheno"
    else:  # Unix-like
        config_dir = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")) / "pheno"

    return config_dir.expanduser()


def get_user_data_dir() -> Path:
    """
    Get user data directory.
    """
    if os.name == "nt":  # Windows
        data_dir = Path(os.environ.get("LOCALAPPDATA", "~")) / "pheno"
    else:  # Unix-like
        data_dir = Path(os.environ.get("XDG_DATA_HOME", "~/.local/share")) / "pheno"

    return data_dir.expanduser()


def get_user_cache_dir() -> Path:
    """
    Get user cache directory.
    """
    if os.name == "nt":  # Windows
        cache_dir = Path(os.environ.get("LOCALAPPDATA", "~")) / "pheno" / "cache"
    else:  # Unix-like
        cache_dir = Path(os.environ.get("XDG_CACHE_HOME", "~/.cache")) / "pheno"

    return cache_dir.expanduser()
