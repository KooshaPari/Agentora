"""
Import-linter integration helpers.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pheno.analytics.exceptions import AnalyticsDependencyError

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    from importlinter.application.app import lint_imports  # type: ignore
    from importlinter.domain.helpers import direct_imports_of  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    lint_imports = None
    direct_imports_of = None


def run_import_linter(config_path: Path) -> dict[str, Any]:
    """
    Run import-linter against the provided config file.
    """

    if lint_imports is None:
        raise AnalyticsDependencyError("import-linter", extra="analytics")

    config_path = config_path.resolve()
    logger.debug("import_linter_start", config=str(config_path))
    success = lint_imports(config_filename=str(config_path))
    logger.debug("import_linter_complete", success=success)
    return {"success": success, "config": str(config_path)}


def inspect_direct_imports(module_name: str) -> list[str]:
    """
    Return direct import targets for a module (via import-linter helper).
    """

    if direct_imports_of is None:
        raise AnalyticsDependencyError("import-linter", extra="analytics")

    results = sorted(direct_imports_of(module_name))
    logger.debug("import_linter_direct_imports", module=module_name, count=len(results))
    return results
