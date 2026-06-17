"""Environment Variable Management Utilities.

Provides cascading environment loading and parsing utilities.
"""

import os
from pathlib import Path


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse .env file into dictionary.

    Handles:
    - Comments (lines starting with #)
    - Quoted values (single and double quotes)
    - Empty lines
    - Key=value format

    Args:
        path: Path to .env file

    Returns:
        Dictionary of environment variables
    """
    env_vars = {}

    if not path.exists():
        return env_vars

    try:
        with open(path) as f:
            for line in f:
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                # Must contain =
                if "=" not in line:
                    continue

                # Split on first =
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                # Remove surrounding quotes
                if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]

                env_vars[key] = value

    except Exception as e:
        # Log warning but don't fail
        import logging

        logging.getLogger(__name__).warning(f"Failed to parse {path}: {e}")

    return env_vars


def load_env_cascade(
    root_dirs: list[Path],
    service_env_file: Path | None = None,
    base_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """Load environment variables with cascade priority.

    Priority (highest to lowest):
    1. base_env (passed explicitly, often os.environ)
    2. Root directory .env files (in order)
    3. Service-specific .env file

    Args:
        root_dirs: List of root directories to check for .env files
        service_env_file: Optional service-specific .env file
        base_env: Base environment to start with (defaults to os.environ)

    Returns:
        Merged environment dictionary

    Example:
        >>> env = load_env_cascade(
        ...     root_dirs=[Path("/app"), Path("/app/services/api")],
        ...     service_env_file=Path("/app/services/api/.env.local")
        ... )
    """
    # Start with base environment (usually system env)
    env = dict(base_env) if base_env else os.environ.copy()

    # Load root .env files in order
    for root_dir in root_dirs:
        root_env_file = root_dir / ".env"
        if root_env_file.exists():
            env.update(parse_env_file(root_env_file))

    # Load service-specific .env last (highest priority)
    if service_env_file and service_env_file.exists():
        env.update(parse_env_file(service_env_file))

    return env


def merge_env_configs(
    *env_dicts: dict[str, str], base_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """Merge multiple environment dictionaries.

    Later dictionaries override earlier ones.

    Args:
        *env_dicts: Variable number of environment dictionaries
        base_env: Base environment (defaults to os.environ)

    Returns:
        Merged environment dictionary
    """
    result = dict(base_env) if base_env else os.environ.copy()

    for env_dict in env_dicts:
        if env_dict:
            result.update(env_dict)

    return result
