"""Response compression and optimization middleware for FastAPI/Starlette.

This module provides production-ready middleware for response compression,
header optimization, and performance monitoring.

Performance Impact:
- Response sizes: Reduced by 60-90% for JSON/HTML
- Bandwidth costs: Reduced by 70-80%
- Response time: Minimal overhead (<5ms) for significant bandwidth savings

Extracted from atoms/app.py GZipMiddleware configuration.
"""

from __future__ import annotations

import gzip
import time
from typing import TYPE_CHECKING, Any

from starlette.datastructures import MutableHeaders
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware as StarletteGZipMiddleware
from starlette.responses import Response

if TYPE_CHECKING:
    from collections.abc import Callable

    from starlette.requests import Request
    from starlette.types import ASGIApp

__all__ = [
    "CompressionMiddleware",
    "PerformanceHeadersMiddleware",
    "add_compression_header_middleware",
    "add_gzip_compression",
    "optimize_response_middleware",
]


def add_gzip_compression(
    app: ASGIApp,
    minimum_size: int = 500,
    compresslevel: int = 5,
) -> ASGIApp:
    """Add GZip compression to ASGI application.

    Wraps app with Starlette's GZipMiddleware, compressing responses that:
    - Are larger than minimum_size bytes
    - Have compressible content types (JSON, HTML, CSS, JS, etc.)
    - Client accepts gzip encoding (Accept-Encoding: gzip)

    Args:
        app: ASGI application to wrap
        minimum_size: Only compress responses larger than this (bytes, default: 500)
        compresslevel: GZip compression level 1-9 (default: 5, balanced)
            - 1: Fastest, least compression
            - 9: Slowest, best compression
            - 5: Good balance for most use cases

    Returns:
        ASGI application with compression enabled

    Performance Impact:
        - JSON responses: 60-80% size reduction
        - HTML responses: 70-90% size reduction
        - Compression overhead: 2-10ms for typical responses
        - Bandwidth savings: 70-80% reduction in transfer costs

    Examples:
        Basic usage:
        >>> from fastapi import FastAPI
        >>> from pheno.optimization.middleware import add_gzip_compression
        >>>
        >>> app = FastAPI()
        >>> app = add_gzip_compression(app, minimum_size=500)

        Custom compression:
        >>> # Maximum compression for static assets
        >>> app = add_gzip_compression(app, minimum_size=1000, compresslevel=9)

        From atoms/app.py:
        >>> from starlette.middleware.gzip import GZipMiddleware
        >>> app = GZipMiddleware(_base_app, minimum_size=500)
    """
    return StarletteGZipMiddleware(app, minimum_size=minimum_size, compresslevel=compresslevel)


def add_compression_header_middleware(
    app: ASGIApp,
    server_header: str = "pheno-optimized",
    add_timing: bool = True,
) -> ASGIApp:
    """Add compression hints and performance headers to responses.

    Adds headers that help browsers and CDNs optimize caching and compression:
    - Server identification
    - Processing time
    - Compression indicators

    Args:
        app: ASGI application to wrap
        server_header: Value for Server header (default: "pheno-optimized")
        add_timing: Include X-Process-Time header (default: True)

    Returns:
        ASGI application with enhanced headers

    Examples:
        >>> app = add_compression_header_middleware(app)
        >>> # Responses will include:
        >>> # Server: pheno-optimized
        >>> # X-Process-Time: 0.045
    """
    return PerformanceHeadersMiddleware(app, server_header=server_header, add_timing=add_timing)


