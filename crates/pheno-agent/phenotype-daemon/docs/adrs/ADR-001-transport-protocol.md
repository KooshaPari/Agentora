# ADR-001: Transport Protocol Selection

## Status
**Accepted**

## Context

The phenotype-daemon requires a transport mechanism for client-daemon communication. As a high-performance sidecar daemon for skill management, the transport choice significantly impacts:
- Latency for skill registry operations
- Throughput for concurrent skill resolution
- Cross-platform compatibility
- Deployment complexity
- Security model

We evaluated multiple transport options based on requirements from the phenotype ecosystem and lessons from existing daemon systems (as documented in DAEMON_SYSTEMS_SOTA.md).

### Requirements

1. **Performance:** Sub-millisecond latency for local communication
2. **Concurrency:** Support 100+ concurrent client connections
3. **Cross-Platform:** Linux, macOS, Windows support
4. **Deployment Simplicity:** Work in containers, VMs, and bare metal
5. **Security:** Process-level access control
6. **Auto-Spawn:** Work without system service manager registration

## Decision

We will use **Unix Domain Sockets as the primary transport**, with **TCP as the cross-platform fallback**, and **NATS for cluster mode**.

### Implementation

```rust
// Default: Unix domain socket (Linux/macOS)
#[cfg(unix)]
UnixListener::bind(socket_path)

// Fallback: TCP (all platforms)
TcpListener::bind("127.0.0.1:port")

// Cluster: NATS (optional feature)
#[cfg(feature = "nats-cluster")]
async_nats::connect(nats_url)
```

### Wire Protocol

All transports use the same wire protocol:
- 4-byte big-endian length prefix
- MessagePack-encoded payload

```
┌─────────────────┬─────────────────────────────────────┐
│ Length (4 bytes)│ MessagePack Payload (N bytes)       │
│   (big-endian)  │                                     │
└─────────────────┴─────────────────────────────────────┘
```

## Consequences

### Positive

1. **Performance:** Unix sockets achieve ~50μs latency vs ~100μs for TCP localhost
2. **Simplicity:** Single code path for Unix/TCP (both implement `AsyncRead`/`AsyncWrite`)
3. **Flexibility:** Users choose transport via CLI flags/environment
4. **Future-Proof:** NATS integration enables horizontal scaling
5. **Security:** Unix socket permissions provide fine-grained access control

### Negative

1. **Platform Complexity:** Three transport implementations to maintain
2. **Windows Limitations:** No Unix socket support requires TCP fallback always
3. **Configuration Overhead:** Users must choose appropriate transport
4. **Testing Surface:** Need test coverage for all three transports

### Neutral

1. **Abstract Sockets:** Linux abstract namespace avoids filesystem cleanup issues
2. **Buffer Sizes:** Separate tuning for each transport type
3. **Connection Pooling:** Client shims implement transport-specific pooling

## Alternatives Considered

### Alternative 1: TCP Only

**Decision:** Rejected

**Rationale:** While TCP provides universal compatibility, it introduces unnecessary overhead for local communication. Systemd, launchd, and other modern daemon systems explicitly prefer Unix sockets for local IPC. TCP also complicates security (firewall rules vs file permissions).

**Impact:** Would simplify implementation but sacrifice 2x performance for primary use case.

### Alternative 2: Named Pipes (Windows) + Unix Sockets

**Decision:** Rejected

**Rationale:** Windows named pipes provide semantic similarity to Unix sockets, but introduce platform-specific code paths that complicate testing and maintenance. TCP fallback is simpler and performs adequately for Windows use cases.

**Impact:** Would improve Windows performance but increase code complexity significantly.

### Alternative 3: gRPC

**Decision:** Rejected

**Rationale:** gRPC adds substantial dependencies and complexity. While it provides streaming and code generation, phenotype-daemon's requirements are simpler (request/response RPC). The additional HTTP/2 overhead is unnecessary.

