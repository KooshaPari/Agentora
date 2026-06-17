# ADR-003: Five-Crate Workspace Organization

## Status

Accepted

## Context

PhenoProc encompasses multiple distinct capabilities: process management, deduplication, queuing, shared memory, and Unix domain sockets. We must decide how to structure these components within the Rust workspace.

### Options Considered

1. **Single Monolithic Crate**
   - `pheno-proc`: All functionality
   - Simple dependency management
   - Forces consumers to depend on all features
   - Poor compile-time parallelism
   - All-or-nothing feature flags

2. **Two-Crate Split (Core + IPC)**
   - `pheno-proc-core`: Process management + dedup + queue
   - `pheno-proc-ipc`: Shared memory + UDS
   - Some separation but core remains large
   - Mixed abstraction levels

3. **Five-Crate Granular Split** (Selected)
   - `pheno-proc-core`: Process lifecycle, pools
   - `pheno-proc-dedup`: Command deduplication
   - `pheno-proc-queue`: Priority task queue
   - `pheno-proc-shm`: Shared memory primitives
   - `pheno-proc-uds`: Unix domain sockets
   - Maximum flexibility
   - Clear dependencies

4. **Per-Feature Crates (10+ crates)**
   - Too granular
   - Dependency hell
   - Maintenance overhead
   - Noisy version management

## Decision

We will organize PhenoProc into **five focused crates** within a Cargo workspace.

### Crate Hierarchy

```
pheno-proc-core (foundational)
    └── pheno-proc-queue (uses core for worker processes)
    └── pheno-proc-dedup (optional, uses core for execution)

pheno-proc-shm (standalone IPC primitive)
pheno-proc-uds (standalone IPC primitive)
```

### Rationale

1. **Single Responsibility**: Each crate has one clear purpose
2. **Dependency Clarity**: Consumers depend only on what they need
3. **Compile Parallelism**: Independent crates compile in parallel
4. **Version Independence**: Crates can version independently if needed
5. **Testing Isolation**: Each crate has focused test suite

### Crate Details

#### pheno-proc-core

**Purpose**: Process lifecycle management and pools

```rust
// Key types
pub struct ProcessPool;
pub struct ManagedProcess;
pub struct ProcessHandle;
pub struct Command;
pub struct Output;
```

**Dependencies**: tokio, tracing

#### pheno-proc-dedup

**Purpose**: Command deduplication with content-addressed caching

```rust
// Key types
pub struct DedupCache;
pub struct CommandFingerprint;
pub struct DedupConfig;
```

**Dependencies**: pheno-proc-core, dashmap, lru

#### pheno-proc-queue

**Purpose**: Priority task queue with work stealing

```rust
// Key types
pub struct PriorityQueue<T>;
pub struct TaskScheduler;
pub struct WorkerPool;
pub enum Priority { High, Normal, Low }
```

**Dependencies**: pheno-proc-core, crossbeam-deque

#### pheno-proc-shm

**Purpose**: Safe shared memory abstractions

```rust
// Key types
pub struct SharedMemory;
pub struct SharedMutex;
pub struct SharedCondition;
pub struct MappedRegion;
```

**Dependencies**: nix, memmap2

#### pheno-proc-uds

**Purpose**: Unix domain socket utilities

```rust
// Key types
pub struct UnixListener;
pub struct UnixStream;
pub struct UnixDatagram;
pub struct Credentials;
pub struct FdPassingExt;
```

**Dependencies**: tokio (for async variants), nix

### Consequences

#### Positive

- Consumers depend only on needed functionality
- Clear API boundaries
- Parallel compilation
- Independent testing
- Potential for independent releases

#### Negative

- More Cargo.toml files to maintain
- Cross-crate changes require multiple edits
- Potential for version drift
- Workspace coordination complexity

#### Mitigations

- Single version policy for now (all at 0.1.0)
- Workspace-level dependency management
- CI checks for cross-crate consistency
- Documentation in SPEC.md

### Workspace Configuration

```toml
# Cargo.toml (workspace root)
[workspace]
members = [
    "crates/pheno-proc-core",
    "crates/pheno-proc-dedup",
    "crates/pheno-proc-queue",
    "crates/pheno-proc-shm",
    "crates/pheno-proc-uds",
]
resolver = "2"

[workspace.package]
version = "0.1.0"
edition = "2021"
license = "MIT"
repository = "https://github.com/KooshaPari/PhenoProc"

[workspace.dependencies]
tokio = { version = "1.35", features = ["full"] }
tracing = "0.1"
thiserror = "1.0"
dashmap = "5.5"
```

### Re-export Pattern

For convenience, provide a meta-crate that re-exports all:

```toml
# crates/pheno-proc/Cargo.toml
[package]
name = "pheno-proc"

[features]
default = ["core", "dedup", "queue", "shm", "uds"]
core = ["pheno-proc-core"]
dedup = ["pheno-proc-dedup"]
queue = ["pheno-proc-queue"]
shm = ["pheno-proc-shm"]
uds = ["pheno-proc-uds"]
```

## Related Decisions

- ADR-001: Async-first architecture applies to all crates
- ADR-002: Deduplication logic belongs in its own crate
- SOTA.md: Crate organization enables flexible IPC usage

## References

- [Cargo Workspaces](https://doc.rust-lang.org/cargo/reference/workspaces.html)
- [Rust API Guidelines - Crate Organization](https://rust-lang.github.io/api-guidelines/)

---

**Date**: 2026-04-04
**Author**: PhenoProc Team
