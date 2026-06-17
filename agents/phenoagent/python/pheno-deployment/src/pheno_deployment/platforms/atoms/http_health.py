"""HTTP Health Check Implementation.

Platform-agnostic HTTP health check implementation. Can be moved to pheno-sdk/deploy-
kit/platforms/http_health.py
"""

import time
import urllib.error
import urllib.request

from ...base.deployment import HealthCheckProvider


class HTTPHealthCheckProvider(HealthCheckProvider):
    """
    HTTP-based health check implementation.
    """

    def __init__(self, logger=None):
        self.logger = logger

    def log_info(self, message: str):
        """
        Log info message.
        """
        if self.logger:
            self.logger.info(message)

    def log_warning(self, message: str):
        """
        Log warning message.
        """
        if self.logger and hasattr(self.logger, "warning"):
            self.logger.warning(message)

    def check(self, url: str, timeout: int = 10) -> bool:
        """Check if URL returns 200 OK.

        Args:
            url: URL to check
            timeout: Timeout in seconds

        Returns:
            True if URL returns 200, False otherwise
        """
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.status == 200
        except (urllib.error.HTTPError, urllib.error.URLError, Exception):
            return False

    def check_with_retries(
        self, url: str, max_retries: int = 5, retry_delay: int = 2, timeout: int = 10,
    ) -> bool:
        """Check URL health with retries.

        Args:
            url: URL to check
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            timeout: Timeout per attempt in seconds

        Returns:
            True if healthy within retry limit, False otherwise
        """
        for attempt in range(max_retries):
            self.log_info(f"Health check attempt {attempt + 1}/{max_retries} for {url}")

            try:
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    if response.status == 200:
                        self.log_info(f"Health check passed for {url}")
                        return True
            except urllib.error.HTTPError as e:
                self.log_warning(f"Health check failed with HTTP {e.code}")
            except urllib.error.URLError as e:
                self.log_warning(f"Health check failed with URL error: {e.reason}")
            except Exception as e:
                self.log_warning(f"Health check failed with error: {e}")

            # Wait before retry (except on last attempt)
            if attempt < max_retries - 1:
                time.sleep(retry_delay)

        self.log_warning(f"Health check failed after {max_retries} attempts")
        return False

    def check_endpoint(
        self,
        base_url: str,
        endpoint: str = "/health",
        expected_status: int = 200,
        timeout: int = 10,
    ) -> bool:
        """Check specific endpoint.

        Args:
            base_url: Base URL (e.g., https://example.com)
            endpoint: Endpoint path (e.g., /health)
            expected_status: Expected HTTP status code
            timeout: Timeout in seconds

        Returns:
            True if endpoint returns expected status
        """
        url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.status == expected_status
        except urllib.error.HTTPError as e:
            return e.code == expected_status
        except Exception:
            return False

    def check_multiple_endpoints(self, base_url: str, endpoints: list, timeout: int = 10) -> dict:
        """Check multiple endpoints.

        Args:
            base_url: Base URL
            endpoints: List of endpoint paths
            timeout: Timeout per endpoint

        Returns:
            Dictionary mapping endpoints to their status (True/False)
        """
        results = {}

        for endpoint in endpoints:
            results[endpoint] = self.check_endpoint(
                base_url=base_url, endpoint=endpoint, timeout=timeout,
            )

        return results


class AdvancedHealthChecker:
    """
    Advanced health checking with custom validators.
    """

    def __init__(self, logger=None):
        self.logger = logger
        self.http_checker = HTTPHealthCheckProvider(logger=logger)

    def check_with_validator(self, url: str, validator: callable, timeout: int = 10) -> bool:
        """Check URL with custom validator function.

        Args:
            url: URL to check
            validator: Function that takes response and returns bool
            timeout: Timeout in seconds

        Returns:
            True if validator returns True
        """
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return validator(response)
        except Exception:
            return False

    def check_json_response(self, url: str, expected_keys: list, timeout: int = 10) -> bool:
        """Check if JSON response contains expected keys.

        Args:
            url: URL to check
            expected_keys: List of keys that should be in response
            timeout: Timeout in seconds

        Returns:
            True if all expected keys present
        """
        try:
            import json

            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                data = json.loads(response.read())
                return all(key in data for key in expected_keys)
        except Exception:
            return False

    def check_response_time(self, url: str, max_response_time: float, timeout: int = 10) -> tuple:
        """Check response time.

        Args:
            url: URL to check
            max_response_time: Maximum acceptable response time in seconds
            timeout: Timeout in seconds

        Returns:
            Tuple of (success: bool, response_time: float)
        """
        start_time = time.time()

        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                response_time = time.time() - start_time
                success = response.status == 200 and response_time <= max_response_time
                return (success, response_time)
        except Exception:
            response_time = time.time() - start_time
            return (False, response_time)
