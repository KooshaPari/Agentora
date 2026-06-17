# Phenotype Ports Canonical

**DEPRECATED**: Use `phenotype-port-traits` directly instead.

This crate is a thin re-export wrapper for backwards compatibility.

```toml
# Old (deprecated)
[dependencies]
phenotype-ports-canonical = "0.2"

# New (recommended)
[dependencies]
phenotype-port-traits = "0.2"
```

## Migration

Replace:
```rust
use phenotype_ports_canonical::{inbound, outbound};
```

With:
```rust
use phenotype_port_traits::{inbound, outbound};
```
