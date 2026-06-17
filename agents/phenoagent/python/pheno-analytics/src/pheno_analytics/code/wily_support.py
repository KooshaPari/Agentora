"""
Helper utilities for running wily metrics (optional).
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from typing import TYPE_CHECKING

from pheno.analytics.exceptions import AnalyticsDependencyError

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

logger = logging.getLogger(__name__)


def run_wily_report(path: Path, metrics: Iterable[str] | None = None) -> dict[str, str]:
    """
    Run wily build/report and return the captured stdout.
    """

    if shutil.which("wily") is None:
        raise AnalyticsDependencyError("wily", extra="analytics")

    metrics = metrics or ("cyclomatic_complexity", "raw.loc")
    target = path.resolve()
    logger.debug("wily_build_start", path=str(target))
    subprocess.run(["wily", "build", str(target)], check=True, capture_output=False)

    metric_args = []
    for metric in metrics:
        metric_args.extend(["-m", metric])

    logger.debug("wily_report_start", path=str(target), metrics=list(metrics))
    report = subprocess.run(
        ["wily", "report", str(target), *metric_args],
        check=True,
        capture_output=True,
        text=True,
    )

    return {"stdout": report.stdout, "stderr": report.stderr}
