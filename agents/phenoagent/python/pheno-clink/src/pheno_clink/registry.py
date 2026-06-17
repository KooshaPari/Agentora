"""
Configuration registry for clink CLI integrations.
"""

from __future__ import annotations

import json
import logging
import shlex
from pathlib import Path
from typing import TYPE_CHECKING

from .constants import (
    CONFIG_DIR,
    DEFAULT_TIMEOUT_SECONDS,
    INTERNAL_DEFAULTS,
    PROJECT_ROOT,
    USER_CONFIG_DIR,
    CLIInternalDefaults,
)
from .models import (
    CLIClientConfig,
    CLIRoleConfig,
    ResolvedCLIClient,
    ResolvedCLIRole,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

try:
    from pheno.config import get_config as get_pheno_config
    from pheno.core.utils.env import get_env as _get_env

    PHENO_CONFIG_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    import os

    def _get_env(key: str, default: str | None = None) -> str | None:
        return os.environ.get(key, default)

    PHENO_CONFIG_AVAILABLE = False

    def get_pheno_config():
        class _ConfigMock:
            def get(self, key, default=None):
                return default

        return _ConfigMock()


def _read_json_file(path: str) -> dict:
    """
    Read JSON file with proper error handling.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Failed to read JSON file {path}: {exc}") from exc


logger = logging.getLogger("clink.registry")

CONFIG_ENV_VAR = "CLI_CLIENTS_CONFIG_PATH"


# Dynamic config path based on pheno-sdk availability
def get_clink_config_env_var() -> str:
    """
    Get the environment variable name for CLI clients config based on availability.
    """
    if PHENO_CONFIG_AVAILABLE:
        pheno_config = get_pheno_config()
        # Check if a custom config path is set in pheno config
        custom_path = pheno_config.get("clink_clients_config_path", None)
        return custom_path if custom_path else CONFIG_ENV_VAR
    return CONFIG_ENV_VAR


class RegistryLoadError(RuntimeError):
    """
    Raised when configuration files are invalid or missing critical data.
    """


class ClinkRegistry:
    """
    Loads CLI client definitions and exposes them for schema generation/runtime use.
    """

    def __init__(self) -> None:
        self._clients: dict[str, ResolvedCLIClient] = {}
        self._load()

    def _load(self) -> None:
        self._clients.clear()
        for config_path in self._iter_config_files():
            try:
                data = _read_json_file(str(config_path))
            except json.JSONDecodeError as exc:
                raise RegistryLoadError(f"Invalid JSON in {config_path}: {exc}") from exc

            if not data:
                logger.debug("Skipping empty configuration file: %s", config_path)
                continue

            config = CLIClientConfig.model_validate(data)
            resolved = self._resolve_config(config, source_path=config_path)
            key = resolved.name.lower()
            if key in self._clients:
                logger.info(
                    "Overriding CLI configuration for '%s' from %s", resolved.name, config_path,
                )
            else:
                logger.debug(
                    "Loaded CLI configuration for '%s' from %s", resolved.name, config_path,
                )
            self._clients[key] = resolved

        if not self._clients:
            raise RegistryLoadError(
                "No CLI clients configured. Ensure conf/cli_clients contains at least one definition or set "
                f"{CONFIG_ENV_VAR}.",
            )

    def reload(self) -> None:
        """
        Reload configurations from disk.
        """

        self._load()

    def list_clients(self) -> list[str]:
        return sorted(client.name for client in self._clients.values())

    def list_roles(self, cli_name: str) -> list[str]:
        config = self.get_client(cli_name)
        return sorted(config.roles.keys())

    def get_client(self, cli_name: str) -> ResolvedCLIClient:
        key = cli_name.lower()
        if key not in self._clients:
            available = ", ".join(self.list_clients())
            raise KeyError(f"CLI '{cli_name}' is not configured. Available clients: {available}")
        return self._clients[key]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _iter_config_files(self) -> Iterable[Path]:
        """
        Iterate over all configuration files in search paths.
        """
        search_paths = self._build_search_paths()
        seen = set()

        for base_path in search_paths:
            if not base_path or base_path in seen:
                continue
            seen.add(base_path)

            yield from self._yield_config_files_from_path(base_path)

    def _build_search_paths(self) -> list[Path]:
        """
        Build list of search paths for configuration files.
        """
        search_paths = [CONFIG_DIR]

        # Add pheno-sdk config path if available
        pheno_path = self._get_pheno_config_path()
        if pheno_path:
            search_paths.append(pheno_path)

        # Add environment-specified path
        env_path = self._get_env_config_path()
        if env_path:
            search_paths.append(env_path)

        search_paths.append(USER_CONFIG_DIR)
        return search_paths

    def _get_pheno_config_path(self) -> Path | None:
        """
        Get pheno-sdk configuration path if available.
        """
        if not PHENO_CONFIG_AVAILABLE:
            return None

        pheno_config = get_pheno_config()
        pheno_clink_dir = pheno_config.get("clink_config_dir", None)
        return Path(pheno_clink_dir) if pheno_clink_dir else None

    def _get_env_config_path(self) -> Path | None:
        """
        Get environment-specified configuration path.
        """
        env_path_raw = _get_env(get_clink_config_env_var())
        return Path(env_path_raw).expanduser() if env_path_raw else None

    def _yield_config_files_from_path(self, base_path: Path) -> Iterable[Path]:
        """
        Yield configuration files from a single path.
        """
        if not base_path.exists():
            logger.debug("Configuration path does not exist: %s", base_path)
            return

        if base_path.is_file() and base_path.suffix.lower() == ".json":
            yield base_path
            return

        if base_path.is_dir():
            for path in sorted(base_path.glob("*.json")):
                if path.is_file():
                    yield path

    def _resolve_config(self, raw: CLIClientConfig, *, source_path: Path) -> ResolvedCLIClient:
        if not raw.name:
            raise RegistryLoadError(f"CLI configuration at {source_path} is missing a 'name' field")

        normalized_name = raw.name.strip()
        internal_defaults = INTERNAL_DEFAULTS.get(normalized_name.lower())
        if internal_defaults is None:
            raise RegistryLoadError(f"CLI '{raw.name}' is not supported by clink")

        executable = self._resolve_executable(raw, internal_defaults, source_path)

        internal_args = list(internal_defaults.additional_args) if internal_defaults else []
        config_args = list(raw.additional_args)

        timeout_seconds = raw.timeout_seconds or (
            internal_defaults.timeout_seconds if internal_defaults else DEFAULT_TIMEOUT_SECONDS
        )

        parser_name = internal_defaults.parser
        if not parser_name:
            raise RegistryLoadError(
                f"CLI '{raw.name}' must define a parser either in configuration or internal defaults",
            )

        runner_name = internal_defaults.runner if internal_defaults else None

        env = self._merge_env(raw, internal_defaults)
        working_dir = self._resolve_optional_path(raw.working_dir, source_path.parent)
        roles = self._resolve_roles(raw, internal_defaults, source_path)

        output_to_file = raw.output_to_file

        return ResolvedCLIClient(
            name=normalized_name,
            executable=executable,
            internal_args=internal_args,
            config_args=config_args,
            env=env,
            timeout_seconds=int(timeout_seconds),
            parser=parser_name,
            runner=runner_name,
            roles=roles,
            output_to_file=output_to_file,
            working_dir=working_dir,
        )

    def _resolve_executable(
        self,
        raw: CLIClientConfig,
        internal_defaults: CLIInternalDefaults | None,
        source_path: Path,
    ) -> list[str]:
        command = raw.command
        if not command:
            raise RegistryLoadError(f"CLI '{raw.name}' must specify a 'command' in configuration")
        return shlex.split(command)

    def _merge_env(
        self,
        raw: CLIClientConfig,
        internal_defaults: CLIInternalDefaults | None,
    ) -> dict[str, str]:
        merged: dict[str, str] = {}
        if internal_defaults and internal_defaults.env:
            merged.update(internal_defaults.env)
        merged.update(raw.env)
        return merged

    def _resolve_roles(
        self,
        raw: CLIClientConfig,
        internal_defaults: CLIInternalDefaults | None,
        source_path: Path,
    ) -> dict[str, ResolvedCLIRole]:
        roles: dict[str, CLIRoleConfig] = dict(raw.roles)

        default_role_prompt = internal_defaults.default_role_prompt if internal_defaults else None
        if "default" not in roles:
            roles["default"] = CLIRoleConfig(prompt_path=default_role_prompt)
        elif roles["default"].prompt_path is None and default_role_prompt:
            roles["default"].prompt_path = default_role_prompt

        resolved: dict[str, ResolvedCLIRole] = {}
        for role_name, role_config in roles.items():
            prompt_path_str = role_config.prompt_path or default_role_prompt
            if not prompt_path_str:
                raise RegistryLoadError(
                    f"Role '{role_name}' for CLI '{raw.name}' must define a prompt_path",
                )
            prompt_path = self._resolve_prompt_path(prompt_path_str, source_path.parent)
            resolved[role_name] = ResolvedCLIRole(
                name=role_name,
                prompt_path=prompt_path,
                role_args=list(role_config.role_args),
                description=role_config.description,
            )
        return resolved

    def _resolve_prompt_path(self, prompt_path: str, base_dir: Path) -> Path:
        resolved = self._resolve_path(prompt_path, base_dir)
        if not resolved.exists():
            raise RegistryLoadError(f"Prompt file not found: {resolved}")
        return resolved

    def _resolve_optional_path(self, candidate: str | None, base_dir: Path) -> Path | None:
        if not candidate:
            return None
        return self._resolve_path(candidate, base_dir)

    def _resolve_path(self, candidate: str, base_dir: Path) -> Path:
        path = Path(candidate)
        if path.is_absolute():
            return path

        candidate_path = (base_dir / path).resolve()
        if candidate_path.exists():
            return candidate_path

        return (PROJECT_ROOT / path).resolve()


_REGISTRY: ClinkRegistry | None = None


def get_registry() -> ClinkRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = ClinkRegistry()
    return _REGISTRY
