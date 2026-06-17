# MCP Endpoint Management - KInfra Extension

## Overview

KInfra's SmartInfraManager has been extended with MCP-specific endpoint management functionality to support multi-environment deployments for the Atoms MCP project.

## Features

### 1. **Environment Auto-Detection** (`detect_environment()`)

Automatically detects the current deployment environment by checking:
- `DEPLOY_ENV` environment variable
- `VERCEL_ENV` (Vercel deployments)
- `RENDER` + `RENDER_GIT_BRANCH` (Render deployments)
- Domain patterns from `VERCEL_URL` or `RENDER_EXTERNAL_HOSTNAME`
- Local development indicators (`ATOMS_LOCAL_TEST`, `ATOMS_USE_LOCAL_SERVER`)

Returns: `'prod'`, `'dev'`, or `'local'`

### 2. **MCP Endpoint Resolution** (`get_mcp_endpoint()`)

Resolves the MCP API endpoint URL for any environment:
- **Production**: `https://mcp.atoms.tech/api/mcp`
- **Development**: `https://mcpdev.atoms.tech/api/mcp`
- **Local**: `http://localhost:{port}/api/mcp` (uses configured port)

Supports environment variable overrides:
- `MCP_ENDPOINT_PROD`
- `MCP_ENDPOINT_DEV`
- `MCP_ENDPOINT_LOCAL`

### 3. **Complete Configuration** (`get_mcp_config()`)

Returns comprehensive MCP configuration for an environment:

```python
{
    'endpoint': str,          # MCP API endpoint URL
    'environment': str,       # 'prod', 'dev', or 'local'
    'project': str,          # Project name
    'domain': str,           # Base domain
    'auth_domain': str,      # AuthKit/WorkOS domain
    'public_url': str,       # Public-facing URL
    'port': Optional[int],   # Local port (local env only)
    'tunnel_url': Optional[str], # Tunnel URL (local env only)
}
```

### 4. **Environment Display** (`get_environment_display()`)

Human-readable environment description:
- `"production (https://mcp.atoms.tech/api/mcp)"`
- `"development (https://mcpdev.atoms.tech/api/mcp)"`
- `"local development (http://localhost:50002/api/mcp)"`

## API Reference

### Class Methods

```python
from kinfra import SmartInfraManager

manager = SmartInfraManager(project_name="atoms_mcp", domain="kooshapari.com")

# Detect current environment
env = manager.detect_environment()

# Get endpoint for specific environment
endpoint = manager.get_mcp_endpoint(environment="prod")

# Get complete configuration
config = manager.get_mcp_config(environment="dev")

# Get display string
display = manager.get_environment_display(environment="local")
```

### Convenience Functions

```python
from kinfra import (
    get_mcp_endpoint,
    detect_mcp_environment,
    get_mcp_config,
    set_mcp_environment,
)

# Detect environment
env = detect_mcp_environment()

# Get endpoint
endpoint = get_mcp_endpoint("prod")

# Get full config (auto-detects if environment=None)
config = get_mcp_config()

# Set MCP_ENDPOINT environment variable
set_mcp_environment("dev")
```

## Usage Examples

### Basic Usage

```python
from kinfra import get_mcp_endpoint, get_mcp_config

# Get endpoint for production
prod_endpoint = get_mcp_endpoint("prod")
# Returns: "https://mcp.atoms.tech/api/mcp"

# Get complete dev configuration
dev_config = get_mcp_config("dev")
# Returns: {
#   'endpoint': 'https://mcpdev.atoms.tech/api/mcp',
#   'auth_domain': 'https://auth-dev.atoms.tech',
#   ...
# }
```

### Auto-Detection

```python
from kinfra import detect_mcp_environment, get_mcp_config

# Auto-detect current environment
current_env = detect_mcp_environment()

# Get config for current environment
config = get_mcp_config()  # Uses auto-detected environment
```

### Cross-Environment Testing

```python
from kinfra import get_mcp_config, set_mcp_environment

# Test against different environments
for env in ["local", "dev", "prod"]:
    config = get_mcp_config(env)
    print(f"{env}: {config['endpoint']}")

# Switch to dev environment
set_mcp_environment("dev")
# Sets os.environ["MCP_ENDPOINT"] = "https://mcpdev.atoms.tech/api/mcp"
```

### Integration with atoms_mcp

```python
from kinfra import SmartInfraManager

# Initialize for atoms_mcp project
manager = SmartInfraManager(
    project_name="atoms_mcp",
    domain="kooshapari.com"
)

# Auto-detect and configure
env = manager.detect_environment()
config = manager.get_mcp_config(env)

# Use in FastMCP or other clients
os.environ["MCP_ENDPOINT"] = config["endpoint"]
os.environ["AUTHKIT_DOMAIN"] = config["auth_domain"]
```

## Environment Variables

### Detection Variables

