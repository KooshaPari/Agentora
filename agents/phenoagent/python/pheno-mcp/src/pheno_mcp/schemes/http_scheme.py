"""HTTP Scheme Handler.

Provides access to HTTP resources via http:// and https:// URIs.
"""

from typing import Any

from pheno.ports.mcp import ResourceSchemeHandler


class HttpSchemeHandler(ResourceSchemeHandler):
    """
    Handler for http:// and https:// schemes.

    Provides access to HTTP resources.
    Automatically parses JSON responses.

    URI Format:
        http://example.com/api/resource
        https://api.example.com/v1/users/123

    Example:
        >>> handler = HttpSchemeHandler()
        >>> data = await handler.get_resource("https://api.example.com/users/123")
    """

    def __init__(self, headers: dict | None = None, timeout: int = 30):
        """Initialize HTTP scheme handler.

        Args:
            headers: Optional default headers
            timeout: Request timeout in seconds
        """
        self.headers = headers or {}
        self.timeout = timeout

    async def get_resource(self, uri: str) -> Any:
        """Get HTTP resource.

        Args:
            uri: HTTP(S) URL

        Returns:
            Response data (parsed if JSON)

        Raises:
            ValueError: If request fails

        Example:
            >>> data = await handler.get_resource("https://api.example.com/data")
        """
        try:
            import aiohttp
        except ImportError:
            raise ImportError(
                "aiohttp is required for HTTP scheme handler. Install with: pip install aiohttp",
            )

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(uri, timeout=self.timeout) as response:
                if response.status != 200:
                    raise ValueError(f"HTTP request failed: {response.status} {response.reason}")

                content_type = response.headers.get("Content-Type", "")

                if "application/json" in content_type:
                    return await response.json()
                return await response.text()

    async def list_resources(self, uri: str) -> list[str]:
        """List HTTP resources.

        Note: This is not typically supported for HTTP.
        Returns empty list.

        Args:
            uri: HTTP(S) URL pattern

        Returns:
            Empty list
        """
        # HTTP doesn't support listing
        return []

    def supports_scheme(self, scheme: str) -> bool:
        """
        Check if scheme is supported.
        """
        return scheme in ["http", "https"]


__all__ = ["HttpSchemeHandler"]
