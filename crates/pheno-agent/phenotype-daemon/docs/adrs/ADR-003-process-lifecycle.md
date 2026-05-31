# ADR-003: Process Lifecycle Model

## Status
**Accepted**

## Context

phenotype-daemon is designed as a "sidecar" daemon that provides skill management services to language-agnostic clients. Unlike system-level daemons (systemd, launchd) that require explicit installation and registration, phenotype-daemon follows a model inspired by modern development tools and container patterns.

The key question: How should the daemon lifecycle be managed in different deployment scenarios?

### Deployment Scenarios

1. **Development:** Developer runs daemon locally, expects automatic management
2. **CI/CD:** Ephemeral instances for testing
3. **Container:** Docker/Kubernetes with health checks
4. **System Service:** Traditional daemon managed by systemd/launchd
5. **IDE Extension:** VS Code, JetBrains plugin context

### Existing Patterns

| System | Lifecycle Model | Auto-Spawn | Parent Monitoring |
|--------|----------------|------------|-------------------|
| Docker daemon | System service + socket group | No | No |
| Language servers | Editor spawns | Yes | Yes |
| Build daemons (Bazel) | First build spawns | Yes | Idle timeout |
| sccache | User spawns | Optional | No |
| supervisord | Manual start | No | Yes (restart) |

## Decision

We will implement an **auto-spawn with parent monitoring** lifecycle model as the primary mode, with support for manual daemon management as a secondary option.

### Core Principles

1. **Zero Configuration:** Daemon starts automatically when first client connects
2. **Self-Healing:** Daemon exits when parent process terminates (no orphans)
3. **Transparent:** Clients work whether daemon is running or not
4. **Resource Conscious:** Minimal idle resource consumption

### Implementation

```rust
#[derive(Parser)]
struct Args {
    /// Enable auto-spawn mode with parent monitoring
    #[arg(long)]
    auto_spawn: bool,
    
    /// Parent PID to monitor (auto-spawn mode)
    #[arg(long)]
    parent_pid: Option<u32>,
    
    /// Idle timeout in seconds (0 = no timeout)
    #[arg(long, default_value = "0")]
    idle_timeout: u64,
}

/// Monitor parent and shutdown when it exits
async fn monitor_parent(parent_pid: u32) {
    let mut system = System::new_all();
    
    loop {
        sleep(Duration::from_secs(5)).await;
        system.refresh_all();
        
        if system.process(Pid::from(parent_pid as usize)).is_none() {
            info!("Parent process {} exited, shutting down", parent_pid);
            graceful_shutdown().await;
            std::process::exit(0);
        }
    }
}
```

### Auto-Spawn Flow

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Client     │      │   Socket     │      │   Daemon     │
│   Connect    │─────►│   Exists?    │      │   Process    │
└──────────────┘      └──────┬───────┘      └──────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
                    ▼ Yes             ▼ No
            ┌──────────────┐   ┌──────────────┐
            │  Connect     │   │  Spawn       │
            │  Normally    │   │  Daemon      │
            └──────────────┘   └──────┬───────┘
                                      │
                                      ▼
                             ┌──────────────┐
                             │  Wait for   │
                             │  Socket     │
                             │  (5s max)   │
                             └──────┬──────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼ Success                       ▼ Timeout
            ┌──────────────┐                 ┌──────────────┐
            │  Connect     │                 │  Error       │
            │  & Proceed   │                 │  Daemon Dead │
            └──────────────┘                 └──────────────┘
```

## Consequences

### Positive

1. **Developer Experience:** No manual daemon management required
2. **No Orphans:** Automatic cleanup prevents resource leaks
3. **Container Friendly:** Works without init system
4. **IDE Integration:** Natural fit for editor extension model
5. **Testing Simplicity:** Each test can have isolated daemon instance

### Negative

1. **Startup Latency:** First request includes daemon spawn time (~100-500ms)
2. **Race Conditions:** Multiple simultaneous clients might spawn multiple daemons
3. **Debugging Complexity:** Transient daemon processes harder to attach debugger
4. **Monitoring:** Traditional process monitoring tools see churn

### Mitigations

| Issue | Mitigation |
|-------|------------|
| Startup latency | Pre-warming in CI; keep-alive pings in dev |
| Race conditions | File-based locking during spawn |
| Debugging | `PHENOTYPE_DEBUG=1` keeps daemon alive after parent exit |
| Monitoring | Structured logging; metrics endpoint |

## Alternatives Considered

### Alternative 1: System Service Only

**Decision:** Rejected

**Rationale:** Requiring explicit installation as a system service creates friction for:
- CI/CD pipelines (would need privileged setup)
- Development environments (per-developer configuration)
- Container deployments (would need init system)

While system service mode is supported, it should not be the primary or required mode.

**Implementation:** Still available via:
```bash
# systemd
systemctl --user enable phenotype-daemon