| Variable | Purpose | Values |
|----------|---------|--------|
| `DEPLOY_ENV` | Explicit environment override | `prod`, `dev`, `local` |
| `VERCEL_ENV` | Vercel deployment environment | `production`, `preview`, `development` |
| `RENDER` | Render deployment indicator | `true` |
| `RENDER_GIT_BRANCH` | Render git branch | `main`, `master` (→ prod), others (→ dev) |
| `VERCEL_URL` | Vercel deployment URL | Used for domain pattern matching |
| `ATOMS_LOCAL_TEST` | Local testing flag | Any truthy value |
| `ATOMS_USE_LOCAL_SERVER` | Local server flag | Any truthy value |

### Endpoint Override Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `MCP_ENDPOINT_PROD` | Production endpoint | `https://mcp.atoms.tech/api/mcp` |
| `MCP_ENDPOINT_DEV` | Development endpoint | `https://mcpdev.atoms.tech/api/mcp` |
| `MCP_ENDPOINT_LOCAL` | Local endpoint | `https://atomcp.{domain}/api/mcp` |
| `MCP_ENDPOINT` | Generic endpoint | Used if env matches current |

### Auth Domain Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `AUTHKIT_DOMAIN_PROD` | Production auth | `https://auth.atoms.tech` |
| `AUTHKIT_DOMAIN_DEV` | Development auth | `https://auth-dev.atoms.tech` |
| `FASTMCP_SERVER_AUTH_AUTHKITPROVIDER_AUTHKIT_DOMAIN` | Local auth | `https://decent-hymn-17-staging.authkit.app` |

## Environment Pattern Matching

The system recognizes these domain patterns:

### Production
- `vercel.app`
- `atoms.tech`
- `mcp.atoms.tech`

### Development
- `mcpdev`
- `atoms-dev`
- `preview.vercel.app`

### Local
- `localhost`
- `127.0.0.1`
- `kooshapari.com`

## Integration with Endpoint Registry

The KInfra MCP extensions complement the `config/endpoints.py` endpoint registry in atoms_mcp:

```python
# atoms_mcp/config/endpoints.py pattern
from config.endpoints import EndpointConfig, Environment

endpoint = EndpointConfig.get_endpoint(Environment.PRODUCTION)

# KInfra pattern (same result, more flexible)
from kinfra import get_mcp_endpoint

endpoint = get_mcp_endpoint("prod")
```

### Advantages of KInfra Integration

1. **Auto-detection**: Automatically determines environment from deployment context
2. **Complete config**: Returns full configuration including auth domains, public URLs
3. **Infrastructure integration**: Works with port allocation, tunnel management
4. **Cross-project**: Can be used by any KInfra-based project
5. **Environment setting**: Can programmatically set environment variables

## Complete Example

See `/Users/kooshapari/KInfra/libraries/python/kinfra/examples/mcp_endpoint_example.py` for a comprehensive example.

```bash
cd /Users/kooshapari/KInfra/libraries/python
PYTHONPATH=/Users/kooshapari/KInfra/libraries/python:$PYTHONPATH \
    python3 kinfra/examples/mcp_endpoint_example.py
```

## Migration Note

The core SmartInfraManager infrastructure features are deprecated in favor of ServiceOrchestrator + ServiceManager. However, the MCP endpoint management features are **actively maintained** and will be migrated to the new architecture in v2.0.

For now, you can safely use:
- ✅ `get_mcp_endpoint()`
- ✅ `detect_mcp_environment()`
- ✅ `get_mcp_config()`
- ✅ `set_mcp_environment()`
- ✅ `get_environment_display()`

These functions will continue to work and will be available in the new architecture.

## Files Modified

1. **`/Users/kooshapari/KInfra/libraries/python/kinfra/smart_infra_manager.py`**
   - Added `detect_environment()` method
   - Added `get_mcp_endpoint()` method
   - Added `get_mcp_config()` method
   - Added `get_environment_display()` method
   - Added MCP-specific convenience functions
   - Added environment pattern constants

2. **`/Users/kooshapari/KInfra/libraries/python/kinfra/__init__.py`**
   - Exported MCP-specific functions
   - Added to `__all__` list

3. **`/Users/kooshapari/KInfra/libraries/python/kinfra/examples/mcp_endpoint_example.py`**
   - Created comprehensive usage example

## Testing

All MCP endpoint management features have been tested and verified:

```bash
# Test direct module
cd /Users/kooshapari/KInfra/libraries/python
python3 -c "from kinfra.infrastructure_manager import get_mcp_endpoint; print(get_mcp_endpoint('prod'))"

# Test package exports
python3 -c "from kinfra import get_mcp_endpoint; print(get_mcp_endpoint('dev'))"

# Test full functionality
python3 -c "
from kinfra import detect_mcp_environment, get_mcp_config
env = detect_mcp_environment()
config = get_mcp_config(env)
print(f'{env}: {config[\"endpoint\"]}')
"
```

## Summary

KInfra now provides comprehensive MCP endpoint management with:
- ✅ Automatic environment detection
- ✅ Multi-environment endpoint resolution
- ✅ Complete configuration management
- ✅ Integration with atoms_mcp deployment workflows
- ✅ Backward compatibility with existing code
- ✅ Clean API for cross-environment testing
