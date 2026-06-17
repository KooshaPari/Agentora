# ADR-001: Async Runtime Architecture

## Status
**Accepted**

## Date
2026-04-04

## Context

The Phenotype Router Monitor requires an async runtime to execute concurrent health checks, manage timeouts, and handle metrics export operations. This decision is foundational and affects all subsequent architectural choices.

### Requirements

1. **Concurrent Health Checks:** Must execute multiple health checks concurrently without blocking
2. **Timeout Management:** Must support fine-grained timeouts on individual operations
3. **Resource Efficiency:** Must minimize overhead for monitoring operations that run continuously
4. **Ecosystem Compatibility:** Must work with existing Phenotype ecosystem dependencies (reqwest, tokio-based libraries)
5. **Cancellation Safety:** Must properly handle cancellation to prevent resource leaks

### Options Considered

| Runtime | Pros | Cons |
|---------|------|------|
| **Tokio** | Mature, extensive ecosystem, work-stealing scheduler, great performance | Heavier binary size, brings full runtime |
| **async-std** | Smaller, closer to stdlib APIs | Less mature ecosystem, fewer integrations |
| **smol** | Minimal, embeddable | Limited ecosystem, requires more manual work |
| **glommio** (io_uring) | Excellent for I/O heavy workloads | Linux-only, less mature |
| **embassy** (embedded) | Extremely lightweight | Embedded-focused, limited for general use |

## Decision

We will use **Tokio** as the async runtime with the following configuration:

- **Flavor:** Multi-thread work-stealing scheduler (default)
- **Worker Threads:** Equal to number of CPU cores (default)
- **Max Blocking Threads:** 512 (default sufficient for our use case)
- **Enable:** All features (net, process, signal, time)

### Rationale

1. **Ecosystem Dominance:** Tokio is the de facto standard in the Rust async ecosystem. Major libraries (reqwest, hyper, tonic) are built on Tokio.

2. **Performance Characteristics:** Work-stealing scheduler provides excellent throughput for our mixed I/O and light CPU workload pattern.

3. **Maturity:** Production-proven at scale by companies like AWS (Firecracker), Discord, and Fly.io.

4. **Cancellation Support:** Tokio's cancellation tokens provide the safety we need for timeout handling.

5. **Integration:** Seamless integration with `reqwest` (HTTP client) and `opentelemetry` SDK.

## Consequences

### Positive

- Immediate compatibility with all major async libraries
- Rich ecosystem of middleware and instrumentation
- Built-in metrics and tracing integration points
- Excellent documentation and community support

### Negative

- Binary size increase (~500KB for full runtime)
- Dependency on tokio-specific APIs in some cases
- Cannot easily switch runtimes later without significant refactoring

### Mitigations

- Use `async-trait` for public APIs to maintain runtime agnosticism where possible
- Isolate Tokio-specific code in internal modules
- Document the Tokio dependency in architecture documentation

## Implementation Details

### Runtime Configuration

```rust
// src/runtime.rs
use tokio::runtime::{Builder, Runtime};

pub fn create_monitor_runtime() -> Runtime {
    Builder::new_multi_thread()
        .worker_threads(num_cpus::get())
        .thread_name("router-monitor")
        .enable_all()
        .build()
        .expect("Failed to create Tokio runtime")
}
```

### Task Spawning Patterns

```rust
// Fire-and-forget background tasks
 tokio::spawn(async {
    metrics_exporter.run().await;
});

// Scoped tasks with cancellation
let handle = tokio::spawn(async {
    health_checker.run().await
});

// Graceful shutdown
tokio::select! {
    _ = handle => {},
    _ = shutdown_signal.recv() => {
        handle.abort();
    }
}
```

### Timeout Handling

```rust
use tokio::time::{timeout, Duration};

async fn check_with_timeout(
    check: impl Future<Output = CheckResult>,
    duration: Duration
) -> CheckResult {
    match timeout(duration, check).await {
        Ok(result) => result,
        Err(_) => CheckResult::timeout(duration),
    }
}
```

### Cancellation Safety

All async operations must be cancellation-safe:

```rust
// GOOD: Uses channels that handle cancellation
async fn cancellable_check(mut rx: mpsc::Receiver<CheckCommand>) {
    while let Some(cmd) = rx.recv().await {
        // recv() returns None if channel closed (cancelled)
        perform_check(cmd).await;
    }
}

// BAD: May leave resources in inconsistent state
async fn unsafe_check() {
    let conn = pool.acquire().await; // If cancelled here...
    conn.query("SELECT 1").await;    // ...connection leaked
}
```

## Alternatives Considered in Detail

### async-std

**Why not chosen:**
- Smaller ecosystem means more friction integrating with monitoring libraries
- Several key dependencies (reqwest, opentelemetry) prefer Tokio
- Performance characteristics less optimized for our use case

**When it would be better:**
- If minimizing binary size was critical (< 1MB total)
- If we needed runtime-agnostic code for library distribution

### smol

**Why not chosen:**
- Would require building more infrastructure ourselves
- Limited integration with existing telemetry libraries
- Smaller community for support

**When it would be better:**
- For embedded or resource-constrained environments
- When complete control over runtime behavior is needed

## Related Decisions

- ADR-002: Metrics Export Strategy (uses Tokio-based OpenTelemetry)
- ADR-003: Health Check Pattern (relies on Tokio timeouts)

## References

1. Tokio Documentation: https://tokio.rs/
2. Async Rust Book: https://rust-lang.github.io/async-book/
3. Tokio in Production (AWS Firecracker): https://aws.amazon.com/blogs/aws/firecracker-lightweight-virtualization-for-serverless-computing/

## History

| Date | Author | Change |
|------|--------|--------|
| 2026-04-04 | Phenotype Team | Initial decision |