# launchd
launchctl bootstrap gui/$UID ~/Library/LaunchAgents/phenotype.plist
```

### Alternative 2: Daemon Per Client Process

**Decision:** Rejected

**Rationale:** Spawning a new daemon for every client process would:
- Defeat the purpose of shared skill registry
- Increase memory overhead (each daemon loads registry)
- Complicate skill state management

**Alternative Accepted:** Single daemon with parent monitoring (not daemon per client).

### Alternative 3: Idle Timeout

**Decision:** Partially Accepted

**Rationale:** Idle timeout (terminate after N seconds of no activity) is a common pattern (used by sccache, Bazel). However:
- Timeout adds complexity (race conditions on restart)
- Modern systems have abundant RAM; daemon overhead (~10MB) negligible
- Predictability preferred over marginal resource savings

**Decision:** Idle timeout is optional (`--idle-timeout`), disabled by default.

### Alternative 4: Client-Initiated Heartbeat

**Decision:** Rejected

**Rationale:** Requiring clients to send periodic heartbeats:
- Complicates client implementations
- Failure to heartbeat causes unexpected daemon termination
- TCP keepalive achieves similar without application complexity

**Alternative:** Parent PID monitoring + optional idle timeout.

### Alternative 5: systemd Socket Activation

**Decision:** Supported but not primary

**Rationale:** systemd socket activation is elegant for Linux systems with systemd. However:
- Not portable (macOS, Windows, containers)
- Requires systemd configuration
- More complex than auto-spawn for development use

**Implementation:** Socket activation supported for system deployments:
```ini
# /etc/systemd/user/phenotype-daemon.socket
[Socket]
ListenStream=%t/phenotype.sock

