"""Progress display for test execution.

Provides:
- ComprehensiveProgressDisplay for enhanced progress tracking
- ProgressTracker for basic tqdm-based progress
"""

from typing import TYPE_CHECKING, Any, List, Optional

try:
    from tqdm import tqdm as _tqdm

    HAS_TQDM = True
except ImportError:
    _tqdm = None  # type: ignore[assignment]
    HAS_TQDM = False


if TYPE_CHECKING:
    from .test_runner import BaseTestRunner


class ProgressTracker:
    """Wraps tqdm for basic progress tracking."""

    def __init__(self, total_tests: int):
        self._pbar: Optional[Any] = None
        if HAS_TQDM and _tqdm:
            self._pbar = _tqdm(
                total=total_tests,
                desc="Running tests",
                unit="test",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
            )

    def close(self) -> None:
        if self._pbar:
            self._pbar.close()

    def update(self, n: int = 1) -> None:
        if self._pbar:
            self._pbar.update(n)

    def write(self, msg: str) -> None:
        if self._pbar:
            self._pbar.write(msg)
        else:
            print(msg)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


try:
    from .progress_display import ComprehensiveProgressDisplay
except ImportError:
    ComprehensiveProgressDisplay = None
