# MCP-QA Framework Abstraction Guide

This document explains how the MCP-QA framework was abstracted from the Atoms project to be a reusable, project-agnostic testing framework.

## Overview

The framework was extracted from `/atoms/pheno_vendor/mcp_qa/` and generalized to `/pheno-sdk/src/pheno/testing/mcp_qa/` with all Atoms-specific dependencies removed or abstracted.

## Key Abstractions

### 1. Hardcoded URLs → Environment Variables

**Pattern:** Replace all hardcoded project-specific URLs with environment variables that have sensible defaults.

**Files Changed:**
- `oauth/auth_session.py`
- `oauth/credential_broker.py`
- `tui/example_tui_with_status.py`
- `testing/pytest_adapter.py`

**Before:**
```python
base_url: str = "https://mcp.atoms.tech"
oauth_url = "https://mcp.atoms.tech/oauth/authorize"
mcp_endpoint = "https://mcp.atoms.tech/api/mcp"
```

**After:**
```python
base_url: str = os.getenv("MCP_BASE_URL", "http://localhost:8000")
oauth_url = os.getenv("TEST_OAUTH_URL", f"{os.getenv('MCP_BASE_URL')}/oauth/authorize")
mcp_endpoint = os.getenv("MCP_ENDPOINT", f"{os.getenv('MCP_BASE_URL')}/api/mcp")
```

**Migration for Projects:**
```bash
# Set in your project's environment
export MCP_BASE_URL="https://your-server.com"
export MCP_ENDPOINT="https://your-server.com/api/mcp"
```

### 2. Project-Specific Adapters → Base Classes

**Pattern:** Replace concrete project adapters with abstract base classes that projects extend.

**Files Changed:**
- `core/base/test_runner.py`
- `oauth/session_oauth_broker.py`
- `testing/runner_old.py`
- `testing/tdd_test_runner.py`
- `tui/dashboard.py`

**Before (Atoms-specific):**
```python
from framework.adapters import AtomsMCPClientAdapter

worker_adapter = AtomsMCPClientAdapter(worker_client, verbose_on_fail=True)
```

**After (Framework-level):**
```python
# Framework provides base class
from pheno.testing.mcp_qa import BaseClientAdapter

# Projects implement their own adapter
class MyProjectClientAdapter(BaseClientAdapter):
    def _process_result(self, result, tool_name, params):
        # Your project-specific result processing
        return result.content if hasattr(result, 'content') else result

    def _log_error(self, error, tool_name, params):
        # Your project-specific error logging
        logger.error(f"{tool_name} failed: {error}")
```

**Migration for Projects:**
1. Create your own adapter class extending `BaseClientAdapter`
2. Implement `_process_result()` and `_log_error()` methods
3. Replace all references to `AtomsMCPClientAdapter` with your adapter

### 3. Logger Names

**Pattern:** Change project-specific logger names to framework-level names.

**Files Changed:**
- `core/enhanced_adapter.py`
- `tui/dashboard.py`

**Before (Atoms-specific):**
```python
logger = logging.getLogger("atoms.mcp")
logger = logging.getLogger("atoms.tui")
```

**After (Framework-level):**
```python
logger = logging.getLogger("pheno.testing.mcp_qa.core")
logger = logging.getLogger("pheno.testing.mcp_qa.tui")
```

**Migration for Projects:**
- Use your own logger names in your adapter implementations
- The framework's internal loggers use `pheno.testing.mcp_qa.*`

### 4. Metadata → Abstract Methods

**Pattern:** Replace hardcoded metadata with abstract methods that projects implement.

**Files Changed:**
- `core/base/test_runner.py`

**Before (Atoms-specific):**
```python
metadata = {
    "endpoint": "https://mcp.atoms.tech/api/mcp",
    "project": "atoms",
    "auth_status": "authenticated"
}
```

**After (Framework-level):**
```python
class BaseTestRunner(ABC):
    @abstractmethod
    def _get_metadata(self) -> Dict[str, Any]:
        """Return project-specific metadata."""
        pass

# Projects implement:
class MyProjectRunner(BaseTestRunner):
    def _get_metadata(self):
        return {
            "endpoint": self.client_adapter.endpoint,
            "project": "myproject",
            "environment": "production"
        }
```

