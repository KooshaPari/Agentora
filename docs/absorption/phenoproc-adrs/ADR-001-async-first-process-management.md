# ADR-001: Async-First Process Management Architecture

## Status

Accepted

## Context

PhenoProc needs to manage processes within the Phenotype ecosystem. We must decide on the fundamental concurrency model for process operations. The ecosystem is built primarily in Rust and targets modern async/await patterns.

### Requirements

- Non-blocking process operations
- Integration with existing Rust async ecosystem (tokio)
- Efficient resource utilization
- Clean error handling and cancellation
- Compatible with both high-throughput and low-latency use cases

### Options Considered

1. **Blocking/Synchronous API**
   - Simple implementation
   - Forces consumers to manage thread pools
   - Poor scalability for many concurrent processes

2. **Callback-Based (Legacy Async)**
   - Composable but verbose
   - Error handling via callbacks is complex
   - Not idiomatic modern Rust

3. **Async/Await with Tokio**
   - Industry standard for Rust async
   - Composable, readable code
   - Excellent ecosystem support
   - Built-in backpressure mechanisms

4. **Actor Model (Actix)**
   - Message-passing semantics
   - Higher overhead
   - Steeper learning curve

## Decision

We will build PhenoProc with an **async-first architecture** using Tokio as the async runtime.

### Rationale

1. **Ecosystem Alignment**: The Phenotype ecosystem already uses Tokio extensively. Consistency reduces cognitive load.

2. **Performance**: Async/await enables efficient I/O multiplexing without thread-per-connection overhead.

3. **Composability**: Async functions compose naturally, enabling complex process workflows.

4. **Cancellation**: Tokio provides structured cancellation via `JoinHandle::abort()` and drop semantics.

5. **Backpressure**: Tokio's channels and semaphores provide explicit backpressure mechanisms.

### Implementation Details

```rust
// ProcessPool will be async
pub struct ProcessPool {
    // ...
}

impl ProcessPool {
    pub async fn acquire(&self) -> Result<ProcessHandle, PoolError> {
        // Non-blocking acquisition
    }
    
    pub async fn spawn(&self, cmd: Command) -> Result<Child, SpawnError> {
        // Async spawn with proper resource cleanup
    }
}

// Usage
let pool = ProcessPool::builder()
    .max_size(10)
    .build()
    .await?;

let mut proc = pool.acquire().await?;
let output = proc.run("echo hello").await?;
```

### Consequences

#### Positive

- Consistent with Phenotype ecosystem patterns
- Excellent performance characteristics
- Rich ecosystem of compatible libraries
- Clear error propagation via `Result`
- Structured concurrency via tokio::spawn

#### Negative

- Adds dependency on Tokio
- Requires understanding of async Rust (learning curve)
- Some operations may require `spawn_blocking` for true CPU-bound work
- Debug complexity (async stack traces)

#### Mitigations

- Provide sync wrappers where appropriate for simple use cases
- Document async patterns clearly
- Use `tracing` for async-aware logging

## Related Decisions

- ADR-003: Workspace crate organization enables separate async core
- SOTA.md: Research on Tokio vs other runtimes

## References

- [Tokio Documentation](https://tokio.rs/)
- [Async Rust Book](https://rust-lang.github.io/async-book/)
- [SOTA.md - Tokio Async Runtime section](../SOTA.md)

---

**Date**: 2026-04-04
**Author**: PhenoProc Team