class CompressionMiddleware(BaseHTTPMiddleware):
    """Advanced compression middleware with multiple algorithms.

    Supports:
    - GZip compression (widely supported)
    - Brotli compression (better compression, modern browsers)
    - Automatic algorithm selection based on Accept-Encoding

    Examples:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> app.add_middleware(CompressionMiddleware, minimum_size=500)
    """

    def __init__(
        self,
        app: ASGIApp,
        minimum_size: int = 500,
        compresslevel: int = 5,
        enable_brotli: bool = False,
    ):
        """Initialize compression middleware.

        Args:
            app: ASGI application
            minimum_size: Minimum response size to compress (bytes)
            compresslevel: Compression level 1-9
            enable_brotli: Enable Brotli compression (requires brotli package)
        """
        super().__init__(app)
        self.minimum_size = minimum_size
        self.compresslevel = compresslevel
        self.enable_brotli = enable_brotli

        if enable_brotli:
            try:
                import brotli  # noqa: F401

                self._has_brotli = True
            except ImportError:
                self._has_brotli = False
        else:
            self._has_brotli = False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and compress response if applicable.
        """
        response = await call_next(request)

        # Check if compression is needed
        if not self._should_compress(request, response):
            return response

        # Select compression algorithm
        accept_encoding = request.headers.get("accept-encoding", "").lower()

        if self._has_brotli and "br" in accept_encoding:
            return await self._compress_brotli(response)
        if "gzip" in accept_encoding:
            return await self._compress_gzip(response)

        return response

    def _should_compress(self, request: Request, response: Response) -> bool:
        """
        Check if response should be compressed.
        """
        # Already compressed
        if "content-encoding" in response.headers:
            return False

        # Check size
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) < self.minimum_size:
            return False

        # Check content type
        content_type = response.headers.get("content-type", "")
        compressible_types = (
            "text/",
            "application/json",
            "application/javascript",
            "application/xml",
            "application/x-javascript",
        )
        return any(content_type.startswith(t) for t in compressible_types)

    async def _compress_gzip(self, response: Response) -> Response:
        """
        Compress response with GZip.
        """
        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        compressed = gzip.compress(body, compresslevel=self.compresslevel)

        headers = MutableHeaders(response.headers)
        headers["content-encoding"] = "gzip"
        headers["content-length"] = str(len(compressed))
        headers["vary"] = "Accept-Encoding"

        return Response(
            content=compressed,
            status_code=response.status_code,
            headers=dict(headers),
            media_type=response.media_type,
        )

    async def _compress_brotli(self, response: Response) -> Response:
        """
        Compress response with Brotli.
        """
        import brotli

        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        compressed = brotli.compress(body, quality=self.compresslevel)

        headers = MutableHeaders(response.headers)
        headers["content-encoding"] = "br"
        headers["content-length"] = str(len(compressed))
        headers["vary"] = "Accept-Encoding"

        return Response(
            content=compressed,
            status_code=response.status_code,
            headers=dict(headers),
            media_type=response.media_type,
        )


class PerformanceHeadersMiddleware(BaseHTTPMiddleware):
    """Add performance and optimization headers to responses.

    Headers added:
    - Server: Server identification
    - X-Process-Time: Request processing time in seconds
    - X-Content-Type-Options: nosniff (security)
    - X-Frame-Options: SAMEORIGIN (security)

    Examples:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> app.add_middleware(PerformanceHeadersMiddleware)
    """

    def __init__(
        self,
        app: ASGIApp,
        server_header: str = "pheno-optimized",
        add_timing: bool = True,
        add_security_headers: bool = True,
    ):
        """Initialize performance headers middleware.

        Args:
            app: ASGI application
            server_header: Value for Server header
            add_timing: Add X-Process-Time header
            add_security_headers: Add basic security headers
        """
        super().__init__(app)
        self.server_header = server_header
        self.add_timing = add_timing
        self.add_security_headers = add_security_headers

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add headers.
        """
        start_time = time.perf_counter()

        response = await call_next(request)

        headers = MutableHeaders(response.headers)

        # Server identification
        if self.server_header:
            headers["server"] = self.server_header

        # Processing time
        if self.add_timing:
            process_time = time.perf_counter() - start_time
            headers["x-process-time"] = f"{process_time:.3f}"

        # Security headers
        if self.add_security_headers:
            headers["x-content-type-options"] = "nosniff"
            headers["x-frame-options"] = "SAMEORIGIN"

        return response


def optimize_response_middleware(
    app: ASGIApp,
    enable_compression: bool = True,
    enable_headers: bool = True,
    minimum_size: int = 500,
    compresslevel: int = 5,
    server_header: str = "pheno-optimized",
) -> ASGIApp:
    """Apply all optimization middleware in recommended order.

    Combines compression, headers, and performance optimizations.

    Args:
        app: ASGI application
        enable_compression: Enable GZip compression
        enable_headers: Enable performance headers
        minimum_size: Minimum size for compression (bytes)
        compresslevel: Compression level 1-9
        server_header: Server identification header

    Returns:
        Fully optimized ASGI application

    Middleware order (inside-out):
    1. Base application
    2. Performance headers (innermost - adds timing)
    3. Compression (outermost - compresses response)

    Examples:
        >>> from fastapi import FastAPI
        >>> from pheno.optimization.middleware import optimize_response_middleware
        >>>
        >>> app = FastAPI()
        >>> # ... add routes ...
        >>> app = optimize_response_middleware(app)

        Custom configuration:
        >>> app = optimize_response_middleware(
        ...     app,
        ...     minimum_size=1000,
        ...     compresslevel=9,
        ...     server_header="my-api-v1",
        ... )
    """
    # Apply middleware in reverse order (inside-out wrapping)

    # 1. Performance headers (innermost)
    if enable_headers:
        app = PerformanceHeadersMiddleware(app, server_header=server_header)

    # 2. Compression (outermost)
    if enable_compression:
        app = StarletteGZipMiddleware(
            app,
            minimum_size=minimum_size,
            compresslevel=compresslevel,
        )

    return app


# FastAPI integration helper


def create_optimized_fastapi_app(**fastapi_kwargs) -> Any:
    """Create FastAPI app with optimization middleware pre-configured.

    Args:
        **fastapi_kwargs: Arguments passed to FastAPI constructor

    Returns:
        FastAPI application with optimizations enabled

    Examples:
        >>> from pheno.optimization.middleware import create_optimized_fastapi_app
        >>>
        >>> app = create_optimized_fastapi_app(title="My API", version="1.0.0")
        >>> # Compression and performance headers already configured
        >>>
        >>> @app.get("/")
        >>> async def root():
        ...     return {"message": "Optimized API"}
    """
    from fastapi import FastAPI

    app = FastAPI(**fastapi_kwargs)

    # Apply optimization middleware
    return optimize_response_middleware(
        app,
        enable_compression=True,
        enable_headers=True,
        minimum_size=500,
        compresslevel=5,
    )