**Migration for Projects:**
- Implement `_get_metadata()` in your test runner
- Return any metadata you want in test reports

### 5. Import Paths

**Pattern:** Update all internal imports to use the new pheno-sdk location.

**Files Changed:** 67 files (see migration output)

**Before:**
```python
from mcp_qa.core.base.test_runner import BaseTestRunner
from mcp_qa.reporters import ConsoleReporter
```

**After:**
```python
from pheno.testing.mcp_qa import BaseTestRunner
from pheno.testing.mcp_qa import ConsoleReporter
```

**Migration for Projects:**
- Update all imports to use `pheno.testing.mcp_qa.*`
- Use the convenience imports from `pheno.testing.mcp_qa.__init__`

## Files Modified Summary

### Abstraction Changes (6 files)
1. `core/base/test_runner.py` - Commented out AtomsMCPClientAdapter references
2. `oauth/auth_session.py` - Replaced hardcoded URLs with env vars
3. `oauth/session_oauth_broker.py` - Updated adapter imports
4. `testing/runner_old.py` - Updated adapter imports
5. `testing/tdd_test_runner.py` - Updated adapter imports
6. `tui/dashboard.py` - Updated logger name and adapter imports

### Import Path Updates (67 files)
All files updated to use `pheno.testing.mcp_qa.*` instead of `mcp_qa.*`

## Configuration Reference

### Environment Variables

The framework expects these environment variables (all optional with defaults):

```bash
# Server Configuration
MCP_BASE_URL="http://localhost:8000"           # Base URL for MCP server
MCP_ENDPOINT="http://localhost:8000/api/mcp"   # MCP API endpoint

# OAuth Configuration (if using OAuth)
WORKOS_CLIENT_ID="client_xxx"
FASTMCP_SERVER_AUTH_AUTHKITPROVIDER_BASE_URL="https://your-server.com"
FASTMCP_SERVER_AUTH_AUTHKITPROVIDER_AUTHKIT_DOMAIN="https://your-authkit.app"
TEST_OAUTH_URL="https://your-server.com/oauth/authorize"

# Test Configuration
TEST_PARALLEL_WORKERS="4"
TEST_CACHE_ENABLED="true"
TEST_TIMEOUT="60"

# Demo Credentials (for testing without OAuth)
FASTMCP_DEMO_USER="demo@example.com"
FASTMCP_DEMO_PASS="demo_password"
```

## Migration Checklist

For projects migrating from Atoms or implementing the framework:

### 1. Setup
- [ ] Install pheno-sdk: `pip install pheno-sdk[testing]`
- [ ] Set environment variables for your server
- [ ] Create configuration directory for cache: `~/.mcp_test_cache`

### 2. Create Adapter
- [ ] Create `YourProjectClientAdapter(BaseClientAdapter)`
- [ ] Implement `_process_result()` method
- [ ] Implement `_log_error()` method
- [ ] Store any project-specific attributes (e.g., endpoint)

### 3. Create Test Runner
- [ ] Create `YourProjectTestRunner(BaseTestRunner)`
- [ ] Implement `_get_metadata()` method
- [ ] Optionally override `_get_category_order()`
- [ ] Optionally override `_extract_base_url()`

### 4. Write Tests
- [ ] Import test registry: `from pheno.testing.mcp_qa.core.test_registry import register_test`
- [ ] Decorate test functions with `@register_test(category, tool_name)`
- [ ] Write async test functions that accept `client_adapter`
- [ ] Return `{"success": True}` or raise assertions

### 5. Run Tests
- [ ] Create FastMCP client instance
- [ ] Wrap in your adapter
- [ ] Create runner with adapter
- [ ] Call `runner.run_all()` or `runner.run_all(categories=["core"])`

## Examples

### Complete Adapter Implementation

