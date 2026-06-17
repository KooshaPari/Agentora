"""OAuth Provider Implementations.

Provides Playwright-based OAuth automation and callback handling.
"""

from fastmcp.client.auth import OAuth


class CaptureOAuth(OAuth):
    """OAuth handler that captures URL and token."""

    def __init__(self, broker, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.broker = broker
        self.broker._callback_port = self.redirect_port
        self.broker.logger.debug("CaptureOAuth initialized", redirect_port=self.redirect_port)

    async def redirect_handler(self, authorization_url: str) -> None:
        """Called when OAuth URL is ready."""
        self.broker.logger.debug("redirect_handler called", url=authorization_url)
        self.broker._oauth_url = authorization_url

    async def launch_browser(self, authorization_url: str) -> None:
        """Override launch_browser to capture URL before launching."""
        self.broker.logger.debug("launch_browser called", url=authorization_url)
        self.broker._oauth_url = authorization_url


async def trigger_oauth_callback(callback_url: str) -> None:
    """Trigger OAuth callback."""
    import httpx

    async with httpx.AsyncClient() as client:
        await client.get(callback_url, follow_redirects=True)
