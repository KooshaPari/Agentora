"""Environment variable bootstrap for credentials."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from pheno.testing.mcp_qa.logging import get_logger

from ._types import ENV_IMPORT_RULES, Credential


class EnvBootstrap:
    """Imports credentials from environment variables and .env files."""

    def __init__(self, credentials: Dict[str, Credential]):
        self._credentials = credentials
        self._bootstrapped = False
        self.logger = get_logger(__name__)

    def bootstrap_if_needed(self, store_credential, update_credential) -> bool:
        """Run bootstrap if not already done."""
        if self._bootstrapped:
            return False

        env_data = self._collect_env_data()
        if not env_data:
            self._bootstrapped = True
            return False

        self._import_from_rules(env_data, store_credential, update_credential)
        self._bootstrapped = True
        return True

    def _collect_env_data(self) -> Dict[str, str]:
        """Collect environment variables from os.environ and .env files."""
        env_data: Dict[str, str] = {}

        for key, value in os.environ.items():
            if isinstance(value, str) and value:
                env_data[key] = value

        for env_file in self._discover_env_files():
            env_data.update(self._parse_env_file(env_file))

        return env_data

    def _discover_env_files(self) -> List[Path]:
        """Find relevant .env files for credential import."""
        candidates: List[Path] = []

        explicit_files = os.getenv("MCP_QA_ENV_FILES")
        if explicit_files:
            for entry in explicit_files.split(os.pathsep):
                if not entry:
                    continue
                path = Path(entry).expanduser()
                if path.is_file():
                    candidates.append(path)

        explicit_file = os.getenv("MCP_QA_ENV_FILE")
        if explicit_file:
            path = Path(explicit_file).expanduser()
            if path.is_file():
                candidates.append(path)

        search = Path.cwd()
        for _ in range(6):
            for name in (".env", ".env.local"):
                candidate = search / name
                if candidate.is_file():
                    candidates.append(candidate)
            if search.parent == search:
                break
            search = search.parent

        unique: List[Path] = []
        seen: Set[str] = set()
        for path in candidates:
            resolved = path.resolve()
            key = str(resolved)
            if key not in seen:
                unique.append(resolved)
                seen.add(key)

        return unique

    def _parse_env_file(self, path: Path) -> Dict[str, str]:
        """Parse key=value pairs from an env file."""
        data: Dict[str, str] = {}
        try:
            with path.open("r", encoding="utf-8") as handle:
                for raw_line in handle:
                    line = raw_line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if line.lower().startswith("export "):
                        line = line[7:].strip()
                    if "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    if not key:
                        continue
                    if value.startswith('"') and value.endswith('"') and len(value) >= 2:
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'") and len(value) >= 2:
                        value = value[1:-1]
                    if value:
                        data[key] = value
        except Exception:
            return {}
        return data

    def _import_from_rules(self, env_data: Dict[str, str], store_credential, update_credential):
        """Import credentials based on ENV_IMPORT_RULES."""
        for rule in ENV_IMPORT_RULES:
            value = self._first_present(env_data, rule.get("value_keys", []))
            if not value:
                continue

            name = rule["name"]
            provider = rule["provider"]
            credential_type = rule["credential_type"]
            email = self._first_present(env_data, rule.get("email_keys", []))
            username = self._first_present(env_data, rule.get("username_keys", []))

            metadata: Dict[str, Any] = {"source": "env"}
            for meta_key, keys in rule.get("metadata_keys", {}).items():
                meta_value = self._first_present(env_data, keys)
                if meta_value:
                    metadata[meta_key] = meta_value

            existing = self._credentials.get(name)
            if existing:
                update_kwargs: Dict[str, Any] = {}
                if existing.value != value:
                    update_kwargs["value"] = value
                if email and existing.email != email:
                    update_kwargs["email"] = email
                if username and existing.username != username:
                    update_kwargs["username"] = username

                combined_metadata = existing.metadata.copy() if existing.metadata else {}
                metadata_changed = False
                for meta_key, meta_value in metadata.items():
                    if combined_metadata.get(meta_key) != meta_value:
                        combined_metadata[meta_key] = meta_value
                        metadata_changed = True
                if metadata_changed:
                    update_kwargs["metadata"] = combined_metadata

                if update_kwargs:
                    update_credential(name, **update_kwargs)
            else:
                store_credential(
                    name=name,
                    credential_type=credential_type,
                    provider=provider,
                    value=value,
                    username=username,
                    email=email,
                    metadata=metadata,
                )

    @staticmethod
    def _first_present(data: Dict[str, str], keys: Optional[List[str]]) -> Optional[str]:
        """Return the first non-empty value for the provided keys."""
        if not keys:
            return None
        for key in keys:
            if not key:
                continue
            value = data.get(key)
            if isinstance(value, str):
                cleaned = value.strip()
                if cleaned:
                    return cleaned
        return None