```python
from pheno.testing.mcp_qa import BaseClientAdapter
import json
import logging

logger = logging.getLogger("myproject.tests")

class MyProjectClientAdapter(BaseClientAdapter):
    """MCP client adapter for MyProject."""

    def __init__(self, client, verbose_on_fail=False):
        super().__init__(client, verbose_on_fail)
        # Store project-specific attributes
        self.endpoint = getattr(client, 'mcp_url', 'http://localhost:8000')
        self.project_name = "myproject"

    def _process_result(self, result, tool_name, params):
        """Transform FastMCP result to project format."""
        # Handle FastMCP CallToolResult format
        if hasattr(result, 'content'):
            content = result.content
            # FastMCP returns list of content blocks
            if isinstance(content, list) and len(content) > 0:
                # Extract text from first block
                first_block = content[0]
                if hasattr(first_block, 'text'):
                    return first_block.text
                return first_block
            return content

        # Return as-is if not FastMCP format
        return result

    def _log_error(self, error, tool_name, params):
        """Log error with project-specific formatting."""
        logger.error(f"Tool call failed: {tool_name}")
        logger.error(f"Params: {json.dumps(params, indent=2, default=str)}")
        logger.error(f"Error: {error}")

        if self.verbose_on_fail:
            # Print detailed error to console
            print(f"\n{'='*60}")
            print(f"TOOL CALL FAILURE: {tool_name}")
            print(f"{'='*60}")
            print(f"Parameters:")
            print(json.dumps(params, indent=2, default=str))
            print(f"\nError:")
            print(str(error))
            print(f"{'='*60}\n")
```

### Complete Runner Implementation

```python
from pheno.testing.mcp_qa import BaseTestRunner, ConsoleReporter, JSONReporter
from typing import Dict, Any, List

class MyProjectTestRunner(BaseTestRunner):
    """Test runner for MyProject."""

    def _get_metadata(self) -> Dict[str, Any]:
        """Return project-specific metadata for reports."""
        return {
            "project": "myproject",
            "endpoint": self.client_adapter.endpoint,
            "environment": os.getenv("ENVIRONMENT", "development"),
            "version": "1.0.0"
        }

    def _get_category_order(self) -> List[str]:
        """Define test execution order."""
        return [
            "health",      # Health checks first
            "core",        # Core functionality
            "entity",      # Entity operations
            "query",       # Query operations
            "integration"  # Integration tests last
        ]

    def _extract_base_url(self) -> str:
        """Extract base URL from client for connection pool."""
        # Custom URL extraction logic
        if hasattr(self.client_adapter, 'endpoint'):
            return self.client_adapter.endpoint
        return super()._extract_base_url()

# Usage
async def main():
    from fastmcp import FastMCP

    # Create client
    client = FastMCP("MyProject")
    await client.connect("http://localhost:8000/api/mcp")

    # Create adapter and runner
    adapter = MyProjectClientAdapter(client, verbose_on_fail=True)
    runner = MyProjectTestRunner(
        client_adapter=adapter,
        cache=True,
        parallel=True,
        parallel_workers=4,
        reporters=[
            ConsoleReporter(show_running=True),
            JSONReporter(output_file="results.json")
        ]
    )

    # Run tests
    summary = await runner.run_all()

    # Print summary
    print(f"\nTest Summary:")
    print(f"  Passed:  {summary['passed']}")
    print(f"  Failed:  {summary['failed']}")
    print(f"  Skipped: {summary['skipped']}")
    print(f"  Cached:  {summary['cached']}")
```

## No Longer Supported

The following Atoms-specific features are **not** included in the framework:

1. **AtomsMCPClientAdapter** - Projects must create their own adapter
2. **Atoms-specific error handling** - Projects implement in `_log_error()`
3. **Atoms-specific result parsing** - Projects implement in `_process_result()`
4. **Hardcoded Atoms URLs** - Use environment variables
5. **Atoms workspace/entity logic** - Projects implement in their tests

## Support

For questions or issues:
1. Check this guide for common patterns
2. Review the README.md for usage examples
3. Examine the base classes (`BaseTestRunner`, `BaseClientAdapter`)
4. Look at the example implementations in `examples/`

## Version History

- **0.2.0** (Current) - Extracted from Atoms, fully abstracted
- **0.1.0** - Original Atoms-specific implementation
