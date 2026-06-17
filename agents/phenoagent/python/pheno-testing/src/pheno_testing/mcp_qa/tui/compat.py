"""Backward Compatibility Shims for mcp-QA.

This module provides compatibility aliases for code migrated to tui-kit.
Import from here instead of old locations for seamless migration.

Migration status:
- ✅ Progress widgets -> tui_kit.widgets.unified_progress
- ✅ Stream capture -> tui_kit.core.stream_capture
- 🔄 Status widgets -> (pending migration)

Usage:
    # Old code (still works)
    from pheno.testing.mcp_qa.tui.progress_display import ComprehensiveProgressDisplay

    # New code (recommended)
    from tui_kit.widgets.unified_progress import UnifiedProgressWidget
"""

# Import unified implementations from tui-kit
try:
    from tui_kit.core.stream_capture import (
        CapturedLine,
        LogLevel,
        OutputFormatter,
        StreamCapture,
        capture_output,
    )
    from tui_kit.widgets.unified_progress import (
        CategoryStats,
        Task,
        TaskMetrics,
        TaskPriority,
        TaskStatus,
        UnifiedProgressWidget,
    )

    HAS_TUI_KIT = True
except ImportError:
    HAS_TUI_KIT = False
    # Fallback to local implementations if tui-kit not installed
    import warnings

    warnings.warn(
        "tui-kit not found. Using legacy implementations. "
        "Install tui-kit with: pip install -e ../tui-kit",
        DeprecationWarning,
        stacklevel=2,
    )


# Compatibility aliases for progress widgets
if HAS_TUI_KIT:
    # Alias for old names
    ComprehensiveProgressDisplay = UnifiedProgressWidget
    TestProgressTracker = UnifiedProgressWidget
    ProgressWidget = UnifiedProgressWidget

    # Export all from unified module
    __all__ = [
        # Main widgets
        "UnifiedProgressWidget",
        "ComprehensiveProgressDisplay",  # Compat alias
        "TestProgressTracker",  # Compat alias
        "ProgressWidget",  # Compat alias
        # Data classes
        "Task",
        "TaskStatus",
        "TaskPriority",
        "TaskMetrics",
        "CategoryStats",
        # Stream capture
        "StreamCapture",
        "CapturedLine",
        "LogLevel",
        "OutputFormatter",
        "capture_output",
    ]
else:
    # If tui-kit not available, provide minimal fallback
    __all__ = []


# Deprecation helper
def _deprecation_warning(old_name: str, new_name: str):
    """
    Show deprecation warning for old imports.
    """
    import warnings

    warnings.warn(
        f"{old_name} is deprecated. Use {new_name} from tui_kit instead.",
        DeprecationWarning,
        stacklevel=3,
    )
