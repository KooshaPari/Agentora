"""Test Runner with caching, quiet mode, and verbose failures.

Features:
- Session caching (reuse authenticated clients)
- Quiet mode (only show failures)
- Verbose failure output (show call/response details)
- Timeout handling
- Progress tracking
"""

import hashlib
import json
import logging
import traceback
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class CachedSession:
    """
    Cached authentication session.
    """

    client: Any
    endpoint: str
    created_at: datetime
    expires_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_valid(self) -> bool:
        """
        Check if session is still valid.
        """
        return datetime.now() < self.expires_at

    def time_remaining(self) -> timedelta:
        """
        Get time remaining until expiration.
        """
        return self.expires_at - datetime.now()


class SessionCache:
    """Cache for authenticated sessions.

    Reuses authenticated clients across test runs for 90%+ speed improvement.
    """

    def __init__(self, cache_dir: Optional[Path] = None, default_ttl: int = 3600):
        self.cache_dir = cache_dir or Path.home() / ".cache" / "mcp_test_sessions"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl
        self._memory_cache: Dict[str, CachedSession] = {}

    def _get_cache_key(self, endpoint: str, user: Optional[str] = None) -> str:
        """
        Generate cache key for endpoint.
        """
        key_data = f"{endpoint}:{user or 'default'}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]

    def get(self, endpoint: str, user: Optional[str] = None) -> Optional[Any]:
        """
        Get cached session.
        """
        cache_key = self._get_cache_key(endpoint, user)

        # Check memory cache
        if cache_key in self._memory_cache:
            session = self._memory_cache[cache_key]
            if session.is_valid():
                return session.client
            else:
                del self._memory_cache[cache_key]

        return None

    def set(
        self,
        endpoint: str,
        client: Any,
        ttl: Optional[int] = None,
        user: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Cache a session.
        """
        cache_key = self._get_cache_key(endpoint, user)
        ttl = ttl or self.default_ttl

        session = CachedSession(
            client=client,
            endpoint=endpoint,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=ttl),
            metadata=metadata or {},
        )

        self._memory_cache[cache_key] = session

    def clear(self, endpoint: Optional[str] = None):
        """
        Clear cached sessions.
        """
        if endpoint:
            cache_key = self._get_cache_key(endpoint)
            self._memory_cache.pop(cache_key, None)
        else:
            self._memory_cache.clear()


class TestRunner:
    """Test runner with quiet mode and verbose failure output.

    Features:
    - Quiet mode: only show failures
    - Verbose failures: show full call/response details
    - Progress tracking
    - Summary at end

    Example:
        runner = TestRunner(verbose=False)

        with runner.test("test_something") as ctx:
            result = await client.call_tool("tool", {})
            ctx.record_call("call_tool", args=["tool", {}], response=result)
            assert result.success

        runner.print_summary()
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results = []
        self._captured_output = []

    class TestContext:
        """
        Context manager for individual tests.
        """

        def __init__(self, runner, test_name: str):
            self.runner = runner
            self.test_name = test_name
            self.start_time = None
            self.success = False
            self.error = None
            self.call_details = {}

        def __enter__(self):
            self.start_time = datetime.now()
            if self.runner.verbose:
                print(f"▶ Running {self.test_name}...")
            return self

        def record_call(
            self,
            method: str,
            args: Any = None,
            kwargs: Any = None,
            response: Any = None,
            error: Any = None,
        ):
            """
            Record API call details for failure reporting.
            """
            self.call_details = {
                "method": method,
                "args": args,
                "kwargs": kwargs,
                "response": response,
                "error": error,
                "timestamp": datetime.now().isoformat(),
            }

        def __exit__(self, exc_type, exc_val, exc_tb):
            duration = (datetime.now() - self.start_time).total_seconds()

            if exc_type is None:
                # Success
                self.success = True
                if self.runner.verbose:
                    print(f"✓ {self.test_name} passed ({duration:.2f}s)")
            else:
                # Failure - show detailed output
                self.success = False
                self.error = exc_val

                # Always show failures with full details
                print(f"\n{'='*70}")
                print(f"❌ {self.test_name} FAILED ({duration:.2f}s)")
                print(f"{'='*70}")

                # Show error
                print("\n📛 Error:")
                print(f"  {exc_type.__name__}: {exc_val}")

                # Show call details if available
                if self.call_details:
                    print("\n📞 Last API Call:")
                    print(f"  Method: {self.call_details.get('method', 'N/A')}")

                    if self.call_details.get("args"):
                        print("  Args:")
                        try:
                            print(
                                f"    {json.dumps(self.call_details['args'], indent=4, default=str)}"
                            )
                        except Exception:
                            print(f"    {self.call_details['args']}")

                    if self.call_details.get("kwargs"):
                        print("  Kwargs:")
                        try:
                            print(
                                f"    {json.dumps(self.call_details['kwargs'], indent=4, default=str)}"
                            )
                        except Exception:
                            print(f"    {self.call_details['kwargs']}")

                    if self.call_details.get("response"):
                        print("\n📥 Response:")
                        try:
                            if hasattr(self.call_details["response"], "__dict__"):
                                response_dict = vars(self.call_details["response"])
                                print(f"  {json.dumps(response_dict, indent=2, default=str)}")
                            else:
                                print(
                                    f"  {json.dumps(self.call_details['response'], indent=2, default=str)}"
                                )
                        except Exception:
                            print(f"  {self.call_details['response']}")

                    if self.call_details.get("error"):
                        print("\n❌ API Error:")
                        print(f"  {self.call_details['error']}")

                # Show traceback
                if exc_tb:
                    print("\n📍 Traceback:")
                    tb_lines = traceback.format_tb(exc_tb)
                    for line in tb_lines[-3:]:  # Show last 3 frames
                        for subline in line.strip().split("\n"):
                            print(f"  {subline}")

                # Show captured output
                if self.runner._captured_output:
                    print("\n📝 Captured Output:")
                    for line in self.runner._captured_output:
                        print(f"  {line}")

                print(f"{'='*70}\n")

            # Record result
            self.runner.results.append(
                {
                    "name": self.test_name,
                    "success": self.success,
                    "duration": duration,
                    "error": str(self.error) if self.error else None,
                    "call_details": self.call_details if not self.success else None,
                }
            )

            # Clear captured output
            self.runner._captured_output.clear()

            # Don't suppress exception
            return False

    def test(self, name: str):
        """
        Create test context.
        """
        return self.TestContext(self, name)

    def print_summary(self):
        """
        Print test summary.
        """
        total = len(self.results)
        passed = sum(1 for r in self.results if r["success"])
        failed = total - passed

        print("\n" + "=" * 70)
        print(f"📊 Test Summary: {passed}/{total} passed")

        if failed > 0:
            print(f"\n❌ Failed tests ({failed}):")
            for result in self.results:
                if not result["success"]:
                    print(f"  • {result['name']}: {result['error']}")
        else:
            print("\n✅ All tests passed!")

        print("=" * 70)


class SmartTestRunner(TestRunner):
    """Deprecated: Use TestRunner instead."""

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "SmartTestRunner is deprecated, use TestRunner instead",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)


