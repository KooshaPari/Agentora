# Widget Compatibility Layer for mcp-QA

## Overview

The `widgets_compat.py` module provides a comprehensive backward compatibility layer for mcp-QA TUI widgets, allowing existing code to work without modification while internally using the enhanced tui-kit widgets via protocol-based adapters.

## Features

### 🔄 Zero-Code-Change Migration
- Existing mcp-QA code continues to work without any modifications
- Same API surface as original dashboard.py widgets
- Deprecation warnings guide users to new API with detailed migration instructions

### 🎯 Protocol-Based Dependency Injection
- No hard dependencies on specific implementations
- Adapters expose minimal protocol interfaces
- Works with any client implementing the required methods
- Graceful degradation when dependencies are missing

### ✨ Enhanced Features (Opt-In)
- Token refresh metrics and sparklines (OAuth)
- Server health check history and trends (Server)
- Bandwidth tracking and latency visualization (Tunnel)
- System resource monitoring with threshold alerts (Resource)

### 🛡️ Graceful Fallbacks
- Works even if tui-kit is not installed (basic display)
- Handles missing clients without errors
- Clear error messages when configuration is incomplete

## Architecture

```
mcp-QA Code (Legacy)
        ↓
widgets_compat.py (This file)
        ↓
    ┌───────────────┐
    │   Adapters    │  (Protocol conversion)
    │ MCPClient     │
    │ OAuthCache    │
    └───────────────┘
        ↓
tui-kit Widgets (Enhanced)
        ↓
    Display/Logic
```

## Components

### Wrapper Classes

All wrapper classes maintain exact API compatibility with the original dashboard.py widgets:

#### 1. **OAuthStatusWidget**
Monitors OAuth token status with cache validation and expiry tracking.

**Original API (still works):**
```python
from mcp_qa.tui.dashboard import OAuthStatusWidget

oauth_client = CachedOAuthClient("https://api.example.com")
widget = OAuthStatusWidget(oauth_cache_client=oauth_client)
await widget.refresh_status()
```

**New API (recommended):**
```python
from tui_kit.widgets import OAuthStatusWidget

widget = OAuthStatusWidget(
    oauth_cache_client=oauth_client,
    show_metrics=True,          # Token refresh metrics
    show_sparklines=True,        # Latency trends
    auto_refresh_interval=60.0  # Configurable refresh
)
```

#### 2. **ServerStatusWidget**
Monitors MCP server connection status with health checks.

**Original API (still works):**
```python
from mcp_qa.tui.dashboard import ServerStatusWidget
from mcp_qa.core.adapters import AtomsMCPClientAdapter

client_adapter = AtomsMCPClientAdapter(client)
widget = ServerStatusWidget(client_adapter=client_adapter)
await widget.refresh_status()
```

**New API (recommended):**
```python
from tui_kit.widgets import ServerStatusWidget
from mcp_qa.tui.widgets_compat import MCPClientAdapter

# Wrap adapter for protocol compatibility
protocol_adapter = MCPClientAdapter(mcp_client_adapter)

widget = ServerStatusWidget(
    client_adapter=protocol_adapter,
    check_interval=10.0,     # Auto health checks
    max_history=50,          # Enhanced history
    stream_capture=capture   # Log integration
)
```

#### 3. **TunnelStatusWidget**
Monitors tunnel status for local development (ngrok, Cloudflare, custom).

**Original API (still works):**
```python
from mcp_qa.tui.dashboard import TunnelStatusWidget

tunnel_config = {"type": "ngrok", "port": 4040}
widget = TunnelStatusWidget(tunnel_config=tunnel_config)
await widget.refresh_status()
```

**New API (recommended):**
```python
from tui_kit.widgets import TunnelStatusWidget

widget = TunnelStatusWidget(
    tunnel_config=tunnel_config,
    enable_bandwidth_tracking=True,  # Upload/download metrics
    enable_latency_tracking=True,    # Latency sparklines
    latency_history_size=50
)
```

#### 4. **ResourceStatusWidget**
Monitors resources (database, Redis, API limits, system metrics).

**Original API (still works):**
```python
from mcp_qa.tui.dashboard import ResourceStatusWidget

resource_config = {
    "check_db": True,
    "check_redis": True,
    "check_api_limits": True
}
widget = ResourceStatusWidget(resource_config=resource_config)
await widget.refresh_status()
```

**New API (recommended):**
```python
from tui_kit.widgets import ResourceStatusWidget

widget = ResourceStatusWidget(
    resource_config=resource_config,
    enable_sparklines=True,        # Trend visualization
    enable_system_monitoring=True, # CPU/memory/disk/network
    history_size=50,
    check_interval=5.0
)

# Optional: Set custom thresholds
widget.set_thresholds('cpu', warning=70.0, critical=90.0)
```

### Protocol Adapters

#### **MCPClientAdapter**
Adapts mcp-QA client to tui-kit ServerStatusWidget protocol.

```python
from mcp_qa.tui.widgets_compat import MCPClientAdapter

# Wrap your mcp-QA client adapter
protocol_adapter = MCPClientAdapter(mcp_client_adapter)

# Use with tui-kit widget
widget = ServerStatusWidget(client_adapter=protocol_adapter)
```

**Protocol Requirements:**
- `endpoint: str` property
- `async list_tools() -> List[Dict[str, Any]]` method

#### **MCPOAuthCacheAdapter**
Adapts mcp-QA OAuth cache client to tui-kit protocol.

```python
from mcp_qa.tui.widgets_compat import MCPOAuthCacheAdapter

# Wrap your OAuth client
adapter = MCPOAuthCacheAdapter(oauth_client)

# Use with tui-kit widget
widget = OAuthStatusWidget(oauth_cache_client=adapter)
```

