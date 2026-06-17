"""Auth Validation Module.

Validates authentication immediately after OAuth completes, before running tests.
Provides comprehensive checks for:
- Token validity (structure, expiration)
- HTTP endpoint accessibility (with/without auth)
- Basic tool call functionality
- Response structure validation
- Pre-test session authentication

Usage:
    # Post-OAuth validation
    from pheno.testing.mcp_qa.testing.auth_validator import AuthValidator

    validator = AuthValidator(client, credentials, mcp_endpoint)
    validation_result = await validator.validate_all()

    if not validation_result['valid']:
        # Handle validation failure
        print(validation_result['error'])

    # Pre-test session authentication (use in conftest.py)
    from pheno.testing.mcp_qa.testing.auth_validator import ensure_auth_before_tests

    @pytest.fixture(scope="session", autouse=True)
    async def setup_auth():
        credentials = await ensure_auth_before_tests(
            mcp_endpoint=os.getenv("MCP_ENDPOINT"),
            show_completion=True
        )
        return credentials
"""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

import httpx

from pheno.testing.mcp_qa.logging import get_logger

if TYPE_CHECKING:
    from pheno.testing.mcp_qa.oauth.credential_broker import CapturedCredentials

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """
    Result of auth validation checks.
    """

    valid: bool
    checks: Dict[str, Dict[str, Any]]
    error: Optional[str] = None
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "checks": self.checks,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


