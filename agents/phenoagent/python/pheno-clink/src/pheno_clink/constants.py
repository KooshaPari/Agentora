"""
Internal defaults and constants for clink.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_TIMEOUT_SECONDS = 1800
DEFAULT_STREAM_LIMIT = 10 * 1024 * 1024  # 10MB per stream


def _discover_project_root() -> Path:
    """
    Best-effort discovery of the consuming project's root directory.
    """

    env_candidates = [
        os.environ.get("CLINK_PROJECT_ROOT"),
        os.environ.get("ZEN_MCP_PROJECT_ROOT"),
        os.environ.get("ZEN_MCP_ROOT"),
    ]
    for raw in env_candidates:
        if raw:
            candidate = Path(raw).expanduser()
            if candidate.exists():
                return candidate

    probable_locations: list[Path] = []
    try:
        probable_locations.append(Path.cwd())
    except Exception:  # pragma: no cover - defensive
        pass

    module_path = Path(__file__).resolve()
    probable_locations.extend(module_path.parents[:5])

    for base in probable_locations:
        if not base:
            continue
        prompts_dir = base / "systemprompts" / "clink"
        conf_dir = base / "conf" / "cli_clients"
        if prompts_dir.exists() or conf_dir.exists():
            return base

    return module_path.parent.parent


PROJECT_ROOT = _discover_project_root()
BUILTIN_PROMPTS_DIR = PROJECT_ROOT / "systemprompts" / "clink"
CONFIG_DIR = PROJECT_ROOT / "conf" / "cli_clients"
USER_CONFIG_DIR = Path.home() / ".zen" / "cli_clients"


@dataclass(frozen=True)
class CLIInternalDefaults:
    """
    Internal defaults applied to a CLI client during registry load.
    """

    parser: str
    additional_args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    default_role_prompt: str | None = None
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    runner: str | None = None


INTERNAL_DEFAULTS: dict[str, CLIInternalDefaults] = {
    "gemini": CLIInternalDefaults(
        parser="gemini_json",
        additional_args=["-o", "json"],
        default_role_prompt="systemprompts/clink/default.txt",
        runner="gemini",
    ),
    "codex": CLIInternalDefaults(
        parser="codex_jsonl",
        additional_args=["exec"],
        default_role_prompt="systemprompts/clink/default.txt",
        runner="codex",
    ),
    "claude": CLIInternalDefaults(
        parser="claude_json",
        additional_args=["--print", "--output-format", "json"],
        default_role_prompt="systemprompts/clink/default.txt",
        runner="claude",
    ),
}
