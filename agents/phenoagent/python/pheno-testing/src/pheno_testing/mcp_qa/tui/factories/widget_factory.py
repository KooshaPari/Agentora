"""Widget Factory for Creating Reusable UI Components.

Provides factory methods for common widget types.
"""

from typing import Any, Dict, List, Optional

try:
    from textual.widgets import Label, Static

    HAS_TEXTUAL = True
except ImportError:
    HAS_TEXTUAL = False
    Static = object
    Label = object


class WidgetFactory:
    """
    Factory for creating reusable dashboard widgets.
    """

    @staticmethod
    def create_status_panel(
        title: str, fields: List[str], initial_data: Optional[Dict[str, Any]] = None
    ):
        """Create a generic status panel widget.

        Args:
            title: Panel title
            fields: List of field names to display
            initial_data: Initial data values

        Returns:
            Widget: Status panel widget

        Example:
            panel = WidgetFactory.create_status_panel(
                title="Server Status",
                fields=["Port", "Status", "Uptime"],
                initial_data={"Port": 8000, "Status": "Running"}
            )
        """
        from ..components.status_panel import GenericStatusPanel

        return GenericStatusPanel(title=title, fields=fields, data=initial_data or {})

    @staticmethod
    def create_log_viewer(title: str, source: str, max_lines: int = 1000):
        """Create a log viewer widget.

        Args:
            title: Viewer title
            source: Log source (file path or stream name)
            max_lines: Maximum lines to keep in buffer

        Returns:
            Widget: Log viewer widget
        """
        from ..components.log_viewer import GenericLogViewer

        return GenericLogViewer(title=title, source=source, max_lines=max_lines)

    @staticmethod
    def create_progress_bar(title: str, total: int, show_percentage: bool = True):
        """Create a progress bar widget.

        Args:
            title: Progress bar title
            total: Total steps
            show_percentage: Whether to show percentage

        Returns:
            Widget: Progress bar widget
        """
        from ..components.progress import GenericProgressBar

        return GenericProgressBar(title=title, total=total, show_percentage=show_percentage)

    @staticmethod
    def create_test_tree(title: str = "Tests", auto_expand: bool = True):
        """Create a test tree widget.

        Args:
            title: Tree title
            auto_expand: Auto-expand nodes

        Returns:
            Widget: Test tree widget
        """
        from ..components.test_tree import GenericTestTree

        return GenericTestTree(title=title, auto_expand=auto_expand)
