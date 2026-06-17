"""
Version management for Pheno-CLI.
"""

import importlib.metadata


def get_version() -> str:
    """
    Get the current version of pheno-cli.
    """
    try:
        return importlib.metadata.version("pheno-cli")
    except importlib.metadata.PackageNotFoundError:
        # Fallback for development
        return "1.0.0-dev"
