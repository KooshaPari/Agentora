"""OAuth-related widgets for MCP QA TUI.

Note: OAuth widgets are not yet implemented in this module.
This module is reserved for future OAuth-related UI components:
- OAuthStatusWidget: OAuth flow status display
- OAuthConfigWidget: OAuth configuration dialog
- TokenDisplayWidget: Token information display
"""

from textual.widget import Widget


class OAuthStatusWidget(Widget):
    """OAuth authentication status display.

    Features:
    - Connection status indicator
    - Token expiration countdown
    - Refresh button
    - Error message display
    """

    DEFAULT_CSS = """
    OAuthStatusWidget {
        height: auto;
        border: solid $primary;
        padding: 1;
    }
    """

    def compose(self):
        """Create child widgets."""
        from textual.widgets import Static

        yield Static("OAuth Status", id="oauth-status")