class AuthValidator:
    """Validates authentication after OAuth completes.

    Performs comprehensive checks to ensure auth is working before running the full test
    suite.
    """

    def __init__(
        self,
        client: Any,
        credentials: Any,
        mcp_endpoint: str,
        verbose: bool = True,
        timeout: float = 30.0,
    ):
        """Initialize auth validator.

        Args:
            client: Authenticated MCP client
            credentials: Captured credentials with access_token
            mcp_endpoint: MCP endpoint URL
            verbose: Print validation progress
            timeout: Timeout for validation checks (seconds)
        """
        self.client = client
        self.credentials = credentials
        self.mcp_endpoint = mcp_endpoint
        self.verbose = verbose
        self.timeout = timeout
        self.checks: Dict[str, Dict[str, Any]] = {}

    def _print_check(self, name: str, status: str, message: str = "", duration_ms: float = 0):
        """
        Print check result.
        """
        if not self.verbose:
            return

        status_icons = {"start": "⏳", "success": "✓", "warning": "⚠", "error": "✗", "skip": "○"}

        icon = status_icons.get(status, "•")
        duration_str = f" - {duration_ms:.0f}ms" if duration_ms > 0 else ""

        if status == "start":
            print(f"   {icon} {name}...", end="", flush=True)
        elif status in ["success", "warning"]:
            print(f"\r   {icon} {name}{duration_str}")
            if message:
                print(f"      {message}")
        elif status == "error":
            print(f"\r   {icon} {name}{duration_str}")
            if message:
                print(f"      → {message}")
        elif status == "skip":
            print(f"\r   {icon} {name} (skipped)")
            if message:
                print(f"      {message}")

    async def validate_token(self) -> Tuple[bool, str]:
        """Validate token format and structure.

        Returns:
            (success, message)
        """
        check_name = "Token captured"
        self._print_check(check_name, "start")
        start = time.time()

        try:
            token = self.credentials.access_token

            # Check if token is not a placeholder
            if not token or token in ("captured_from_oauth", "placeholder", "TODO", ""):
                return False, "Token is placeholder or empty"

            # Check token format (basic JWT structure)
            parts = token.split(".")
            if len(parts) != 3:
                # Not a JWT, but might be valid - just warn
                duration_ms = (time.time() - start) * 1000
                self._print_check(
                    check_name,
                    "warning",
                    f"Token format unusual (not JWT): {token[:20]}...",
                    duration_ms,
                )
                return True, f"Token present (non-JWT): {token[:20]}..."

            # Try to decode JWT header and payload (without verification)
            try:
                import base64
                import json

                # Decode header
                json.loads(base64.urlsafe_b64decode(parts[0] + "=="))

                # Decode payload
                payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))

                # Check expiration
                exp = payload.get("exp")
                if exp:
                    exp_dt = datetime.fromtimestamp(exp)
                    now = datetime.now()
                    if exp_dt <= now:
                        return False, f"Token expired at {exp_dt}"

                    time_left = exp_dt - now
                    hours = int(time_left.total_seconds() / 3600)
                    minutes = int((time_left.total_seconds() % 3600) / 60)

                    duration_ms = (time.time() - start) * 1000
                    self._print_check(
                        check_name,
                        "success",
                        f"{token[:10]}... (expires in {hours}h {minutes}m)",
                        duration_ms,
                    )
                    return True, f"Token valid (expires in {hours}h {minutes}m)"
                else:
                    duration_ms = (time.time() - start) * 1000
                    self._print_check(
                        check_name, "success", f"{token[:10]}... (no expiration)", duration_ms
                    )
                    return True, "Token valid (no expiration)"

            except Exception as e:
                # JWT decode failed, but token might still be valid
                duration_ms = (time.time() - start) * 1000
                self._print_check(check_name, "warning", f"JWT decode failed: {e}", duration_ms)
                return True, f"Token present but decode failed: {token[:20]}..."

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            self._print_check(check_name, "error", str(e), duration_ms)
            return False, f"Token validation error: {e}"

    async def validate_http_endpoint(self) -> Tuple[bool, str]:
        """Test HTTP endpoint with authentication.

        Makes a simple GET/OPTIONS request to verify endpoint is accessible
        and authentication is working.

        Returns:
            (success, message)
        """
        check_name = "HTTP endpoint accessible"
        self._print_check(check_name, "start")
        start = time.time()

        try:
            token = self.credentials.access_token

            # Test with auth
            headers = {"Authorization": f"Bearer {token}"}

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Try OPTIONS first (lightweight)
                try:
                    response = await client.options(self.mcp_endpoint, headers=headers)
                    if response.status_code < 500:
                        duration_ms = (time.time() - start) * 1000
                        self._print_check(
                            check_name,
                            "success",
                            f"({response.status_code} {response.reason_phrase})",
                            duration_ms,
                        )
                        return True, f"{response.status_code} {response.reason_phrase}"
                except Exception:
                    pass

                # Try GET with /health or root
                for path in ["", "/health", "/api/health"]:
                    try:
                        url = f"{self.mcp_endpoint.rstrip('/')}{path}"
                        response = await client.get(url, headers=headers)

                        if response.status_code == 401:
                            return False, "401 Unauthorized - token may be invalid"
                        elif response.status_code == 403:
                            return False, "403 Forbidden - insufficient permissions"
                        elif response.status_code < 500:
                            duration_ms = (time.time() - start) * 1000
                            self._print_check(
                                check_name, "success", f"({response.status_code} OK)", duration_ms
                            )
                            return True, f"{response.status_code} OK"
                    except httpx.ConnectError:
                        continue
                    except Exception:
                        continue

                # If we get here, endpoint is not accessible
                return False, "Endpoint not accessible (connection failed)"

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            self._print_check(check_name, "error", str(e), duration_ms)
            return False, f"HTTP test error: {e}"

    async def validate_tool_call(self) -> Tuple[bool, str]:
        """Test basic tool call functionality.

        Makes a simple tool call to verify MCP client is working.

        Returns:
            (success, message)
        """
        check_name = "Tool call successful"
        self._print_check(check_name, "start")
        start = time.time()

        try:
            # Try to list tools (lightest operation)
            try:
                tools = await asyncio.wait_for(self.client.list_tools(), timeout=self.timeout)

                duration_ms = (time.time() - start) * 1000
                tool_count = len(tools) if tools else 0

                self._print_check(
                    check_name, "success", f"list_tools returned {tool_count} tools", duration_ms
                )
                return True, f"list_tools succeeded ({tool_count} tools, {duration_ms:.0f}ms)"

            except asyncio.TimeoutError:
                return False, f"Tool call timed out after {self.timeout}s"
            except AttributeError:
                # Client doesn't have list_tools - try a different approach
                self._print_check(check_name, "skip", "list_tools not available on client")
                return True, "Skipped (list_tools not available)"
            except Exception as e:
                return False, f"Tool call failed: {e}"

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            self._print_check(check_name, "error", str(e), duration_ms)
            return False, f"Tool call error: {e}"

    async def validate_response_structure(self) -> Tuple[bool, str]:
        """Validate that tool responses have expected structure.

        Returns:
            (success, message)
        """
        check_name = "Response structure valid"
        self._print_check(check_name, "start")
        start = time.time()

        try:
            # Try to get a tool response
            try:
                tools = await asyncio.wait_for(self.client.list_tools(), timeout=self.timeout)

                # Check if response is a list
                if not isinstance(tools, list):
                    return False, f"Expected list, got {type(tools)}"

                # Check if tools have expected fields
                if tools and len(tools) > 0:
                    first_tool = tools[0]
                    if not hasattr(first_tool, "name"):
                        return False, "Tool missing 'name' field"

                duration_ms = (time.time() - start) * 1000
                self._print_check(
                    check_name, "success", f"Structure valid ({len(tools)} tools)", duration_ms
                )
                return True, f"Structure valid ({len(tools)} tools)"

            except AttributeError:
                # Client doesn't support list_tools
                self._print_check(check_name, "skip", "No tools to validate")
                return True, "Skipped (no tools available)"
            except asyncio.TimeoutError:
                return False, f"Validation timed out after {self.timeout}s"

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            self._print_check(check_name, "error", str(e), duration_ms)
            return False, f"Validation error: {e}"

    async def validate_all(self) -> ValidationResult:
        """Run all validation checks.

        Returns:
            ValidationResult with all check results
        """
        start = time.time()

        if self.verbose:
            print("")
            print("🔍 Validating authentication...")

        # Run all checks
        checks = {}

        # 1. Token validation
        success, message = await self.validate_token()
        checks["token"] = {"success": success, "message": message}

        # 2. HTTP endpoint validation
        success, message = await self.validate_http_endpoint()
        checks["http_endpoint"] = {"success": success, "message": message}

        # 3. Tool call validation
        success, message = await self.validate_tool_call()
        checks["tool_call"] = {"success": success, "message": message}

        # 4. Response structure validation
        success, message = await self.validate_response_structure()
        checks["response_structure"] = {"success": success, "message": message}

        # Check if all critical checks passed
        critical_checks = ["token", "tool_call"]
        all_passed = all(checks[check]["success"] for check in critical_checks if check in checks)

        # Build error message if validation failed
        error = None
        if not all_passed:
            failed = [
                f"{check}: {checks[check]['message']}"
                for check in critical_checks
                if check in checks and not checks[check]["success"]
            ]
            error = "Authentication validation failed:\n   " + "\n   ".join(failed)

        duration_ms = (time.time() - start) * 1000

        if self.verbose:
            if all_passed:
                print("")
                print("✅ Auth validation complete - Ready for test execution")
            else:
                print("")
                print("❌ Auth validation failed:")
                for check, result in checks.items():
                    if not result["success"]:
                        print(f"   ✗ {check}: {result['message']}")
                print("")
                print("   → Token may be invalid or expired")
                print("   → Try clearing cache and retrying...")

        return ValidationResult(
            valid=all_passed, checks=checks, error=error, duration_ms=duration_ms
        )


