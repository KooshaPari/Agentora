# Auth Validation

Comprehensive authentication validation that runs immediately after OAuth completes, before executing the main test suite.

## Overview

The auth validation module provides:

1. **Token Validation**
   - Extracts access token from authenticated client
   - Verifies token format (JWT structure)
   - Checks expiration timestamp
   - Displays token info (issuer, expiration, scopes)

2. **HTTP Endpoint Testing**
   - Makes simple HTTP GET to MCP endpoint with auth headers
   - Verifies 200 response (not 401)
   - Tests endpoint accessibility

3. **Tool Call Testing**
   - Makes simple tool call (list_tools)
   - Verifies tool responds successfully
   - Displays response time
   - Validates response structure

4. **Automatic Retry**
   - Retries validation once if it fails
   - Provides clear error messages
   - Suggests troubleshooting steps

## Usage

### Automatic (Default)

Auth validation is automatically run by `UnifiedMCPTestRunner` after OAuth completes:

```python
from mcp_qa.testing.unified_runner import UnifiedMCPTestRunner

async with UnifiedMCPTestRunner(
    mcp_endpoint="https://mcp.example.com",
    verbose=True
) as runner:
    # Auth validation happens automatically here
    summary = await runner.run_all()
```

### Manual Validation

You can also run validation manually:

```python
from mcp_qa.testing.auth_validator import validate_auth

# After getting authenticated client
client, credentials = await broker.get_authenticated_client()

# Validate auth
result = await validate_auth(
    client=client,
    credentials=credentials,
    mcp_endpoint="https://mcp.example.com",
    verbose=True,
    retry_on_failure=True
)

if not result.valid:
    print(f"Validation failed: {result.error}")
    for check_name, check_result in result.checks.items():
        print(f"  {check_name}: {check_result['message']}")
```

### Standalone Test

Run the test script to validate auth without running full tests:

```bash
cd /path/to/atoms_mcp-old
python tests/test_auth_validation.py
```

## Output Examples

### Success Output

```
✅ Authentication complete (21.0s)

🔍 Validating authentication...
   ✓ Token captured - 45ms
      eyJhbG... (expires in 23h 59m)
   ✓ HTTP endpoint accessible - 145ms
      (200 OK)
   ✓ Tool call successful - 423ms
      list_tools returned 15 tools
   ✓ Response structure valid - 10ms
      Structure valid (15 tools)

✅ Auth validation complete - Ready for test execution
```

### Failure Output

```
✅ Authentication complete (19.2s)

🔍 Validating authentication...
   ✓ Token captured - 32ms
      eyJhbG... (expires in 23h 59m)
   ✗ HTTP endpoint accessible - 2145ms
      401 Unauthorized - token may be invalid
   ✗ Tool call successful - 189ms
      Tool call failed: Unauthorized
   ○ Response structure valid (skipped)
      No tools to validate

❌ Auth validation failed:
   ✗ tool_call: Tool call failed: Unauthorized
   → Token may be invalid or expired
   → Clearing cache and retrying...

Troubleshooting:
   1. Clear cache: rm -rf ~/.atoms_mcp_test_cache
   2. Check credentials in .env file
   3. Verify MCP endpoint is accessible
```

## Validation Checks

### 1. Token Validation

Checks:
- Token is not empty or placeholder
- Token has valid JWT structure (3 parts)
- Token has not expired
- Token expiration timestamp is in the future

Result includes:
- Token preview (first 10 chars)
- Time until expiration (hours, minutes)
- Warning if token format is unusual

### 2. HTTP Endpoint

Checks:
- Endpoint is accessible
- Auth headers are accepted
- Response is not 401 Unauthorized
- Response is not 403 Forbidden

Attempts:
1. OPTIONS request (lightweight)
2. GET requests to /, /health, /api/health

### 3. Tool Call

Checks:
- Client can list tools
- Tools respond within timeout
- Response is not empty

Measures:
- Response time (ms)
- Number of tools returned

### 4. Response Structure

Checks:
- Response is a list
- Tools have expected fields (name, etc.)
- Structure matches MCP protocol

## Integration

### With UnifiedMCPTestRunner

Auth validation is automatically integrated:

```python
from mcp_qa.testing.unified_runner import UnifiedMCPTestRunner

runner = UnifiedMCPTestRunner(
    mcp_endpoint="https://mcp.example.com",
    verbose=True  # Show validation progress
)

await runner.initialize()  # Auth validation runs here

# Check validation result
if runner.validation_result:
    print(f"Valid: {runner.validation_result.valid}")
    print(f"Duration: {runner.validation_result.duration_ms}ms")
```

### With Atoms Test Runner

The Atoms test runner extends UnifiedMCPTestRunner and includes validation:

