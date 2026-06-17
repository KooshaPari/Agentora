# Pheno Control Center - TUI Components

Enhanced TUI (Text User Interface) components for the Pheno Control Center, providing a unified monitoring and control interface for multiple pheno-sdk projects.

## Features

- **Multi-Project Monitoring**: Monitor multiple pheno-sdk projects simultaneously
- **Interactive Command Execution**: Execute commands with real-time output streaming
- **Scrollable Log Panels**: View and filter logs from all projects
- **Real-time Status Updates**: Live status monitoring with automatic refresh
- **Project Grouping**: Organize processes and resources by project
- **Command History**: Track and replay previous commands
- **Flexible TUI Backend**: Support for both Textual and Rich TUI frameworks

## Components

### Core Components

- **`TUIMonitor`**: Main TUI monitor with project grouping
- **`ProjectRegistry`**: Registry for managing multiple projects
- **`MonitorEngine`**: Monitoring engine for all projects
- **`PhenoControlCenter`**: Main control center application

### Data Models

- **`ProcessInfo`**: Information about monitored processes
- **`ResourceInfo`**: Information about monitored resources
- **`LogEntry`**: Log entries with project context

### CLI Integration

- **`CLIBridge`**: Bridge between TUI and pheno-cli commands
- **`CommandRouter`**: Routes commands to appropriate handlers
- **`CommandExecutor`**: High-level command execution interface

## Usage

### Basic Usage

```python
from pheno_cli.tui.monitors import run_control_center

# Run the control center
await run_control_center()
```

### Advanced Usage

```python
from pheno_cli.tui.monitors import (
    ProjectRegistry,
    MonitorEngine,
    TUIMonitor
)

# Create components
project_registry = ProjectRegistry()
monitor_engine = MonitorEngine()

# Register projects
project_registry.register_project("atoms", {
    "name": "atoms",
    "description": "Atoms MCP Server",
    "default_port": 50002
})

# Add processes
from pheno_cli.tui.enhanced_monitor import ProcessInfo
process_info = ProcessInfo(
    name="atoms-mcp",
    project="atoms",
    pid=12345,
    port=50002,
    state="running"
)
monitor_engine.add_process("atoms", process_info)

# Create and run monitor
monitor = TUIMonitor(
    project_registry=project_registry,
    monitor_engine=monitor_engine
)
await monitor.run()
```

### Command Line Interface

```bash
# Launch the control center
pheno ui monitor

# Launch with specific options
pheno ui monitor --no-textual --refresh-interval 1.0

# Show project status
pheno ui monitor status

# List available projects
pheno ui monitor projects
```

## TUI Frameworks

The TUI components support multiple backends:

### Textual (Recommended)
- Full-featured TUI framework
- Interactive widgets and layouts
- Keyboard navigation
- Rich text formatting

### Rich (Fallback)
- Simpler TUI framework
- Basic layout support
- Good for environments where Textual isn't available

### Simple Console (Fallback)
- Basic console output
- No external dependencies
- Minimal functionality

## Project Configuration

Projects are configured with the following structure:

```python
project_config = {
    "name": "project-name",
    "description": "Project Description",
    "default_port": 8080,
    "tunnel_domain": "project.example.com",
    "processes": ["process1", "process2"],
    "resources": ["resource1", "resource2"]
}
```

## Command Execution

Commands are executed through the CLI bridge and support:

- **Project Commands**: `atoms start`, `zen logs`, `byteport stop`
- **General Commands**: `help`, `status`, `history`, `clear`
- **Real-time Output**: Streaming stdout/stderr with color coding
- **Command History**: Track and replay previous commands
- **Validation**: Command validation and error handling

## Event System

The monitor engine supports event-driven updates:

```python
def handle_event(event_type: str, event_data: dict):
    if event_type == 'process_added':
        print(f"Process added: {event_data['process']}")
    elif event_type == 'log_entry':
        print(f"Log: {event_data['entry']}")

monitor_engine.subscribe_to_events(handle_event)
```

## Dependencies

### Required
- Python 3.8+
- asyncio
- dataclasses
- typing

### Optional
- `textual` - For full TUI support
- `rich` - For Rich TUI support
- `typer` - For CLI interface

## Installation

```bash
# Install with textual support
pip install textual rich typer

# Or install minimal dependencies
pip install rich typer
```

## Examples

### Demo Script

Run the demo script to see the TUI components in action:

```bash
python demo_tui.py
```

### Test Script

Run the test script to verify functionality:

```bash
python test_tui.py
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Pheno Control Center                     │
├─────────────────────────────────────────────────────────────┤
│  TUIMonitor  │  ProjectRegistry  │  MonitorEngine │
├─────────────────────────────────────────────────────────────┤
│  CLIBridge  │  CommandRouter  │  CommandExecutor            │
├─────────────────────────────────────────────────────────────┤
│  Textual TUI  │  Rich TUI  │  Simple Console               │
└─────────────────────────────────────────────────────────────┘
```

## Contributing

When adding new TUI components:

1. Follow the existing patterns for data models
2. Add proper type hints and documentation
3. Include tests for new functionality
4. Update this README with new features
5. Ensure compatibility with both Textual and Rich backends

## Troubleshooting

### Common Issues

1. **Textual not available**: Install with `pip install textual`
2. **Rich not available**: Install with `pip install rich`
3. **Command execution fails**: Check pheno-cli installation
4. **TUI not responding**: Try `--no-textual` flag

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Fallback Mode

If both Textual and Rich are unavailable, the system will fall back to simple console output.
