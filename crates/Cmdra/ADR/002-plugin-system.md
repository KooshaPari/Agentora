# ADR-002: Plugin System Design

## Status
Proposed

## Context
We need extensibility for clikit so users can:
- Add custom commands
- Create new input/output adapters
- Integrate with external systems

## Decision

### Plugin Architecture
1. **Static plugins**: Compile-time plugins via feature flags
2. **Dynamic plugins**: Runtime-loaded via shared libraries

### Plugin Interface
```rust
pub trait Plugin: Send + Sync {
    fn name(&self) -> &str;
    fn version(&self) -> &str;
    fn init(&self) -> Result<()>;
    fn commands(&self) -> Vec<Command>;
    fn cleanup(&self) -> Result<()>;
}
```

### Plugin Manager
- Scans plugin directories
- Loads/unloads plugins
- Provides plugin discovery

## Consequences

### Positive
- Users can extend clikit without modifying core
- Clear plugin API
- Support for both static and dynamic plugins

### Negative
- Plugin API stability required
- Version compatibility tracking
- Security considerations for dynamic loading

## References
- Clap plugin system
- Tower plugin architecture
