"""Rate limiting patterns for FastAPI with per-endpoint and per-user controls.

This module provides production-ready rate limiting using token bucket algorithms
with support for:
- Per-endpoint rate limits
- Per-user rate limits
- Per-IP rate limits
- Burst allowances
- Custom rate limit rules
- FastAPI middleware integration

Extracted from atoms (commit d09ce42) and pheno-sdk utilities.
Built on pheno.utilities.rate_limiter.TokenBucketRateLimiter.
"""

from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from pheno.utilities.rate_limiter import RateLimitRule, TokenBucketRateLimiter

if TYPE_CHECKING:
    from collections.abc import Callable

    from starlette.types import ASGIApp

__all__ = [
    "RateLimitMiddleware",
    "RateLimiter",
    "create_rate_limited_endpoint",
    "get_client_identifier",
    "rate_limit",
]


class RateLimiter:
    """High-level rate limiter with multiple strategies.

    Supports:
    - Per-endpoint limits
    - Per-user limits
    - Per-IP limits
    - Custom key functions
    - Configurable rules

    Examples:
        Basic per-endpoint limiting:
        >>> limiter = RateLimiter(requests_per_minute=60)
        >>> if await limiter.check_limit(request, "api_endpoint"):
        ...     # Process request
        ...     pass

        Per-user limiting:
        >>> limiter = RateLimiter(requests_per_minute=100)
        >>> user_id = get_user_from_token(request)
        >>> if await limiter.check_limit(request, f"user:{user_id}"):
        ...     # Process request
        ...     pass
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        burst_multiplier: float = 2.0,
        enable_ip_limiting: bool = True,
        enable_user_limiting: bool = True,
    ):
        """Initialize rate limiter.

        Args:
            requests_per_minute: Default sustained rate limit
            burst_multiplier: Burst allowance multiplier (default: 2x sustained)
            enable_ip_limiting: Enable per-IP rate limiting
            enable_user_limiting: Enable per-user rate limiting
        """
        self.requests_per_minute = requests_per_minute
        self.burst_multiplier = burst_multiplier
        self.enable_ip_limiting = enable_ip_limiting
        self.enable_user_limiting = enable_user_limiting

        # Create token bucket limiter
        default_rule = RateLimitRule(
            requests_per_period=requests_per_minute,
            period_seconds=60.0,
            burst=requests_per_minute * burst_multiplier,
        )
        self._limiter = TokenBucketRateLimiter(default_rule=default_rule)

        # Custom rules per endpoint/user
        self._custom_rules: dict[str, RateLimitRule] = {}

    def configure_endpoint(
        self,
        endpoint: str,
        requests_per_minute: int,
        burst_multiplier: float | None = None,
    ) -> None:
        """Configure custom rate limit for specific endpoint.

        Args:
            endpoint: Endpoint identifier (e.g., "POST /api/users")
            requests_per_minute: Requests per minute for this endpoint
            burst_multiplier: Burst multiplier (defaults to instance default)

        Examples:
            >>> limiter.configure_endpoint("POST /api/heavy", 10)
            >>> limiter.configure_endpoint("GET /api/light", 1000, burst_multiplier=3.0)
        """
        burst = burst_multiplier or self.burst_multiplier
        rule = RateLimitRule(
            requests_per_period=requests_per_minute,
            period_seconds=60.0,
            burst=requests_per_minute * burst,
        )
        self._custom_rules[endpoint] = rule
        self._limiter.configure_rule(endpoint, rule)

    def configure_user(
        self,
        user_id: str,
        requests_per_minute: int,
        burst_multiplier: float | None = None,
    ) -> None:
        """Configure custom rate limit for specific user.

        Args:
            user_id: User identifier
            requests_per_minute: Requests per minute for this user
            burst_multiplier: Burst multiplier

        Examples:
            >>> limiter.configure_user("premium_user_123", 1000)
            >>> limiter.configure_user("free_user_456", 60)
        """
        burst = burst_multiplier or self.burst_multiplier
        rule = RateLimitRule(
            requests_per_period=requests_per_minute,
            period_seconds=60.0,
            burst=requests_per_minute * burst,
        )
        key = f"user:{user_id}"
        self._custom_rules[key] = rule
        self._limiter.configure_rule(key, rule)

    async def check_limit(
        self,
        request: Request,
        key: str,
        permits: float = 1.0,
    ) -> bool:
        """Check if request is within rate limit.

        Args:
            request: FastAPI request object
            key: Rate limit key (endpoint, user, custom)
            permits: Number of permits to consume (default: 1.0)

        Returns:
            True if request allowed, False if rate limited

        Examples:
            >>> if await limiter.check_limit(request, "api_endpoint"):
            ...     return {"data": "response"}
            >>> else:
            ...     raise HTTPException(429, "Rate limit exceeded")
        """
        return await self._limiter.allow(key, permits)

    def get_retry_after(self, key: str, permits: float = 1.0) -> float:
        """Get seconds until rate limit resets.

        Args:
            key: Rate limit key
            permits: Number of permits needed

        Returns:
            Seconds to wait before retry
        """
        return self._limiter.get_retry_after(key, permits)

    def get_remaining(self, key: str) -> float:
        """Get remaining requests available.

        Args:
            key: Rate limit key

        Returns:
            Number of requests remaining
        """
        return self._limiter.get_remaining(key)

    async def check_combined_limits(
        self,
        request: Request,
        endpoint: str,
        user_id: str | None = None,
    ) -> tuple[bool, str | None]:
        """Check multiple rate limits (endpoint, user, IP).

        Args:
            request: FastAPI request object
            endpoint: Endpoint identifier
            user_id: Optional user identifier

        Returns:
            Tuple of (allowed, reason_if_blocked)

        Examples:
            >>> allowed, reason = await limiter.check_combined_limits(
            ...     request, "POST /api/users", user_id="user_123"
            ... )
            >>> if not allowed:
            ...     raise HTTPException(429, reason)
        """
        # Check endpoint limit
        if not await self.check_limit(request, endpoint):
            retry_after = self.get_retry_after(endpoint)
            return False, f"Endpoint rate limit exceeded. Retry after {retry_after:.0f}s"

        # Check user limit
        if self.enable_user_limiting and user_id:
            user_key = f"user:{user_id}"
            if not await self.check_limit(request, user_key):
                retry_after = self.get_retry_after(user_key)
                return False, f"User rate limit exceeded. Retry after {retry_after:.0f}s"

        # Check IP limit
        if self.enable_ip_limiting:
            client_ip = get_client_identifier(request)
            ip_key = f"ip:{client_ip}"
            if not await self.check_limit(request, ip_key):
                retry_after = self.get_retry_after(ip_key)
                return False, f"IP rate limit exceeded. Retry after {retry_after:.0f}s"

        return True, None

    def reset(self, key: str | None = None) -> None:
        """Reset rate limit counters.

        Args:
            key: Specific key to reset, or None to reset all

        Examples:
            >>> limiter.reset("user:123")  # Reset specific user
            >>> limiter.reset()  # Reset all limits
        """
        self._limiter.reset(key)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for automatic rate limiting.

    Applies rate limits to all endpoints based on configuration.

    Examples:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> app.add_middleware(
        ...     RateLimitMiddleware,
        ...     requests_per_minute=60,
        ...     enable_user_limiting=True,
        ... )
    """

    def __init__(
        self,
        app: ASGIApp,
        requests_per_minute: int = 60,
        burst_multiplier: float = 2.0,
        enable_ip_limiting: bool = True,
        enable_user_limiting: bool = False,
        user_id_extractor: Callable[[Request], str | None] | None = None,
    ):
        """Initialize rate limit middleware.

        Args:
            app: ASGI application
            requests_per_minute: Default rate limit
            burst_multiplier: Burst allowance multiplier
            enable_ip_limiting: Enable per-IP limiting
            enable_user_limiting: Enable per-user limiting
            user_id_extractor: Function to extract user ID from request
        """
        super().__init__(app)
        self.limiter = RateLimiter(
            requests_per_minute=requests_per_minute,
            burst_multiplier=burst_multiplier,
            enable_ip_limiting=enable_ip_limiting,
            enable_user_limiting=enable_user_limiting,
        )
        self.user_id_extractor = user_id_extractor

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Apply rate limiting to request.
        """
        # Build endpoint key
        endpoint = f"{request.method} {request.url.path}"

        # Extract user ID if enabled
        user_id = None
        if self.limiter.enable_user_limiting and self.user_id_extractor:
            try:
                user_id = self.user_id_extractor(request)
            except Exception:
                pass  # Continue without user ID

        # Check rate limits
        allowed, reason = await self.limiter.check_combined_limits(request, endpoint, user_id)

        if not allowed:
            retry_after = self.limiter.get_retry_after(endpoint)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "rate_limit_exceeded",
                    "message": reason,
                    "retry_after": int(retry_after),
                },
                headers={"Retry-After": str(int(retry_after))},
            )

        # Add rate limit headers to response
        response = await call_next(request)
        remaining = self.limiter.get_remaining(endpoint)
        response.headers["X-RateLimit-Limit"] = str(self.limiter.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(int(remaining))

        return response


def get_client_identifier(request: Request) -> str:
    """Extract client identifier from request.

    Checks headers for real IP (reverse proxy support):
    - X-Forwarded-For
    - X-Real-IP
    - Falls back to direct client IP

    Args:
        request: FastAPI request object

    Returns:
        Client IP address or identifier

    Examples:
        >>> ip = get_client_identifier(request)
        >>> limiter.check_limit(request, f"ip:{ip}")
    """
    # Check X-Forwarded-For (proxy/load balancer)
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # Take first IP in chain
        return forwarded.split(",")[0].strip()

    # Check X-Real-IP
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    # Fall back to direct client
    if request.client:
        return request.client.host

    return "unknown"


def rate_limit(
    requests_per_minute: int = 60,
    burst_multiplier: float = 2.0,
    key_func: Callable[[Request], str] | None = None,
):
    """Decorator for rate limiting specific endpoints.

    Args:
        requests_per_minute: Rate limit for this endpoint
        burst_multiplier: Burst allowance multiplier
        key_func: Optional function to generate custom rate limit key

    Returns:
        Decorator function

    Examples:
        Basic endpoint rate limiting:
        >>> @app.post("/api/heavy")
        >>> @rate_limit(requests_per_minute=10)
        >>> async def heavy_endpoint():
        ...     return {"status": "processing"}

        Per-user rate limiting:
        >>> def get_user_key(request: Request) -> str:
        ...     user_id = request.state.user_id
        ...     return f"user:{user_id}"
        >>>
        >>> @app.post("/api/user-action")
        >>> @rate_limit(requests_per_minute=100, key_func=get_user_key)
        >>> async def user_action(request: Request):
        ...     return {"status": "ok"}

        Per-IP rate limiting:
        >>> @app.post("/api/public")
        >>> @rate_limit(
        ...     requests_per_minute=30,
        ...     key_func=lambda req: f"ip:{get_client_identifier(req)}"
        ... )
        >>> async def public_endpoint():
        ...     return {"data": "response"}
    """
    # Create shared limiter for this decorator
    rule = RateLimitRule(
        requests_per_period=requests_per_minute,
        period_seconds=60.0,
        burst=requests_per_minute * burst_multiplier,
    )
    limiter = TokenBucketRateLimiter(default_rule=rule)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if request is None:
                request = kwargs.get("request")

            if request is None:
                raise ValueError("rate_limit decorator requires Request parameter")

            # Generate rate limit key
            if key_func:
                key = key_func(request)
            else:
                # Default: use endpoint
                key = f"{request.method} {request.url.path}"

            # Check rate limit
            allowed = await limiter.allow(key)
            if not allowed:
                retry_after = limiter.get_retry_after(key)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "rate_limit_exceeded",
                        "message": f"Rate limit exceeded. Retry after {retry_after:.0f}s",
                        "retry_after": int(retry_after),
                    },
                    headers={"Retry-After": str(int(retry_after))},
                )

            # Call endpoint
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def create_rate_limited_endpoint(
    limiter: RateLimiter,
    endpoint: str,
    requests_per_minute: int,
) -> Callable:
    """Create a rate-limited endpoint wrapper.

    Args:
        limiter: RateLimiter instance
        endpoint: Endpoint identifier
        requests_per_minute: Rate limit

    Returns:
        Decorator function

    Examples:
        >>> limiter = RateLimiter()
        >>> api_limit = create_rate_limited_endpoint(
        ...     limiter, "POST /api/users", 100
        ... )
        >>>
        >>> @app.post("/api/users")
        >>> @api_limit
        >>> async def create_user(request: Request):
        ...     return {"id": "new_user"}
    """
    limiter.configure_endpoint(endpoint, requests_per_minute)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if request is None:
                request = kwargs.get("request")

            if request is None:
                raise ValueError("Rate limited endpoint requires Request parameter")

            allowed = await limiter.check_limit(request, endpoint)
            if not allowed:
                retry_after = limiter.get_retry_after(endpoint)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "rate_limit_exceeded",
                        "message": f"Endpoint rate limit exceeded. Retry after {retry_after:.0f}s",
                        "retry_after": int(retry_after),
                    },
                    headers={"Retry-After": str(int(retry_after))},
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator
