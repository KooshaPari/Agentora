"""Network-level optimizations for HTTP requests."""

import httpx


class NetworkOptimizer:
    """
    Network-level optimizations for HTTP requests.
    """

    @staticmethod
    def create_optimized_client(
        base_url: str,
        enable_http2: bool = True,
        enable_compression: bool = True,
        timeout: int = 30,
    ) -> httpx.AsyncClient:
        """
        Create an optimized HTTP client with advanced features.
        """
        headers = {}
        if enable_compression:
            headers["Accept-Encoding"] = "gzip, deflate, br"

        return httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            http2=enable_http2,
            headers=headers,
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100,
                keepalive_expiry=30.0,
            ),
            transport=httpx.AsyncHTTPTransport(
                retries=3,
                http2=enable_http2,
            ),
        )