**Protocol Requirements:**
- `_get_cache_path() -> Path` method

### Utility Functions

#### **create_compatible_widgets()**
Convenience function to create all widgets at once.

```python
from mcp_qa.tui.widgets_compat import create_compatible_widgets

widgets = create_compatible_widgets(
    oauth_cache_client=oauth_client,
    client_adapter=mcp_adapter,
    tunnel_config={"type": "ngrok"},
    resource_config={"check_db": True},
    suppress_warnings=True  # Optional: suppress deprecation warnings
)

# Access widgets
oauth_widget = widgets['oauth']
server_widget = widgets['server']
tunnel_widget = widgets['tunnel']
resource_widget = widgets['resource']
```

#### **check_tui_kit_available()**
Check if tui-kit is installed and available.

```python
from mcp_qa.tui.widgets_compat import check_tui_kit_available

if check_tui_kit_available():
    print("tui-kit is available - using enhanced widgets")
else:
    print("tui-kit not installed - using basic fallback")
```

#### **get_migration_guide()**
Get comprehensive migration guide text.

```python
from mcp_qa.tui.widgets_compat import get_migration_guide

# Print detailed migration instructions
print(get_migration_guide())
```

## Migration Path

### Phase 1: Keep Everything Working (Immediate)
No changes needed! Your existing code continues to work.

```python
# This still works exactly as before
from mcp_qa.tui.dashboard import OAuthStatusWidget
widget = OAuthStatusWidget(oauth_cache_client=client)
```

### Phase 2: Update Imports (5 minutes)
Change imports to use tui-kit directly.

```python
# Change this:
from mcp_qa.tui.dashboard import OAuthStatusWidget

# To this:
from tui_kit.widgets import OAuthStatusWidget
```

### Phase 3: Wrap Adapters (10 minutes)
For ServerStatusWidget, wrap your client adapter.

```python
from tui_kit.widgets import ServerStatusWidget
from mcp_qa.tui.widgets_compat import MCPClientAdapter

protocol_adapter = MCPClientAdapter(mcp_adapter)
widget = ServerStatusWidget(client_adapter=protocol_adapter)
```

### Phase 4: Enable New Features (Optional)
Take advantage of enhanced features.

```python
widget = OAuthStatusWidget(
    oauth_cache_client=client,
    show_metrics=True,           # Enable metrics
    show_sparklines=True,        # Enable trends
    auto_refresh_interval=30.0   # Customize refresh
)
```

## Deprecation Warnings

The compatibility layer emits helpful deprecation warnings:

```
DeprecationWarning:
mcp_qa.tui.dashboard.OAuthStatusWidget is deprecated and will be removed in a future version.
Please migrate to tui_kit.widgets.OAuthStatusWidget.

Migration guide:
# Old code (still works):
from mcp_qa.tui.dashboard import OAuthStatusWidget
widget = OAuthStatusWidget(oauth_cache_client=client)

# New code (recommended):
from tui_kit.widgets import OAuthStatusWidget
widget = OAuthStatusWidget(
    oauth_cache_client=client,
    show_metrics=True,
    show_sparklines=True,
    auto_refresh_interval=60.0
)
```

### Suppressing Warnings

For testing or gradual migration:

```python
# Suppress for individual widget
widget = OAuthStatusWidget(
    oauth_cache_client=client,
    _skip_deprecation_warning=True
)

# Or use batch creation with suppression
widgets = create_compatible_widgets(
    oauth_cache_client=client,
    suppress_warnings=True
)

# Or globally
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
```

## Error Handling

### Missing tui-kit
If tui-kit is not installed, widgets gracefully fall back to basic display:

```
RuntimeWarning: tui-kit not installed. Install with: pip install tui-kit
Falling back to basic display without enhanced features.
```

### Missing Client
When no client is configured, widgets show clear status:

```python
# This is safe - no errors
widget = ServerStatusWidget()  # Shows "No client configured"

# Add client later
widget.set_client_adapter(my_adapter)
await widget.refresh_status()
```

## Testing

The compatibility layer includes verification scripts:

```bash
# Verify file structure and syntax
cd /path/to/mcp-QA
python3 verify_compat.py

# Run comprehensive tests (requires tui-kit)
python3 -m pytest mcp_qa/tui/test_compat.py
```

## Benefits

### For Existing Code
- ✅ No breaking changes
- ✅ Immediate access to bug fixes
- ✅ Gradual migration path
- ✅ Clear deprecation guidance

### For New Code
- ✅ Enhanced features
- ✅ Better performance
- ✅ Protocol-based flexibility
- ✅ Standalone tui-kit package

## Support

### Documentation
- tui-kit docs: https://docs.pheno-sdk.dev/tui-kit
- Migration guide: https://docs.pheno-sdk.dev/migration/tui-widgets
- Examples: `/path/to/tui-kit/examples/`

### Getting Help
- File issues: https://github.com/pheno-sdk/tui-kit/issues
- Discussions: https://github.com/pheno-sdk/tui-kit/discussions

## Version Compatibility

| mcp-QA Version | tui-kit Version | Compatibility Layer |
|----------------|-----------------|---------------------|
| 0.x - 1.x      | Not required    | Built-in widgets    |
| 2.0+           | 0.1.0+          | widgets_compat.py   |

## Future Plans

- **v2.1**: Compatibility layer with full feature parity
- **v2.2**: Deprecation warnings added
- **v3.0**: Compatibility layer marked deprecated
- **v4.0**: Direct tui-kit dependency (breaking change)

The compatibility layer will be maintained for at least 2 major versions after tui-kit integration.

---

**Created**: 2025
**Author**: pheno-sdk team
**License**: Same as mcp-QA
