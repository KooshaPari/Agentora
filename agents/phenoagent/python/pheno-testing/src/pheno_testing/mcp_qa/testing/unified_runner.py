"""Unified MCP Test Runner with Automatic OAuth and Parallel Execution.

Handles:
- Single OAuth authentication (shared across all tests)
- Parallel client pooling (N connections sharing auth)
- Session persistence (cached tokens between runs)
- Automatic cleanup

Usage:
    runner = UnifiedMCPTestRunner(
        mcp_endpoint="https://your-server.com/mcp",
        parallel=True,
        workers=16
    )

    summary = await runner.run_all()
"""

import os
from typing import Any, Dict, List, Optional

from pheno.testing.mcp_qa.core.parallel_clients import ParallelClientManager
from pheno.testing.mcp_qa.oauth.credential_broker import UnifiedCredentialBroker
from pheno.testing.mcp_qa.testing.auth_validator import validate_auth


class UnifiedMCPTestRunner:
    """
    Unified test runner that automatically handles:
    - OAuth authentication (once per run)
    - Parallel client pooling (shared auth)
    - Session caching (persistent tokens)
    - Cleanup on exit
    """

    def __init__(
        self,
        mcp_endpoint: str,
        provider: str = "authkit",
        parallel: bool = True,
        workers: int = None,
        cache: bool = True,
        verbose: bool = False,
        reporters: List[Any] = None,
    ):
        """Initialize unified test runner.

        Args:
            mcp_endpoint: MCP server endpoint URL
            provider: OAuth provider (default: authkit)
            parallel: Enable parallel execution (default: True)
            workers: Number of parallel workers (default: auto-detect CPU cores)
            cache: Enable session caching (default: True)
            verbose: Verbose output (default: False)
            reporters: List of test reporters
        """
        self.mcp_endpoint = mcp_endpoint
        self.provider = provider
        self.parallel = parallel
        self.workers = workers or os.cpu_count() or 16
        self.cache = cache
        self.verbose = verbose
        self.reporters = reporters or []

        # Internal state
        self._broker: Optional[UnifiedCredentialBroker] = None
        self._client = None
        self._credentials = None
        self._client_manager: Optional[ParallelClientManager] = None
        self._runner = None
        self._initialized = False
        self._auth_validated = False
        self._validation_result = None

    async def initialize(self):
        """
        Initialize OAuth and client pool.
        """
        if self._initialized:
            return

        if self.verbose:
            print(f"📡 Connecting to {self.mcp_endpoint}...")

        # Step 1: Authenticate (once)
        self._broker = UnifiedCredentialBroker(
            mcp_endpoint=self.mcp_endpoint, provider=self.provider
        )

        self._client, self._credentials = await self._broker.get_authenticated_client()

        if self.verbose:
            email = getattr(self._credentials, "email", "authenticated")
            print(f"✅ Authenticated as: {email}")

        # Step 2: Validate authentication
        if not self._auth_validated:
            validation_result = await validate_auth(
                client=self._client,
                credentials=self._credentials,
                mcp_endpoint=self.mcp_endpoint,
                verbose=self.verbose,
                retry_on_failure=True,
            )

            self._validation_result = validation_result
            self._auth_validated = True

            if not validation_result.valid:
                error_msg = validation_result.error or "Authentication validation failed"
                if self.verbose:
                    print(f"\n❌ {error_msg}")
                    print("\nTroubleshooting:")
                    print("   1. Clear cache: rm -rf ~/.atoms_mcp_test_cache")
                    print("   2. Check credentials in .env file")
                    print("   3. Verify MCP endpoint is accessible")
                    print("")
                raise RuntimeError(error_msg)

        # Step 3: Re-enable parallel client pool with HTTP adapters
        # Now that JSON-RPC over HTTP POST is fixed, parallel HTTP adapters work great
        if self.parallel:
            try:
                # Capture token from the broker for HTTP adapters
                access_token = None
                if hasattr(self, "credentials") and self.credentials:
                    access_token = self.credentials.access_token

                self._client_manager = ParallelClientManager(
                    endpoint=self.mcp_endpoint,
                    client_name="unified_mcp_test_runner",
                    num_clients=self.workers,
                    oauth_handler=None,
                    access_token=access_token,
                    use_direct_http=True,  # JSON-RPC 2.0 over HTTP POST
                )
                await self._client_manager.initialize()

                if self.verbose:
                    print(f"✅ Parallel HTTP pool: {self.workers} adapters ready")
            except Exception as e:
                if self.verbose:
                    print(f"⚠️  Parallel pool failed: {e}")
                    print("   Falling back to single client")
                self._client_manager = None
        else:
            self._client_manager = None

        self._initialized = True

    async def run_all(self, categories: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run all tests with automatic OAuth and parallel execution.

        Args:
            categories: Optional list of test categories to run

        Returns:
            Test summary dict with results
        """
        await self.initialize()

        # Import project-specific runner
        # This is a placeholder - projects should override this
        raise NotImplementedError(
            "Subclass UnifiedMCPTestRunner and implement run_all() "
            "to call your project's TestRunner"
        )

    async def cleanup(self):
        """
        Cleanup resources.
        """
        # Cleanup client manager
        if self._client_manager:
            try:
                await self._client_manager.cleanup()
            except Exception:
                pass

        # Cleanup broker
        if self._broker:
            try:
                await self._broker.close()
            except Exception:
                pass

        # Cleanup client
        if self._client:
            try:
                await self._client.__aexit__(None, None, None)
            except Exception:
                pass

    async def __aenter__(self):
        """
        Async context manager entry.
        """
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Async context manager exit.
        """
        await self.cleanup()

    @property
    def client(self):
        """
        Get the authenticated MCP client.
        """
        return self._client

    @property
    def client_manager(self):
        """
        Get the parallel client manager.
        """
        return self._client_manager

    @property
    def credentials(self):
        """
        Get the OAuth credentials.
        """
        return self._credentials

    @property
    def validation_result(self):
        """
        Get the auth validation result.
        """
        return self._validation_result


# Helper function for quick test runs
async def run_mcp_tests(
    mcp_endpoint: str,
    test_runner_class,
    provider: str = "authkit",
    parallel: bool = True,
    workers: int = None,
    categories: Optional[List[str]] = None,
    verbose: bool = False,
    **kwargs,
) -> Dict[str, Any]:
    """Quick helper to run MCP tests with automatic OAuth and parallel execution.

    Args:
        mcp_endpoint: MCP server endpoint URL
        test_runner_class: Project-specific TestRunner class
        provider: OAuth provider (default: authkit)
        parallel: Enable parallel execution (default: True)
        workers: Number of parallel workers (default: auto-detect)
        categories: Optional list of test categories
        verbose: Verbose output
        **kwargs: Additional arguments for test runner

    Returns:
        Test summary dict

    Example:
        from tests.framework import TestRunner

        summary = await run_mcp_tests(
            mcp_endpoint="https://zen.kooshapari.com/mcp",
            test_runner_class=TestRunner,
            parallel=True,
            workers=16
        )
    """
    async with UnifiedMCPTestRunner(
        mcp_endpoint=mcp_endpoint,
        provider=provider,
        parallel=parallel,
        workers=workers,
        verbose=verbose,
    ) as unified_runner:
        # Create project-specific test runner with unified resources
        from tests.framework import MCPClientAdapter

        adapter = MCPClientAdapter(unified_runner.client, verbose_on_fail=True)

        runner = test_runner_class(client_adapter=adapter, parallel=parallel, **kwargs)

        # Attach client manager if available
        if unified_runner.client_manager:
            runner.client_manager = unified_runner.client_manager

        # Run tests
        summary = await runner.run_all(categories=categories)

        return summary