async def validate_auth(
    client: Any,
    credentials: Any,
    mcp_endpoint: str,
    verbose: bool = True,
    retry_on_failure: bool = True,
) -> ValidationResult:
    """Convenience function to validate authentication.

    Args:
        client: Authenticated MCP client
        credentials: Captured credentials
        mcp_endpoint: MCP endpoint URL
        verbose: Print validation progress
        retry_on_failure: Retry validation if it fails

    Returns:
        ValidationResult
    """
    validator = AuthValidator(client, credentials, mcp_endpoint, verbose=verbose)
    result = await validator.validate_all()

    # Retry once if validation failed
    if not result.valid and retry_on_failure:
        if verbose:
            print("")
            print("⚠️  Retrying validation...")
        await asyncio.sleep(2)  # Brief pause before retry
        result = await validator.validate_all()

    return result


async def ensure_auth_before_tests(
    mcp_endpoint: str,
    provider: str = "authkit",
    show_progress: bool = True,
    show_completion: bool = True,
) -> "CapturedCredentials":
    """Ensure authentication is complete BEFORE pytest test collection.

    This function should be called in conftest.py at session scope via pytest hook
    to ensure auth happens once and completes before any tests run.

    Args:
        mcp_endpoint: MCP server endpoint URL
        provider: OAuth provider (authkit, workos, etc.)
        show_progress: Whether to show progress bar during auth
        show_completion: Whether to show completion message

    Returns:
        CapturedCredentials with access token and session info

    Raises:
        AuthenticationError: If auth fails after retries

    Example:
        # In conftest.py
        @pytest.fixture(scope="session", autouse=True)
        async def ensure_auth():
            from pheno.testing.mcp_qa.testing.auth_validator import ensure_auth_before_tests
            credentials = await ensure_auth_before_tests(
                mcp_endpoint=os.getenv("MCP_ENDPOINT"),
                show_progress=True
            )
            return credentials
    """
    from pheno.testing.mcp_qa.oauth.credential_broker import UnifiedCredentialBroker

    try:
        # Create broker with specified provider
        broker = UnifiedCredentialBroker(mcp_endpoint=mcp_endpoint, provider=provider)

        # Ensure session authentication (will reuse if already authenticated)
        credentials = await broker.ensure_session_authenticated()

        # Show completion message if requested
        if show_completion:
            try:
                from rich.console import Console

                console = Console()

                expires_str = "N/A"
                if credentials.expires_at:
                    expires_str = credentials.expires_at.strftime("%Y-%m-%d %H:%M:%S")

                console.print("")
                console.print("[bold green]✅ Pre-test authentication complete[/bold green]")
                console.print(f"   [cyan]Email:[/cyan] {credentials.email or 'unknown'}")
                console.print(f"   [cyan]Provider:[/cyan] {credentials.provider}")
                console.print(f"   [cyan]Endpoint:[/cyan] {mcp_endpoint}")
                console.print(f"   [cyan]Token expires:[/cyan] {expires_str}")
                console.print("")
                console.print("[dim]→ Tests will now run with authenticated session[/dim]")
                console.print("")
            except ImportError:
                # Fallback to simple print if rich is not available
                print("")
                print("✅ Pre-test authentication complete")
                print(f"   Email: {credentials.email or 'unknown'}")
                print(f"   Provider: {credentials.provider}")
                print(f"   Endpoint: {mcp_endpoint}")
                print("")
                print("→ Tests will now run with authenticated session")
                print("")

        return credentials

    except Exception as e:
        # Handle authentication errors gracefully
        error_msg = f"Pre-test authentication failed: {e}"

        try:
            from rich.console import Console

            console = Console()
            console.print("")
            console.print(f"[bold red]❌ {error_msg}[/bold red]")
            console.print("")
            console.print("[yellow]Possible solutions:[/yellow]")
            console.print("   1. Check your MCP endpoint URL")
            console.print("   2. Verify your OAuth credentials")
            console.print("   3. Clear cache and retry: rm -rf ~/.atoms_mcp_test_cache")
            console.print("")
        except ImportError:
            print("")
            print(f"❌ {error_msg}")
            print("")
            print("Possible solutions:")
            print("   1. Check your MCP endpoint URL")
            print("   2. Verify your OAuth credentials")
            print("   3. Clear cache and retry: rm -rf ~/.atoms_mcp_test_cache")
            print("")

        # Re-raise as a more specific error
        raise RuntimeError(error_msg) from e