[Install]
WantedBy=sockets.target
```

## Implementation Details

### Client-Side Auto-Spawn

#### TypeScript

```typescript
private async ensureDaemon(): Promise<void> {
    // Check if daemon is responsive
    if (fs.existsSync(this.socketPath)) {
        try {
            await this.testConnection();
            return;
        } catch {
            // Stale socket, remove it
            fs.unlinkSync(this.socketPath);
        }
    }
    
    // Find daemon binary
    const daemonPath = this.findDaemonBinary();
    
    // Spawn with auto-spawn flag
    const parentPid = process.pid;
    this.daemonProcess = spawn(
        daemonPath,
        ['--auto-spawn', '--parent-pid', parentPid.toString()],
        { detached: true, stdio: 'ignore' }
    );
    this.daemonProcess.unref();
    
    // Wait for socket creation (up to 5 seconds)
    for (let i = 0; i < 50; i++) {
        await sleep(100);
        if (fs.existsSync(this.socketPath)) {
            return;
        }
    }
    
    throw new Error('Daemon failed to start');
}
```

#### Python

```python
def _ensure_daemon(self) -> None:
    """Ensure daemon is running, auto-spawn if needed"""
    if os.path.exists(self.socket_path):
        try:
            self.ping()
            return
        except Exception:
            os.unlink(self.socket_path)
    
    # Spawn daemon
    daemon_path = self._find_daemon()
    parent_pid = os.getpid()
    
    self._daemon_proc = subprocess.Popen(
        [daemon_path, '--auto-spawn', '--parent-pid', str(parent_pid)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    
    # Wait for socket
    for _ in range(50):
        time.sleep(0.1)
        if os.path.exists(self.socket_path):
            return
    
    raise RuntimeError("Daemon failed to start")
```

### Spawn Locking

To prevent race conditions when multiple clients spawn simultaneously:

```rust
use std::fs::OpenOptions;
use std::os::unix::fs::OpenOptionsExt;

/// Try to acquire spawn lock
fn acquire_spawn_lock(socket_path: &Path) -> Option<File> {
    let lock_path = socket_path.with_extension("spawn-lock");
    
    match OpenOptions::new()
        .write(true)
        .create_new(true)  // Fails if exists
        .mode(0o600)
        .open(&lock_path)
    {
        Ok(file) => Some(file),
        Err(_) => None,  // Another process is spawning
    }
}

/// Release spawn lock
fn release_spawn_lock(socket_path: &Path) {
    let lock_path = socket_path.with_extension("spawn-lock");
    let _ = fs::remove_file(&lock_path);
}
```

### Parent Process Detection

Cross-platform parent PID detection:

```rust
#[cfg(unix)]
fn get_parent_pid() -> Option<u32> {
    use std::os::unix::process::parent_id;
    Some(parent_id())
}

#[cfg(windows)]
fn get_parent_pid() -> Option<u32> {
    use windows_sys::Win32::System::Threading::GetCurrentProcessId;
    use windows_sys::Win32::System::Threading::GetParentProcessId;
    
    unsafe {
        // Windows doesn't have direct parent PID API
        // Requires NtQueryInformationProcess
        // Simplified: use --parent-pid flag
        None
    }
}
```

### Graceful Shutdown

```rust
async fn graceful_shutdown() {
    info!("Initiating graceful shutdown");
    
    // 1. Stop accepting new connections
    // (Handled by dropping listener in main task)
    
    // 2. Wait for in-flight requests (with timeout)
    let deadline = Instant::now() + Duration::from_secs(30);
    while has_active_requests() {
        if Instant::now() > deadline {
            warn!("Shutdown timeout exceeded, forcing exit");
            break;
        }
        sleep(Duration::from_millis(100)).await;
    }
    
    // 3. Cleanup socket file
    cleanup_socket().await;
    
    // 4. Flush logs
    tracing::dispatcher::get_default(|dispatcher| {
        dispatcher.flush();
    });
    
    info!("Graceful shutdown complete");
}
```

## Lifecycle States

```
                    ┌─────────┐
                    │  Init   │
                    └────┬────┘
                         │ Parse args
                         ▼
                    ┌─────────┐
         ┌─────────│ Standby │─────────┐
         │         │ (auto)  │         │
         │         └────┬────┘         │
         │              │             │
         │ System mode  │ Auto mode   │ Container
         ▼              ▼             ▼
    ┌─────────┐   ┌─────────┐   ┌─────────┐
    │ System  │   │ Monitor │   │ Health  │
    │ Service │   │ Parent  │   │ Checks  │
    └────┬────┘   └────┬────┘   └────┬────┘
         │              │             │
         │              │ Parent exit │ Kill signal
         ▼              ▼             ▼
    ┌─────────────────────────────────────┐
    │           Shutdown                 │
    │  - Drain connections               │
    │  - Cleanup resources               │
    │  - Exit 0                          │
    └─────────────────────────────────────┘
```

## Deployment Patterns

### Development (Auto-Spawn)

```typescript
// Client automatically spawns daemon
const client = await createPooledClient();
await client.registerSkill(manifest);
// ... work ...
// Daemon exits when parent process exits
```

### CI/CD (Explicit)

```yaml
# .github/workflows/test.yml
- name: Start phenotype-daemon
  run: |
    phenotype-daemon --socket /tmp/phenotype-ci.sock &
    sleep 1  # Wait for startup
    
- name: Run tests
  run: cargo test
  env:
    PHENOTYPE_SOCKET: /tmp/phenotype-ci.sock
    
- name: Stop daemon
  run: kill %1  # Kill background job
```

### Container

```dockerfile
# Dockerfile
FROM rust:1.75 as builder
COPY . .
RUN cargo build --release

FROM debian:bookworm-slim
COPY --from=builder /target/release/phenotype-daemon /usr/local/bin/

# Health check
HEALTHCHECK --interval=30s --timeout=3s \
  CMD phenotype-ctl ping || exit 1

EXPOSE 9753
CMD ["phenotype-daemon", "--port", "9753"]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: phenotype-daemon
spec:
  template:
    spec:
      containers:
      - name: daemon
        image: phenotype-daemon:latest
        ports:
        - containerPort: 9753
        livenessProbe:
          exec:
            command: ["/usr/local/bin/phenotype-ctl", "ping"]
          initialDelaySeconds: 10
          periodSeconds: 5
        readinessProbe:
          exec:
            command: ["/usr/local/bin/phenotype-ctl", "version"]
          initialDelaySeconds: 5
          periodSeconds: 5
```

### System Service (systemd)

```ini
# ~/.config/systemd/user/phenotype-daemon.service
[Unit]
Description=Phenotype Daemon
After=network.target

[Service]
Type=simple
ExecStart=%h/.cargo/bin/phenotype-daemon
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

## Related Decisions

- ADR-001: Transport Protocol Selection
- ADR-002: Serialization Format
- [DAEMON_SYSTEMS_SOTA.md](../research/DAEMON_SYSTEMS_SOTA.md) - Lifecycle comparison

## References

1. [The Twelve-Factor App](https://12factor.net/) - Process model
2. [Docker Container Lifecycle](https://docs.docker.com/config/containers/start-containers-automatically/)
3. [Kubernetes Container Lifecycle](https://kubernetes.io/docs/concepts/containers/container-lifecycle-hooks/)
4. [systemd.service](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
5. [launchd.plist](https://developer.apple.com/library/archive/documentation/Darwin/Reference/ManPages/man5/launchd.plist.5.html)

---

**Decision Date:** 2026-04-04  
**Decision Maker:** Phenotype Architecture Team  
**Last Updated:** 2026-04-04
