# Phenotype Errors

**DEPRECATED**: Use `phenotype-error-core` directly instead.

This crate is a thin re-export wrapper for backwards compatibility.

```toml
# Old (deprecated)
[dependencies]
phenotype-errors = "0.2"

# New (recommended)
[dependencies]
phenotype-error-core = "0.2"
```

## Migration

Replace:
```rust
use phenotype_errors::{ApiError, Result};
```

With:
```rust
use phenotype_error_core::{ApiError, Result};
```
