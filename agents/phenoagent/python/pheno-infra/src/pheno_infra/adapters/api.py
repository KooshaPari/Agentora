"""
API Adapter - Generic API-based resource management

Handles remote/cloud resources managed via HTTP APIs (RDS, Cloud SQL, SaaS, etc.).
"""

import asyncio
import logging
from typing import Any

import aiohttp

from ..utils.aiohttp_otel import apply_aiohttp_otel_kwargs
from .base import ResourceAdapter

try:
    import aiohttp

    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
    aiohttp = None


logger = logging.getLogger(__name__)


class APIAdapter(ResourceAdapter):
    """Generic API-based resource adapter.

    Manages resources via HTTP/REST APIs. Useful for:
    - Cloud databases (RDS, Cloud SQL, etc.)
    - SaaS services (Auth0, Stripe, etc.)
    - Serverless functions (Lambda, Cloud Functions)
    - Kubernetes resources via API
    - Remote servers via API

    Configuration:
        api_base_url: str - Base URL for API (required)
        auth: Dict - Authentication configuration
            - type: "bearer", "basic", "api_key", "custom"
            - token: str (for bearer)
            - username: str (for basic)
            - password: str (for basic)
            - api_key: str (for api_key)
            - header_name: str (for api_key, default: "X-API-Key")
            - headers: Dict[str, str] (for custom)
        start_endpoint: str - Endpoint to call to start resource
        start_method: str - HTTP method (default: POST)
        start_body: Dict - Request body for start
        stop_endpoint: str - Endpoint to call to stop resource
        stop_method: str - HTTP method (default: POST)
        stop_body: Dict - Request body for stop
        status_endpoint: str - Endpoint to check status
        health_endpoint: str - Endpoint for health checks
        health_check: Dict - Health check configuration
            - type: "http" (default), "custom"
            - expected_status: int (default: 200)
            - expected_response: Dict - Expected JSON response
            - poll_interval: float (default: 5.0)
    """

    def __init__(self, name: str, config: dict[str, Any]):
        super().__init__(name, config)

        if not HAS_AIOHTTP:
            raise ImportError("aiohttp required for APIAdapter. Install: pip install aiohttp")

        # Validate required fields
        if "api_base_url" not in config:
            raise ValueError("API adapter requires 'api_base_url'")

        self.base_url = config["api_base_url"].rstrip("/")
        self.auth_config = config.get("auth", {})

        # Endpoints
        self.start_endpoint = config.get("start_endpoint", "/start")
        self.start_method = config.get("start_method", "POST")
        self.start_body = config.get("start_body", {})

        self.stop_endpoint = config.get("stop_endpoint", "/stop")
        self.stop_method = config.get("stop_method", "POST")
        self.stop_body = config.get("stop_body", {})

        self.status_endpoint = config.get("status_endpoint", "/status")
        self.health_endpoint = config.get("health_endpoint", "/health")

        self.health_config = config.get("health_check", {})

        # HTTP session
        self.session: aiohttp.ClientSession | None = None

    async def _ensure_session(self):
        """
        Ensure HTTP session is initialized.
        """
        if not self.session:
            self.session = aiohttp.ClientSession(**apply_aiohttp_otel_kwargs({}))

    async def _close_session(self):
        """
        Close HTTP session.
        """
        if self.session:
            await self.session.close()
            self.session = None

    def _get_auth_headers(self) -> dict[str, str]:
        """
        Get authentication headers based on config.
        """
        auth_type = self.auth_config.get("type", "none")

        if auth_type == "bearer":
            token = self.auth_config.get("token")
            return {"Authorization": f"Bearer {token}"}

        if auth_type == "api_key":
            api_key = self.auth_config.get("api_key")
            header_name = self.auth_config.get("header_name", "X-API-Key")
            return {header_name: api_key}

        if auth_type == "basic":
            import base64

            username = self.auth_config.get("username", "")
            password = self.auth_config.get("password", "")
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            return {"Authorization": f"Basic {credentials}"}

        if auth_type == "custom":
            return self.auth_config.get("headers", {})

        return {}

    async def start(self) -> bool:
        """
        Start resource via API.
        """
        try:
            await self._ensure_session()

            url = f"{self.base_url}{self.start_endpoint}"
            headers = self._get_auth_headers()

            logger.info(f"Starting {self.name} via API: {self.start_method} {url}")

            async with self.session.request(
                self.start_method,
                url,
                json=self.start_body if self.start_body else None,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if 200 <= response.status < 300:
                    self.state.running = True
                    logger.info(f"✓ {self.name} started via API")

                    # Wait for health if configured
                    await self._wait_for_health()
                    return True
                error = await response.text()
                logger.error(f"API start failed ({response.status}): {error}")
                self.state.error = error
                return False

        except Exception as e:
            logger.exception(f"Failed to start {self.name} via API: {e}")
            self.state.error = str(e)
            return False

    async def stop(self) -> bool:
        """
        Stop resource via API.
        """
        try:
            await self._ensure_session()

            url = f"{self.base_url}{self.stop_endpoint}"
            headers = self._get_auth_headers()

            logger.info(f"Stopping {self.name} via API: {self.stop_method} {url}")

            async with self.session.request(
                self.stop_method,
                url,
                json=self.stop_body if self.stop_body else None,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if 200 <= response.status < 300:
                    self.state.running = False
                    self.state.healthy = False
                    logger.info(f"✓ {self.name} stopped via API")
                    return True
                error = await response.text()
                logger.error(f"API stop failed ({response.status}): {error}")
                return False

        except Exception as e:
            logger.exception(f"Failed to stop {self.name} via API: {e}")
            return False
        finally:
            await self._close_session()

    async def is_running(self) -> bool:
        """
        Check if resource is running via API.
        """
        try:
            await self._ensure_session()

            url = f"{self.base_url}{self.status_endpoint}"
            headers = self._get_auth_headers()

            async with self.session.request(
                "GET", url, headers=headers, timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    # Look for common status indicators
                    running = data.get("running", data.get("status") == "running")
                    self.state.running = running
                    return running

                return False

        except Exception as e:
            logger.debug(f"Status check failed for {self.name}: {e}")
            return False

    async def check_health(self) -> bool:
        """
        Check resource health via API.
        """
        try:
            await self._ensure_session()

            url = f"{self.base_url}{self.health_endpoint}"
            headers = self._get_auth_headers()

            expected_status = self.health_config.get("expected_status", 200)

            async with self.session.request(
                "GET", url, headers=headers, timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                healthy = response.status == expected_status

                # Check expected response if configured
                if healthy and "expected_response" in self.health_config:
                    data = await response.json()
                    expected = self.health_config["expected_response"]

                    # Simple dict matching
                    for key, value in expected.items():
                        if data.get(key) != value:
                            healthy = False
                            break

                self.state.healthy = healthy
                return healthy

        except Exception as e:
            logger.debug(f"Health check failed for {self.name}: {e}")
            self.state.healthy = False
            return False

    async def _wait_for_health(self, timeout: float = 60.0):
        """
        Wait for resource to become healthy.
        """
        if not self.health_endpoint:
            return

        logger.info(f"Waiting for {self.name} to be healthy...")
        start = asyncio.get_event_loop().time()

        poll_interval = self.health_config.get("poll_interval", 5.0)

        while asyncio.get_event_loop().time() - start < timeout:
            if await self.check_health():
                logger.info(f"✓ {self.name} is healthy")
                return

            await asyncio.sleep(poll_interval)

        logger.warning(f"Health check timeout for {self.name}")
