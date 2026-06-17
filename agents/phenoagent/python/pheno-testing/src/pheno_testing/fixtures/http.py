"""HTTP fixtures for testing.

Provides fixtures for HTTP client testing, mocking, and server simulation.
"""

from collections.abc import AsyncGenerator, Generator
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import Mock

import pytest

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

try:
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False


# ============================================================================
# HTTP Response Mock
# ============================================================================


@dataclass
class MockHTTPResponse:
    """Mock HTTP response for testing.

    Example:
        response = MockHTTPResponse(
            status_code=200,
            json_data={"message": "success"},
            headers={"Content-Type": "application/json"}
        )
    """

    status_code: int = 200
    text: str = ""
    json_data: dict[str, Any] | None = None
    headers: dict[str, str] = field(default_factory=dict)
    content: bytes = b""

    def json(self) -> dict[str, Any]:
        """
        Return JSON data.
        """
        if self.json_data is not None:
            return self.json_data

        import json

        return json.loads(self.text) if self.text else {}

    @property
    def ok(self) -> bool:
        """
        Check if response is successful.
        """
        return 200 <= self.status_code < 300

    def raise_for_status(self) -> None:
        """
        Raise exception for error status codes.
        """
        if not self.ok:
            raise Exception(f"HTTP {self.status_code}")


@pytest.fixture
def mock_http_response():
    """Factory fixture for creating mock HTTP responses.

    Example:
        def test_api(mock_http_response):
            response = mock_http_response(
                status_code=200,
                json_data={"user": "test"}
            )
            assert response.json()["user"] == "test"
    """

    def _create_response(
        status_code: int = 200,
        text: str = "",
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        content: bytes = b"",
    ) -> MockHTTPResponse:
        return MockHTTPResponse(
            status_code=status_code,
            text=text,
            json_data=json_data,
            headers=headers or {},
            content=content,
        )

    return _create_response


# ============================================================================
# HTTP Client Fixtures
# ============================================================================


@pytest.fixture
def http_client() -> Generator[Any, None, None]:
    """Create an HTTP client for testing.

    Uses httpx.Client with sensible defaults for testing.

    Example:
        def test_api(http_client):
            response = http_client.get("https://api.example.com")
            assert response.status_code == 200
    """
    if not HTTPX_AVAILABLE:
        pytest.skip("httpx not installed")

    client = httpx.Client(timeout=30.0, follow_redirects=True)

    yield client

    client.close()


@pytest.fixture
async def async_http_client() -> AsyncGenerator[Any, None]:
    """Create an async HTTP client for testing.

    Uses httpx.AsyncClient with sensible defaults for testing.

    Example:
        async def test_api(async_http_client):
            response = await async_http_client.get("https://api.example.com")
            assert response.status_code == 200
    """
    if not HTTPX_AVAILABLE:
        pytest.skip("httpx not installed")

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        yield client


# ============================================================================
# Mock HTTP Server
# ============================================================================


class MockHTTPServer:
    """Mock HTTP server for testing.

    Allows registering mock responses for specific URLs.

    Example:
        server = MockHTTPServer()
        server.add_response("GET", "/users", json_data={"users": []})

        response = server.request("GET", "/users")
        assert response.json_data == {"users": []}
    """

    def __init__(self):
        self.responses: dict[tuple, MockHTTPResponse] = {}
        self.requests: list = []

    def add_response(
        self,
        method: str,
        path: str,
        status_code: int = 200,
        text: str = "",
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Add a mock response for a specific method and path.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: URL path
            status_code: Response status code
            text: Response text
            json_data: Response JSON data
            headers: Response headers
        """
        key = (method.upper(), path)
        self.responses[key] = MockHTTPResponse(
            status_code=status_code,
            text=text,
            json_data=json_data,
            headers=headers or {},
        )

    def request(self, method: str, path: str, **kwargs) -> MockHTTPResponse:
        """Make a mock request.

        Args:
            method: HTTP method
            path: URL path
            **kwargs: Additional request parameters (stored for inspection)

        Returns:
            MockHTTPResponse
        """
        # Store request for inspection
        self.requests.append(
            {
                "method": method.upper(),
                "path": path,
                "kwargs": kwargs,
            },
        )

        # Find matching response
        key = (method.upper(), path)
        if key in self.responses:
            return self.responses[key]

        # Default 404 response
        return MockHTTPResponse(status_code=404, text="Not Found")

    def get_requests(self, method: str | None = None, path: str | None = None) -> list:
        """Get recorded requests, optionally filtered.

        Args:
            method: Filter by HTTP method
            path: Filter by path

        Returns:
            List of matching requests
        """
        requests = self.requests

        if method:
            requests = [r for r in requests if r["method"] == method.upper()]

        if path:
            requests = [r for r in requests if r["path"] == path]

        return requests

    def reset(self) -> None:
        """
        Reset all responses and requests.
        """
        self.responses.clear()
        self.requests.clear()


@pytest.fixture
def mock_http_server():
    """Create a mock HTTP server for testing.

    Example:
        def test_api_client(mock_http_server):
            mock_http_server.add_response(
                "GET", "/users",
                json_data={"users": [{"id": 1, "name": "Test"}]}
            )

            response = mock_http_server.request("GET", "/users")
            assert len(response.json()["users"]) == 1
    """
    server = MockHTTPServer()
    yield server
    server.reset()


# ============================================================================
# HTTP Mocking Utilities
# ============================================================================


def mock_httpx_response(
    status_code: int = 200,
    json_data: dict[str, Any] | None = None,
    text: str = "",
    headers: dict[str, str] | None = None,
) -> Mock:
    """Create a mock httpx.Response object.

    Example:
        from unittest.mock import patch

        with patch('httpx.get') as mock_get:
            mock_get.return_value = mock_httpx_response(
                json_data={"message": "success"}
            )
            # Test code here
    """
    mock_response = Mock()
    mock_response.status_code = status_code
    mock_response.text = text
    mock_response.headers = headers or {}

    if json_data is not None:
        mock_response.json.return_value = json_data

    mock_response.raise_for_status = Mock()

    return mock_response


__all__ = [
    "MockHTTPResponse",
    "MockHTTPServer",
    "async_http_client",
    "http_client",
    "mock_http_response",
    "mock_http_server",
    "mock_httpx_response",
]
