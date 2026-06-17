"""Health Check Utilities.

Common utilities for HTTP and TCP health checking. Extracted from tunnel_sync.py,
service_manager.py, and kinfra_networking.py.
"""

import asyncio
import logging
import socket
import time

logger = logging.getLogger(__name__)


def check_tcp_health(host: str = "localhost", port: int = 5432, timeout: float = 2.0) -> bool:
    """Check if a TCP port is accepting connections (synchronous).

    Args:
        host: Host to check (default: "localhost")
        port: Port to check (default: 5432)
        timeout: Connection timeout in seconds (default: 2.0)

    Returns:
        True if port is accepting connections, False otherwise

    Examples:
        >>> check_tcp_health("localhost", 5432)
        True  # PostgreSQL is running
        >>> check_tcp_health("localhost", 9999)
        False  # Nothing listening on 9999
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        logger.debug(f"TCP health check failed for {host}:{port}: {e}")
        return False


def check_http_health(
    url: str, timeout: float = 2.0, expected_status: int = 200, method: str = "GET",
) -> bool:
    """Check HTTP endpoint health (synchronous).

    Args:
        url: Full URL to check (e.g., "http://localhost:8080/health")
        timeout: Request timeout in seconds (default: 2.0)
        expected_status: Expected HTTP status code (default: 200)
        method: HTTP method to use (default: "GET")

    Returns:
        True if endpoint returns expected status, False otherwise

    Examples:
        >>> check_http_health("http://localhost:8080/health")
        True
        >>> check_http_health("https://api.example.com/healthz", timeout=5.0)
        False  # Endpoint not reachable
    """
    try:
        import urllib.request

        req = urllib.request.Request(url, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status == expected_status
    except Exception as e:
        logger.debug(f"HTTP health check failed for {url}: {e}")
        return False


async def check_http_health_async(
    url: str, timeout: float = 2.0, expected_status: int = 200, method: str = "GET",
) -> bool:
    """Check HTTP endpoint health (asynchronous).

    Args:
        url: Full URL to check (e.g., "http://localhost:8080/health")
        timeout: Request timeout in seconds (default: 2.0)
        expected_status: Expected HTTP status code (default: 200)
        method: HTTP method to use (default: "GET")

    Returns:
        True if endpoint returns expected status, False otherwise

    Examples:
        >>> await check_http_health_async("http://localhost:8080/health")
        True
        >>> await check_http_health_async("https://api.example.com/healthz", timeout=5.0)
        False  # Endpoint not reachable
    """
    try:
        import aiohttp

        timeout_obj = aiohttp.ClientTimeout(total=timeout)
        async with aiohttp.ClientSession(timeout=timeout_obj) as session:
            async with session.request(method, url) as response:
                return response.status == expected_status
    except Exception as e:
        logger.debug(f"Async HTTP health check failed for {url}: {e}")
        return False


async def wait_for_http_health(
    url: str, timeout_seconds: int = 20, check_interval: float = 0.5, expected_status: int = 200,
) -> bool:
    """Wait for an HTTP endpoint to become healthy with exponential backoff.

    Args:
        url: URL to check (health endpoint path will be appended if not present)
        timeout_seconds: Maximum time to wait (default: 20)
        check_interval: Initial delay between checks in seconds (default: 0.5)
        expected_status: Expected HTTP status code (default: 200)

    Returns:
        True if endpoint became healthy within timeout, False otherwise

    Examples:
        >>> await wait_for_http_health("http://localhost:8080")
        True  # Service became healthy
        >>> await wait_for_http_health("http://localhost:9999", timeout_seconds=5)
        False  # Timed out
    """
    # Ensure URL has health endpoint
    base_url = url.rstrip("/")
    if not base_url.endswith(("/health", "/healthz")):
        health_url = base_url + "/healthz"
    else:
        health_url = base_url

    logger.info(f"Health check starting for: {health_url}")

    start_time = time.time()
    delay = check_interval

    while time.time() - start_time < timeout_seconds:
        if await check_http_health_async(health_url, timeout=4.0, expected_status=expected_status):
            logger.info(f"Health check passed: {health_url}")
            return True

        await asyncio.sleep(delay)
        delay = min(delay * 1.5, 2.0)  # Exponential backoff, max 2s

    logger.warning(f"Health check timed out: {health_url}")
    return False


def check_tunnel_health(hostname: str, port: int) -> dict[str, bool | int | None]:
    """Check both local service and tunnel reachability.

    Args:
        hostname: Tunnel hostname (e.g., "myapp.example.com")
        port: Local port the service is running on

    Returns:
        Dictionary with health status:
        - local_service_up: bool
        - tunnel_reachable: bool
        - response_time_ms: Optional[int]

    Examples:
        >>> check_tunnel_health("myapp.example.com", 8080)
        {'local_service_up': True, 'tunnel_reachable': True, 'response_time_ms': 245}
    """
    health = {"local_service_up": False, "tunnel_reachable": False, "response_time_ms": None}

    # Check local service
    health["local_service_up"] = check_tcp_health("127.0.0.1", port)

    # Check tunnel reachability
    try:
        import urllib.request

        start = time.time()
        req = urllib.request.Request(f"https://{hostname}", method="HEAD")
        urllib.request.urlopen(req, timeout=5)
        health["response_time_ms"] = int((time.time() - start) * 1000)
        health["tunnel_reachable"] = True
    except Exception as e:
        logger.debug(f"Tunnel health check failed for {hostname}: {e}")
        health["tunnel_reachable"] = False

    return health


async def check_tunnel_health_async(hostname: str, port: int) -> dict[str, bool | int | None]:
    """Check both local service and tunnel reachability (async version).

    Args:
        hostname: Tunnel hostname (e.g., "myapp.example.com")
        port: Local port the service is running on

    Returns:
        Dictionary with health status:
        - local_service_up: bool
        - tunnel_reachable: bool
        - response_time_ms: Optional[int]

    Examples:
        >>> await check_tunnel_health_async("myapp.example.com", 8080)
        {'local_service_up': True, 'tunnel_reachable': True, 'response_time_ms': 245}
    """
    health = {"local_service_up": False, "tunnel_reachable": False, "response_time_ms": None}

    # Check local service (run in executor to avoid blocking)
    loop = asyncio.get_event_loop()
    health["local_service_up"] = await loop.run_in_executor(
        None, check_tcp_health, "127.0.0.1", port, 2.0,
    )

    # Check tunnel reachability
    try:
        import aiohttp

        start = time.time()
        timeout = aiohttp.ClientTimeout(total=5.0)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.head(f"https://{hostname}"):
                health["response_time_ms"] = int((time.time() - start) * 1000)
                health["tunnel_reachable"] = True
    except Exception as e:
        logger.debug(f"Async tunnel health check failed for {hostname}: {e}")
        health["tunnel_reachable"] = False

    return health
