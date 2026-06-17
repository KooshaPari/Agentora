"""Base Dashboard Classes for MCP Testing.

Provides foundation classes for building test dashboards. Projects should inherit from
these to create specific implementations.
"""

from abc import abstractmethod
from typing import Any, Dict

try:
    from textual.app import App
    from textual.widgets import Static

    HAS_TEXTUAL = True
except ImportError:
    HAS_TEXTUAL = False

    # Fallback classes when textual not available
    class App:
        def __init__(self, **kwargs):
            pass

        def refresh(self):
            pass

    class Static:
        def __init__(self, **kwargs):
            pass


if HAS_TEXTUAL:
    # When textual is available, use it as base
    class BaseDashboard(App):
        """Base class for all test dashboards.

        Provides structure for:
        - Layout composition
        - Widget management
        - File watching
        - Test execution
        - Status updates

        Projects should inherit and implement:
        - build_layout()
        - setup_watchers()
        - handle_test_results()
        """

else:
    # When textual not available, use plain object
    class BaseDashboard:
        """
        Base class for all test dashboards (fallback without textual).
        """

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.test_results = {}
            self.watchers = []

        @abstractmethod
        def build_layout(self):
            """Build the dashboard layout.

            Returns:
                Container: The main layout container

            Example:
                def build_layout(self):
                    return Container(
                        Header(),
                        StatusPanel(),
                        LogViewer(),
                        Footer()
                    )
            """
            pass

        @abstractmethod
        def setup_watchers(self):
            """Setup file/resource watchers.

            Example:
                def setup_watchers(self):
                    self.watch_file("tests/", self.on_test_change)
                    self.watch_resource("/health", self.on_health_change)
            """
            pass

        def handle_test_results(self, results: Dict[str, Any]):
            """Handle test execution results.

            Args:
                results: Test results dictionary
            """
            self.test_results = results
            if hasattr(self, "refresh"):
                self.refresh()

        def update_status(self, status: str, data: Dict[str, Any]):
            """Update dashboard status.

            Args:
                status: Status type (e.g., "server", "oauth", "tests")
                data: Status data
            """
            pass


if HAS_TEXTUAL:
    # When textual is available, use it as base
    class BaseWidget(Static):
        """Base class for all dashboard widgets.

        Provides reactive data updates and consistent interface.
        """

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.data = {}

        @abstractmethod
        def update_data(self, data: Dict[str, Any]):
            """Update widget with new data.

            Args:
                data: New data to display
            """
            pass

        @abstractmethod
        def render_content(self) -> str:
            """Render widget content.

            Returns:
                str: Rendered content
            """
            pass

else:
    # When textual not available, use plain object
    class BaseWidget:
        """
        Base class for all dashboard widgets (fallback without textual).
        """

        def __init__(self, **kwargs):
            self.data = {}

        @abstractmethod
        def update_data(self, data: Dict[str, Any]):
            """
            Update widget with new data.
            """
            pass

        @abstractmethod
        def render_content(self) -> str:
            """
            Render widget content.
            """
            pass