```python
from tests.framework import AtomsMCPTestRunner

async with AtomsMCPTestRunner(
    mcp_endpoint="https://mcp.atoms.tech/api/mcp",
    verbose=True
) as runner:
    # Auth validation happens automatically
    summary = await runner.run_all()
```

## Configuration

### Timeout

Default timeout is 30 seconds. Adjust via:

```python
from mcp_qa.testing.auth_validator import AuthValidator

validator = AuthValidator(
    client=client,
    credentials=credentials,
    mcp_endpoint=mcp_endpoint,
    timeout=60.0  # 60 seconds
)

result = await validator.validate_all()
```

### Verbose Output

Control output verbosity:

```python
result = await validate_auth(
    client=client,
    credentials=credentials,
    mcp_endpoint=mcp_endpoint,
    verbose=False  # Suppress progress output
)
```

### Retry on Failure

Enable/disable automatic retry:

```python
result = await validate_auth(
    client=client,
    credentials=credentials,
    mcp_endpoint=mcp_endpoint,
    retry_on_failure=False  # Don't retry
)
```

## Error Handling

Validation errors include:

1. **Token Issues**
   - Empty or placeholder token
   - Invalid JWT structure
   - Expired token

2. **Endpoint Issues**
   - Connection timeout
   - 401 Unauthorized
   - 403 Forbidden
   - Endpoint not accessible

3. **Tool Call Issues**
   - Timeout
   - Authorization failure
   - MCP protocol error

4. **Response Issues**
   - Invalid response structure
   - Missing required fields
   - Type mismatch

## Troubleshooting

### Validation Fails with 401

```bash
# Clear cached credentials
rm -rf ~/.atoms_mcp_test_cache

# Check .env file
cat .env | grep TEST_

# Try manual auth
python tests/test_auth_validation.py
```

### Timeout Issues

```python
# Increase timeout
validator = AuthValidator(
    client=client,
    credentials=credentials,
    mcp_endpoint=mcp_endpoint,
    timeout=60.0  # Increase from default 30s
)
```

### Token Format Issues

If token is not a JWT (not 3 parts):
- This is OK for some auth providers
- Validation will warn but continue
- HTTP endpoint test will verify token works

## API Reference

### `validate_auth(client, credentials, mcp_endpoint, verbose=True, retry_on_failure=True)`

Convenience function to validate authentication.

**Parameters:**
- `client`: Authenticated MCP client
- `credentials`: Captured credentials with access_token
- `mcp_endpoint`: MCP endpoint URL
- `verbose`: Print validation progress (default: True)
- `retry_on_failure`: Retry validation if it fails (default: True)

**Returns:**
- `ValidationResult` with validation results

### `AuthValidator(client, credentials, mcp_endpoint, verbose=True, timeout=30.0)`

Auth validator class for custom validation flows.

**Parameters:**
- `client`: Authenticated MCP client
- `credentials`: Captured credentials
- `mcp_endpoint`: MCP endpoint URL
- `verbose`: Print progress (default: True)
- `timeout`: Validation timeout in seconds (default: 30.0)

**Methods:**
- `validate_token()`: Validate token format and expiration
- `validate_http_endpoint()`: Test HTTP endpoint with auth
- `validate_tool_call()`: Test basic tool call functionality
- `validate_response_structure()`: Validate response structure
- `validate_all()`: Run all validation checks

### `ValidationResult`

Result of validation checks.

**Fields:**
- `valid`: True if all critical checks passed
- `checks`: Dict of check results
- `error`: Error message if validation failed
- `duration_ms`: Total validation time in milliseconds

**Methods:**
- `to_dict()`: Convert to dictionary

## Examples

### Basic Usage

```python
from mcp_qa.testing.auth_validator import validate_auth

result = await validate_auth(
    client=client,
    credentials=credentials,
    mcp_endpoint="https://mcp.example.com"
)

if result.valid:
    print("✅ Auth is valid")
else:
    print(f"❌ Auth failed: {result.error}")
```

### Custom Validation

```python
from mcp_qa.testing.auth_validator import AuthValidator

validator = AuthValidator(
    client=client,
    credentials=credentials,
    mcp_endpoint="https://mcp.example.com",
    timeout=60.0
)

# Run specific checks
token_ok, token_msg = await validator.validate_token()
http_ok, http_msg = await validator.validate_http_endpoint()

# Or run all checks
result = await validator.validate_all()
```

### Integration with Test Runner

```python
from mcp_qa.testing.unified_runner import UnifiedMCPTestRunner

async with UnifiedMCPTestRunner(
    mcp_endpoint="https://mcp.example.com",
    verbose=True
) as runner:
    # Check validation result
    if not runner.validation_result.valid:
        print("Validation failed, aborting tests")
        return

    # Run tests
    summary = await runner.run_all()
```
