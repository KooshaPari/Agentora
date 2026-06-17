# Pheno Control Center

A centralized orchestration system for managing multiple pheno-sdk projects with unified monitoring, command routing, and multi-tenant infrastructure management.

## Overview

The Pheno Control Center extends KInfra to provide a unified interface for managing multiple pheno-sdk projects (like atoms, zen-mcp-server, etc.) from a single control point. It addresses the key challenges outlined in the PRD:

- **Multi-project orchestration** with dependency management
- **Port conflict resolution** through dynamic allocation
- **Centralized monitoring** with project-grouped status display
- **Command routing** with project context switching
- **Multi-tenant infrastructure** for tunnels, fallback, and proxy services

## Architecture

### Core Components

1. **ProjectRegistry** (`config.py`)
   - YAML-based project configuration
   - Dependency validation and topological sorting
   - Runtime state management

2. **UnifiedMonitorEngine** (`engine.py`)
   - Process and resource state tracking
   - Event-driven monitoring with callbacks
   - Log aggregation and filtering

3. **CLIBridge & CommandRouter** (`cli_bridge.py`)
   - Subprocess management with streaming output
   - Command history and autocomplete
   - Project context switching

4. **MultiTenantManager** (`multi_tenant.py`)
   - Per-project port allocation (fallback, proxy)
   - Shared tunnel management with isolation
   - Coordinated cleanup without conflicts

5. **Enhanced Monitors**
   - **EnhancedMultiProjectMonitor** (`enhanced_monitor.py`) - Rich-based display
   - **EnhancedTUIMonitor** (`tui_monitor.py`) - Textual-based interactive TUI

## Key Features Implemented

### ✅ Completed ARUs

- **ARU-E1**: Configuration and extensibility framework
- **ARU-M1**: Unified Monitor Engine Core
- **ARU-B1**: CLI Bridge and Command Router
- **ARU-T1**: Multi-tenant tunnels and fallback services
- **ARU-C1**: Enhanced CLI monitor with textual TUI

### Multi-Tenancy Highlights

- **Dynamic Port Allocation**: Each project gets unique ports for fallback (9000+n) and proxy (9100+n)
- **Shared Infrastructure**: Multiple projects can share the same fallback/proxy servers
- **Isolated Cleanup**: Stopping one project doesn't affect others using the same infrastructure
- **Tunnel Namespacing**: Project-specific subdomains (e.g., `service.project.kooshapari.com`)

### Monitoring Features

- **Project-Grouped Display**: Processes and resources organized by project
- **Real-time Status**: Live updates of service health and tunnel status
- **Streaming Logs**: Categorized log output with project/process context
- **Multiple UIs**: Rich TUI, Textual interactive TUI, and fallback simple console

## Usage

### Basic Setup

```python
from kinfra.control_center import PhenoControlCenter

# Initialize control center
control_center = PhenoControlCenter()

# Setup components
await control_center.setup()

# Run TUI monitor
await control_center.run_tui_monitor()
```

### Command Line Usage

```bash
# Run the demo
python -m kinfra.control_center.main demo

# Start TUI monitor
python -m kinfra.control_center.main tui

# Start simple monitor
python -m kinfra.control_center.main monitor
```

### Project Configuration Example

Projects are automatically configured with defaults, but can be customized in `~/.kinfra/control_center/projects.yaml`:

```yaml
projects:
  atoms:
    name: atoms
    cli_entry: [atoms, start]
    base_port: 50000
    fallback_port_offset: 1
    proxy_port_offset: 1
    health_endpoint: /health
    tunnel_domain: kooshapari.com
    auto_start: false
    dependencies: []

  zen:
    name: zen
    cli_entry: [zen, start]
    base_port: 50001
    fallback_port_offset: 2
    proxy_port_offset: 2
    health_endpoint: /health
    tunnel_domain: kooshapari.com
    auto_start: false
    dependencies: []
```

### Command Routing Examples

The control center automatically routes commands to appropriate project contexts:

```bash
# These commands are automatically routed:
atoms start          # -> routes to atoms project context
zen status           # -> routes to zen project context
a start              # -> alias for 'atoms start'
z --help             # -> alias for 'zen --help'
```

### Multi-Project Status Display

```
╭──────────────────────────────────────────────────────────────────────────────╮
│                         Pheno Control Center | Uptime: 0:05:23               │
├──────────────────────────────────────────────────────────────────────────────┤
│ ╭─────────────────────────────── Summary ────────────────────────────────╮   │
│ │ Projects      2/2 healthy                                               │   │
│ │ Processes     2/4 running                                               │   │
│ ╰─────────────────────────────────────────────────────────────────────────╯   │
│ ╭───────────────────────── ATOMS (healthy) ──────────────────────────────╮   │
│ │ ╭─────────────────────────────── Processes ─────────────────────────────╮ │ │
│ │ │  Process     State        PID      Port     Tunnel                    │ │ │
│ │ │  atoms       ● Running    12345    50000    ✓                         │ │ │
│ │ ╰─────────────────────────────────────────────────────────────────────────╯ │ │
│ │ ╭─────────────────────────────── Resources ──────────────────────────────╮ │ │
│ │ │  Resource    State           Endpoint                                  │ │ │
│ │ │  postgres    ○ Optional      localhost:5432                           │ │ │
│ │ │  fallback    ● Available     localhost:9001                           │ │ │
│ │ ╰─────────────────────────────────────────────────────────────────────────╯ │ │
│ ╰─────────────────────────────────────────────────────────────────────────╯   │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## Dependencies

### Required
- `pyyaml>=6.0` - Configuration file parsing
- `psutil>=5.9.0` - Process monitoring
- `aiohttp>=3.8.0` - HTTP client/server

### Optional
- `rich` - Enhanced TUI display (recommended)
- `textual` - Interactive TUI components (recommended)
- `PyQt6` - Desktop GUI (planned for ARU-D1)

## Integration with Existing KInfra

The control center is designed to work alongside existing KInfra components:

- **ServiceManager**: Can be used within project contexts
- **TunnelManager**: Extended for multi-tenant operation
- **PortRegistry**: Enhanced with project-aware allocation
- **FallbackServer/ProxyServer**: Made multi-tenant aware

## Configuration Files

The control center creates these configuration files:

```
~/.kinfra/control_center/
├── projects.yaml          # Project configurations
├── runtime_state.json     # Runtime state tracking
└── plugins/               # Plugin directory
```

## Future Enhancements (ARU-D1)

The remaining PyQt desktop application (ARU-D1) would provide:

- Visual project launcher with start/stop buttons
- Embedded terminal widget for command execution
- Tabbed interface for multiple projects
- System tray integration
- Drag-and-drop project configuration

## Testing

```bash
# Run the demo to see all components working together
python -m kinfra.control_center.main demo

# Test individual components
python -c "from kinfra.control_center import ProjectRegistry; pr = ProjectRegistry(); print(pr.list_projects())"
```

## Integration with User Rules

The implementation follows the user's specified rules:

- ✅ Uses pheno-sdk libraries and patterns
- ✅ Terminal UI follows informative style
- ✅ Factory/adapter patterns for extensibility
- ✅ Pythonic design with proper error handling
- ✅ Serial test execution with persistent state

This implementation provides a solid foundation for the complete Pheno Control Center vision while maintaining compatibility with existing KInfra usage patterns.
