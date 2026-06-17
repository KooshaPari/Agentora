# ADR-002: Command Deduplication via Content-Addressed Cache

## Status

Accepted

## Context

In process-heavy workloads, the same command may be invoked multiple times simultaneously or in rapid succession. Without deduplication, this causes:
- Wasted CPU cycles
- Memory pressure from duplicate processes
- Increased I/O contention
- Resource exhaustion under load

### Problem Statement

Consider a build system where multiple tasks depend on the same generated header. Without deduplication:

```
Task A ──> Run codegen ──┐
                          ├──-> 3 concurrent codegen processes (wasteful)
Task B ──> Run codegen ──┤
                          │
Task C ──> Run codegen ──┘
```

With deduplication:

```
Task A ──> Run codegen ───┐
                           ├──-> 1 process, 3 receivers (efficient)
Task B ──> Wait for ──────┤
                           │
Task C ──> Wait for ──────┘
```

### Requirements

- Coalesce in-flight identical commands
- Cache completed command results
- Configurable TTL for cached results
- Memory-bounded cache
- Thread-safe for concurrent access
- Minimal latency overhead for cache hits

### Options Considered

1. **No Deduplication**
   - Simplest implementation
   - Wasteful under load
   - Unacceptable for production

2. **Simple In-Flight Deduplication Only**
   - Hash map of running commands
   - New waiters join existing command
   - No caching of completed results
   - Good for burst handling, misses optimization opportunity

3. **Content-Addressed Cache with TTL**
   - Cache keyed by command content hash
   - Results stored with expiration
   - Best of both worlds
   - Higher memory usage

4. **External Cache (Redis/Memcached)**
   - Distributed cache
   - Network overhead
   - Overkill for single-node use case

## Decision

We will implement **content-addressed command deduplication with both in-flight coalescing and result caching**.

### Rationale

1. **Content Hashing**: SHA-256 of normalized command (executable + args + env + working dir) provides unique identification

2. **Two-Level Deduplication**:
   - **In-flight**: Commands currently running are tracked; new identical commands wait for completion
   - **Completed**: Results cached with configurable TTL

3. **Memory Safety**: Bounded LRU eviction prevents unbounded growth

4. **Zero-Copy Results**: Successful results can be cheaply cloned or referenced

### Implementation Details

```rust
pub struct DedupCache {
    // In-flight commands being executed
    in_flight: DashMap<CommandHash, Vec<Waker>>,
    
    // Completed results with TTL
    completed: DashMap<CommandHash, CachedResult>,
    
    // LRU eviction tracking
    lru: Mutex<LruCache<CommandHash, ()>>,
}

pub struct CommandFingerprint {
    pub executable_hash: [u8; 32],
    pub args_hash: [u8; 32],
    pub env_hash: [u8; 32],
    pub working_dir_hash: [u8; 32],
}

impl DedupCache {
    pub async fn execute_or_wait(
        &self,
        cmd: Command,
    ) -> Result<Output, DedupError> {
        let fingerprint = cmd.fingerprint();
        
        // Check completed cache
        if let Some(cached) = self.completed.get(&fingerprint) {
            if !cached.is_expired() {
                return Ok(cached.output.clone());
            }
        }
        
        // Check in-flight
        if self.in_flight.contains_key(&fingerprint) {
            // Wait for completion
            return self.wait_for_completion(fingerprint).await;
        }
        
        // Execute new command
        self.execute_and_cache(fingerprint, cmd).await
    }
}
```

### Configuration

```rust
pub struct DedupConfig {
    /// Maximum number of cached results
    pub cache_capacity: usize,
    
    /// Default TTL for successful results
    pub success_ttl: Duration,
    
    /// TTL for failed results (usually shorter)
    pub failure_ttl: Duration,
    
    /// Whether to cache failed results at all
    pub cache_failures: bool,
}

impl Default for DedupConfig {
    fn default() -> Self {
        Self {
            cache_capacity: 1000,
            success_ttl: Duration::from_secs(300),
            failure_ttl: Duration::from_secs(60),
            cache_failures: false,
        }
    }
}
```

### Consequences

#### Positive

- Significant resource savings under load
- Faster response times for cached commands
- Natural backpressure (commands naturally coalesce)
- Transparent to callers (appears as normal execution)

#### Negative

- Memory overhead for cache storage
- Cache invalidation complexity
- Potential for stale results (mitigated by TTL)
- Hash computation overhead (negligible vs process spawn)

#### Mitigations

- Configurable cache size limits
- TTL-based expiration
- Manual invalidation API for critical updates
- Metrics for cache hit/miss rates

## Related Decisions

- ADR-001: Async-first architecture enables efficient waiting
- ADR-003: Separate pheno-proc-dedup crate

## References

- [SOTA.md - Process Pools section](../SOTA.md)
- [Bazel Remote Cache](https://bazel.build/remote/caching) (similar concepts)

---

**Date**: 2026-04-04
**Author**: PhenoProc Team