# Global session cache
_session_cache = SessionCache()


async def get_or_create_client(
    endpoint: str,
    email: str,
    password: str,
    use_cache: bool = True,
    cache_ttl: int = 3600,
    verbose: bool = False,
    client_factory: Optional[Callable] = None,
):
    """Get cached client or create new one.

    Args:
        endpoint: MCP endpoint URL
        email: User email
        password: User password
        use_cache: Whether to use cached sessions
        cache_ttl: Cache TTL in seconds
        verbose: Whether to show verbose output
        client_factory: Optional custom client factory function

    Returns:
        Authenticated client
    """
    # Try cache first
    if use_cache:
        cached_client = _session_cache.get(endpoint, user=email)
        if cached_client:
            if verbose:
                print("✓ Using cached session")
            return cached_client

    # Create new session
    if verbose:
        print("⏳ Creating new session...")

    if client_factory:
        client = await client_factory(endpoint, email, password)
    else:
        # Default: use mcp_qa OAuth flow
        from pheno.testing.mcp_qa.oauth.credential_broker import UnifiedCredentialBroker

        broker = UnifiedCredentialBroker(
            endpoint=endpoint, provider="authkit", email=email, password=password
        )

        client = await broker.get_authenticated_client()

    # Cache the session
    if use_cache:
        _session_cache.set(endpoint, client, ttl=cache_ttl, user=email)

    return client