**Impact:** Would increase binary size by ~5MB and add protobuf complexity.

### Alternative 4: Raw Binary Protocol (Custom)

**Decision:** Rejected

**Rationale:** A custom binary protocol would eliminate MessagePack overhead but require implementing serialization/deserialization logic for each language binding (TypeScript, Python, C#, etc.). MessagePack provides good performance with existing library support.

**Impact:** Would improve performance marginally but significantly increase maintenance burden.

## Lessons from Reference Systems

### systemd
systemd pioneered socket activation over Unix sockets. Their implementation demonstrates:
- Unix sockets can be passed to services via file descriptor passing
- Socket activation enables parallel service startup
- File permissions provide security without authentication complexity

### launchd
launchd uses Unix sockets and Mach ports, with socket passing via `launch_activate_socket()`. Key lessons:
- Socket handoff adds minimal latency (<1ms)
- Service directories enforce ownership
- Abstract sockets (Linux) avoid stale socket issues

### Windows SCM
Windows lacks native Unix socket support (until WSL). Their approach:
- Named pipes offer similar semantics (but different API)
- TCP is common fallback
- Local RPC uses ALPC (advanced local procedure call)

## Implementation Notes

### Unix Socket Path Resolution

```rust
fn default_socket_path() -> PathBuf {
    // Priority: PHENOTYPE_SOCKET > XDG_RUNTIME_DIR > /tmp
    env::var("PHENOTYPE_SOCKET")
        .map(PathBuf::from)
        .or_else(|| {
            env::var("XDG_RUNTIME_DIR")
                .map(|dir| PathBuf::from(dir).join("phenotype.sock"))
        })
        .unwrap_or_else(|| {
            PathBuf::from("/tmp/phenotype.sock")
        })
}
```

### Permission Model

```rust
// Unix socket permissions
#[cfg(unix)]
async fn bind_with_permissions(path: &Path) -> Result<UnixListener> {
    // Bind first
    let listener = UnixListener::bind(path)?;
    
    // Set restrictive permissions
    let mut perms = fs::metadata(path).await?.permissions();
    perms.set_mode(0o600); // User read/write only
    fs::set_permissions(path, perms).await?;
    
    Ok(listener)
}
```

### TCP Security

```rust
// TCP only binds to localhost by default
// This prevents remote access without explicit configuration
const DEFAULT_TCP_BIND: &str = "127.0.0.1:9753";

// Port selection: 9753 (arbitrary, unregistered)
// Future: Register with IANA if protocol becomes public
```

### NATS Clustering

```rust
#[cfg(feature = "nats-cluster")]
pub async fn run_nats_cluster(
    url: String,
    instance: String,
    state: SharedState
) -> Result<()> {
    let client = async_nats::connect(url).await?;
    let jetstream = async_nats::jetstream::new(client);
    
    // Create stream for skill registry updates
    let stream = jetstream
        .create_stream(async_nats::jetstream::stream::Config {
            name: "PHENOTYPE_SKILLS".to_string(),
            subjects: vec!["phenotype.skills.*".to_string()],
            ..Default::default()
        })
        .await?;
    
    // Subscribe to requests
    let consumer = jetstream
        .create_consumer_on_stream(
            async_nats::jetstream::consumer::pull::Config {
                name: Some(format!("daemon-{}", instance)),
                ..Default::default()
            },
            stream,
        )
        .await?;
    
    // Process messages...
}
```

## Related Decisions

- ADR-002: Serialization Format (MessagePack)
- ADR-003: Process Lifecycle Model

## References

1. [DAEMON_SYSTEMS_SOTA.md](../research/DAEMON_SYSTEMS_SOTA.md) - Transport analysis
2. [SPEC.md](../../SPEC.md) - Transport implementation details
3. [The Unix Philosophy in 2024](https://example.com) - IPC best practices

---

**Decision Date:** 2026-04-04  
**Decision Maker:** Phenotype Architecture Team  
**Last Updated:** 2026-04-04
