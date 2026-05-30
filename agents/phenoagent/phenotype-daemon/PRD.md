# Phenotype Daemon Product Requirements Document

**Document ID:** PHENOTYPE_DAEMON_PRD_001  
**Version:** 1.0.0  
**Status:** Approved  
**Last Updated:** 2026-04-05  
**Author:** Phenotype Product Team  
**Stakeholders:** Platform Engineering, AI Engineering, Developer Experience, IDE Developers

---

## 1. Executive Summary

### 1.1 Product Vision

The Phenotype Daemon (phenotype-daemon) is a high-performance sidecar daemon providing language-agnostic access to the Phenotype Skills Registry. By operating as a persistent background service with optimized IPC mechanisms, it achieves 10-100x better performance than stdio-based MCP interfaces while maintaining cross-language compatibility.

### 1.2 Mission Statement

To provide the fastest, most reliable, and most developer-friendly way for applications to interact with the Phenotype Skills ecosystem, enabling seamless skill registration, resolution, and dependency management across all programming languages.

### 1.3 Key Value Propositions

| Value Proposition | Description | Business Impact |
|-------------------|-------------|-----------------|
| **10-100x Performance** | IPC vs stdio | Instant skill operations |
| **Language Agnostic** | TypeScript, Python, C#, Rust clients | Team flexibility |
| **Persistent Registry** | In-memory skill storage | Fast lookups |
| **Auto-Spawn** | Automatic daemon startup | Zero configuration |
| **Dependency Resolution** | Topological sort, cycle detection | Reliable skill management |
| **Type-Safe Protocol** | MessagePack RPC | Reliable communication |

### 1.4 Positioning Statement

For developers building AI-powered tools and IDE extensions, the Phenotype Daemon is the high-performance sidecar that provides persistent skill registry access with 10-100x better performance than stdio-based MCP, unlike stateless process-per-request approaches.

---

## 2. Problem Statement

### 2.1 Current Pain Points

#### 2.1.1 Stdio Performance Limitations

MCP over stdio has high latency for frequent operations:
- **Process startup cost**: 50-500ms per operation
- **Serialization overhead**: JSON parsing for every request
- **No connection reuse**: New process per request
- **Resource exhaustion**: High CPU/memory for frequent ops

#### 2.1.2 State Management Challenges

No shared state between operations:
- **Repeated initialization**: Skills reloaded every request
- **No caching**: Can't cache expensive computations
- **Disconnected operations**: Each request isolated
- **Limited context**: Can't maintain session state

#### 2.1.3 Language Fragmentation

Each language needs custom protocol implementation:
- **Duplicated effort**: Same protocol in N languages
- **Inconsistent behavior**: Subtle differences per SDK
- **Maintenance burden**: Updates required everywhere
- **Feature parity gaps**: Some SDKs lag behind

#### 2.1.4 Dependency Complexity

Manual dependency resolution is error-prone:
- **Circular dependencies**: Hard to detect manually
- **Version conflicts**: No automatic resolution
- **Transitive dependencies**: Easy to miss
- **Ordering issues**: Wrong initialization order

### 2.2 Use Cases

| Scenario | Solution | User |
|----------|----------|------|
| IDE integration | Fast skill lookup for completions | IDE Developer |
| Agent systems | Persistent skill registry | AI Platform Engineer |
| CI/CD pipelines | Automated skill validation | DevOps |
| Multi-language teams | Shared skill ecosystem | Team Lead |
| Complex dependencies | Automatic resolution | Tool Developer |
| High-frequency operations | Low-latency IPC | Performance Engineer |

### 2.3 Market Analysis

| Solution | Strengths | Weaknesses | Our Differentiation |
|----------|-----------|------------|---------------------|
| **MCP stdio** | Simple, universal | Slow, stateless | Persistent, fast |
| **LSP** | Editor standard | Complex, heavy | Lightweight |
| **gRPC** | Fast, typed | Heavy dependencies | Minimal deps |
| **HTTP API** | Universal | Network overhead | Local IPC |
| **Custom IPC** | Fast | Platform-specific | Cross-platform |

---

## 3. Target Users and Personas

### 3.1 Primary Personas

#### 3.1.1 IDE Developer Ivan

**Demographics**: IDE extension developer, 3-7 years experience
**Goals**:
- Build fast IDE completions
- Support multiple languages
- Minimize latency
- Easy integration

**Pain Points**:
- Slow completions hurt UX
- Managing multiple protocol implementations
- Complex setup for users
- Performance variability

**Technical Profile**:
- TypeScript/Python developer
- VS Code/Eclipse/JetBrains experience
- Performance-conscious
- Values clean APIs

**Quote**: "I need completions to be instant. Every millisecond matters for the user experience."

#### 3.1.2 AI Platform Engineer Alice

**Demographics**: AI infrastructure engineer, 5+ years experience
**Goals**:
- Run persistent agent services
- Achieve high throughput
- Maintain reliability
- Scale horizontally

**Pain Points**:
- Stateless services can't cache
- High latency for skill lookups
- Complex dependency management
- Resource overhead per request

**Technical Profile**:
- Distributed systems expert
- Kubernetes/Docker user
- Performance optimizer
- Reliability-focused

**Quote**: "Our agents need fast, reliable access to skills without the overhead of spawning processes."

#### 3.1.3 Language Tool Developer Tim

**Demographics**: Language tooling developer, 4+ years experience
**Goals**:
- Create language-specific tools
- Integrate with skill ecosystem
- Maintain performance
- Simplify integration

**Pain Points**:
- Different protocols for different tools
- Hard to test locally
- Complex setup requirements
- Platform differences

**Technical Profile**:
- Compiler/language server background
- Multiple language experience
- Tooling enthusiast
- Values simplicity

**Quote**: "I want to focus on my language tool, not on the communication protocol."

### 3.2 Secondary Personas

#### 3.2.1 DevOps Engineer Dave

- Manages deployment
- Needs monitoring/observability
- Configures infrastructure

#### 3.2.2 End Developer Erin

- Uses tools built on daemon
- Wants zero configuration
- Values reliability

### 3.3 User Segmentation

| Segment | Size | Primary Need |
|---------|------|--------------|
| IDE extension developers | 40% | Low latency |
| AI platform teams | 30% | Reliability, throughput |
| Language tool developers | 20% | Simplicity |
| DevOps/Platform | 10% | Operations |

---

## 4. Functional Requirements

### 4.1 Core Registry (FR-CR)

#### FR-CR-001: Skill Registration

**Requirement**: Register skills with metadata

**Priority**: P0 - Critical

**Description**: API for registering skills with their metadata, capabilities, and dependencies.

**Skill Manifest Schema**:
```json
{
  "manifest": {
    "name": "rust-analyzer",
    "version": "1.75.0",
    "description": "Rust language server integration",
    "capabilities": ["lsp", "completion", "diagnostics"],
    "dependencies": {
      "cargo": ">=1.70.0",
      "rustc": ">=1.75.0"
    },
    "metadata": {
      "author": "Phenotype Team",
      "license": "MIT",
      "repository": "https://github.com/..."
    },
    "config_schema": {
      "type": "object",
      "properties": {
        "target": { "type": "string" }
      }
    }
  }
}
```

**API Specification**:
```rust
// Daemon RPC method
fn skill_register(manifest: SkillManifest) -> Result<SkillId, RegistrationError>;

// Validation
fn validate_manifest(manifest: &SkillManifest) -> ValidationResult;
```

**Acceptance Criteria**:
1. [ ] Skill name validation (allowed characters, length)
2. [ ] Semver version parsing and validation
3. [ ] Capability registration (predefined + custom)
4. [ ] Duplicate detection (name:version)
5. [ ] Registration latency <1ms
6. [ ] Atomic registration (all or nothing)
7. [ ] Persist to disk (optional)

#### FR-CR-002: Skill Retrieval

**Requirement**: Get skill information by ID or query

**Priority**: P0 - Critical

**API Specification**:
```rust
// Get by ID
fn skill_get(id: SkillId) -> Result<SkillInfo, NotFoundError>;

// List all skills
fn skill_list(filter: Option<SkillFilter>) -> Vec<SkillInfo>;

// Search by name/pattern
fn skill_search(query: &str) -> Vec<SkillInfo>;

// Filter by capability
fn skill_by_capability(cap: Capability) -> Vec<SkillInfo>;
```

**Acceptance Criteria**:
1. [ ] Get by ID (name:version format)
2. [ ] List all skills with pagination
3. [ ] Filter by capability
4. [ ] Search by name (fuzzy matching)
5. [ ] Query latency <1ms for in-memory
6. [ ] Pagination support (limit/offset)

#### FR-CR-003: Dependency Resolution

**Requirement**: Resolve skill dependencies

**Priority**: P1 - High

**Description**: Automatic dependency resolution with topological sorting and cycle detection.

**API Specification**:
```rust
// Resolve dependencies
fn resolve_dependencies(skills: Vec<SkillId>) -> Result<ResolutionResult, ResolutionError>;

// Check for circular dependencies
fn check_circular(skills: Vec<SkillId>) -> Option<Vec<SkillId>>;

// Get dependency tree
fn dependency_tree(root: SkillId) -> DependencyTree;

// Resolution result
struct ResolutionResult {
    ordered: Vec<SkillId>,           // Topologically sorted
    missing: Vec<Dependency>,        // Unmet dependencies
    conflicts: Vec<VersionConflict>, // Version conflicts
}
```

**Acceptance Criteria**:
1. [ ] Transitive dependency collection
2. [ ] Topological sort for initialization order
3. [ ] Circular dependency detection
4. [ ] Version constraint checking (semver)
5. [ ] Resolution latency <10ms for 100 skills
6. [ ] Clear error messages for conflicts
7. [ ] Multiple version support

**Example Resolution**:
```
Input: [A, B]
A depends on: C, D
B depends on: C, E
C depends on: F

Output order: F, C, D, E, A, B
(or: F, C, E, D, B, A)
```

#### FR-CR-004: Skill Unregistration

**Requirement**: Remove skills from registry

**Priority**: P1 - High

**API Specification**:
```rust
fn skill_unregister(id: SkillId) -> Result<(), NotFoundError>;

// Check if skill has dependents
fn has_dependents(id: SkillId) -> Vec<SkillId>;

// Force unregister (breaks dependents)
fn skill_unregister_force(id: SkillId) -> Result<(), Error>;
```

**Acceptance Criteria**:
1. [ ] Remove skill by ID
2. [ ] Check for dependent skills
3. [ ] Optional force removal
4. [ ] Cleanup of associated resources

### 4.2 Transport Layer (FR-TL)

#### FR-TL-001: Unix Domain Socket

**Requirement**: Unix domain socket transport

**Priority**: P0 - Critical

**Description**: Unix socket transport for maximum performance on Unix-like systems.

**Acceptance Criteria**:
1. [ ] Unix socket creation at configurable path
2. [ ] Path resolution priority:
   - $PHENOTYPE_SOCKET environment variable
   - $XDG_RUNTIME_DIR/phenotype/daemon.sock
   - /tmp/phenotype-$UID/daemon.sock
3. [ ] Permission management (0o600 - user only)
4. [ ] Abstract namespace support (Linux)
5. [ ] Cleanup on shutdown
6. [ ] Conflict detection (socket already exists)

#### FR-TL-002: TCP Transport

**Requirement**: TCP transport for cross-platform

**Priority**: P0 - Critical

**Description**: TCP transport for Windows and when Unix sockets aren't available.

**Acceptance Criteria**:
1. [ ] TCP server implementation (async)
2. [ ] Default port 9753 (PHEN on phone keypad)
3. [ ] Localhost-only binding (127.0.0.1)
4. [ ] Connection management (max connections)
5. [ ] Keepalive support
6. [ ] Graceful shutdown

#### FR-TL-003: Named Pipes (Windows)

**Requirement**: Windows named pipes support

**Priority**: P2 - Medium

**Description**: Named pipe transport for Windows-native performance.

**Acceptance Criteria**:
1. [ ] Named pipe server
2. [ ] Pipe name: \\.\pipe\phenotype-daemon
3. [ ] Security descriptor configuration
4. [ ] Performance comparable to Unix sockets

#### FR-TL-004: Transport Selection

**Requirement**: Automatic transport selection

**Priority**: P1 - High

**Selection Priority**:
1. Unix socket (if available)
2. Named pipes (Windows)
3. TCP (fallback)

**Acceptance Criteria**:
1. [ ] Automatic selection based on platform
2. [ ] Override via configuration
3. [ ] Connection testing before selection
4. [ ] Clear logging of transport choice

### 4.3 Protocol (FR-PR)

#### FR-PR-001: Message Framing

**Requirement**: Length-prefixed message framing

**Priority**: P0 - Critical

**Description**: Binary protocol with length-prefixed frames for reliable message boundaries.

**Frame Format**:
```
┌─────────────────┬─────────────────┬──────────────┐
│  Length (4 bytes)  │  MessagePack Payload  │  CRC32 (opt) │
│   (big-endian)     │         (N bytes)       │   (4 bytes)  │
└─────────────────┴─────────────────┴──────────────┘
```

**Acceptance Criteria**:
1. [ ] 4-byte length prefix (big-endian uint32)
2. [ ] MessagePack serialization
3. [ ] Maximum message size: 16MB
4. [ ] Size limit enforcement
5. [ ] Error handling for oversized messages

#### FR-PR-002: RPC Protocol

**Requirement**: Request-response RPC

**Priority**: P0 - Critical

**Description**: JSON-RPC 2.0 inspired protocol over MessagePack.

**Request Format**:
```json
{
  "id": 123,
  "method": "skill.register",
  "params": { ... }
}
```

**Response Format**:
```json
{
  "id": 123,
  "result": { ... },
  "error": null
}
```

**Error Format**:
```json
{
  "id": 123,
  "result": null,
  "error": {
    "code": -32600,
    "message": "Invalid request",
    "data": { ... }
  }
}
```

**Standard Error Codes**:

| Code | Meaning |
|------|---------|
| -32700 | Parse error |
| -32600 | Invalid request |
| -32601 | Method not found |
| -32602 | Invalid params |
| -32603 | Internal error |
| -32000 to -32099 | Server error |

**Acceptance Criteria**:
1. [ ] Request ID correlation
2. [ ] Method routing
3. [ ] Error code standardization
4. [ ] Request timeout handling
5. [ ] Protocol version negotiation

#### FR-PR-003: RPC Methods

**Requirement**: Standard RPC method set

**Priority**: P0 - Critical

**Core Methods**:

| Method | Description | Params | Result |
|--------|-------------|--------|--------|
| `ping` | Health check | - | `{"pong": true}` |
| `version` | Daemon info | - | `{"version": "1.0.0", "pid": 1234}` |
| `skill.register` | Register skill | `manifest` | `skill_id` |
| `skill.get` | Get skill | `skill_id` | `skill_info` |
| `skill.list` | List skills | `filter?` | `skill_info[]` |
| `skill.unregister` | Remove skill | `skill_id` | `success` |
| `resolve` | Resolve dependencies | `skill_ids[]` | `resolution_result` |
| `check_circular` | Check cycles | `skill_ids[]` | `cycle?` |

**Acceptance Criteria**:
1. [ ] All methods implemented
2. [ ] Proper error codes
3. [ ] Request/response correlation
4. [ ] Protocol versioning

### 4.4 Client SDKs (FR-SD)

#### FR-SD-001: TypeScript Client

**Requirement**: TypeScript/Node.js client with pooling

**Priority**: P1 - High

**API Specification**:
```typescript
class PhenotypeClient {
  constructor(options?: ClientOptions);
  
  // Auto-spawn daemon if not running
  static async create(options?: ClientOptions): Promise<PhenotypeClient>;
  
  // Core methods
  async skillRegister(manifest: SkillManifest): Promise<SkillId>;
  async skillGet(id: SkillId): Promise<SkillInfo>;
  async skillList(filter?: SkillFilter): Promise<SkillInfo[]>;
  async resolveDependencies(skills: SkillId[]): Promise<ResolutionResult>;
  
  // Lifecycle
  async ping(): Promise<boolean>;
  async close(): Promise<void>;
}
```

**Acceptance Criteria**:
1. [ ] Connection pooling
2. [ ] Auto-spawn daemon
3. [ ] Promise-based API
4. [ ] TypeScript definitions
5. [ ] Error handling with specific error types
6. [ ] EventEmitter for connection events

#### FR-SD-002: Python Client

**Requirement**: Python client with context manager

**Priority**: P1 - High

**API Specification**:
```python
from phenotype_daemon import PhenotypeClient, SkillManifest

# Context manager for auto-cleanup
async with PhenotypeClient() as client:
    skill_id = await client.skill_register(manifest)
    info = await client.skill_get(skill_id)

# Or manual management
client = PhenotypeClient()
await client.connect()  # Auto-spawns daemon
# ... use client ...
await client.close()
```

**Acceptance Criteria**:
1. [ ] Context manager support (`async with`)
2. [ ] Auto-spawn daemon
3. [ ] Async/await API
4. [ ] Type hints (Python 3.9+)
5. [ ] Exception hierarchy
6. [ ] Connection pooling

#### FR-SD-003: C# Client

**Requirement**: C#/.NET client

**Priority**: P2 - Medium

**Acceptance Criteria**:
1. [ ] Async/await support
2. [ ] IDisposable pattern
3. [ ] Auto-spawn daemon
4. [ ] Strongly-typed API
5. [ ] NuGet package

#### FR-SD-004: Rust Client

**Requirement**: Rust client

**Priority**: P2 - Medium

**Acceptance Criteria**:
1. [ ] Async support (tokio)
2. [ ] Drop trait for cleanup
3. [ ] Auto-spawn daemon
4. [ ] Type-safe API
5. [ ] crates.io package

### 4.5 Daemon Management (FR-DM)

#### FR-DM-001: Auto-Spawn

**Requirement**: Automatic daemon startup

**Priority**: P1 - High

**Description**: Clients automatically start the daemon if not running.

**Spawn Logic**:
1. Check if daemon is running (ping)
2. If not, spawn daemon process
3. Wait for daemon to be ready
4. Connect via transport

**Acceptance Criteria**:
1. [ ] Detect running daemon
2. [ ] Spawn daemon process
3. [ ] Wait for startup (timeout 5s)
4. [ ] Handle spawn failures
5. [ ] Log spawn events
6. [ ] PID tracking

#### FR-DM-002: Lifecycle Management

**Requirement**: Graceful startup and shutdown

**Priority**: P1 - High

**Acceptance Criteria**:
1. [ ] Signal handling (SIGTERM, SIGINT)
2. [ ] Graceful shutdown (finish in-flight requests)
3. [ ] Cleanup resources (sockets, temp files)
4. [ ] Exit code handling
5. [ ] Startup/shutdown hooks

#### FR-DM-003: Health Checks

**Requirement**: Daemon health monitoring

**Priority**: P2 - Medium

**Acceptance Criteria**:
1. [ ] Built-in ping endpoint
2. [ ] Health metrics (memory, goroutines)
3. [ ] Readiness probe
4. [ ] Liveness probe

---

## 5. Non-Functional Requirements

### 5.1 Performance

#### 5.1.1 Response Time Targets

| Operation | Target | Measurement |
|-----------|--------|-------------|
| Skill lookup | <1ms p99 | Benchmark |
| Skill registration | <1ms p99 | Benchmark |
| Dependency resolution (100 skills) | <10ms p99 | Benchmark |
| Client connection | <50ms | Benchmark |
| Throughput | 10,000 req/sec | Load test |

#### 5.1.2 Resource Usage

| Resource | Target |
|----------|--------|
| Memory (baseline) | <50MB |
| Memory (1000 skills) | <100MB |
| CPU (idle) | <1% |
| CPU (1000 req/sec) | <10% |
| Disk (if persisting) | <10MB |

### 5.2 Reliability

#### 5.2.1 Availability

- Daemon uptime: 99.9%
- Automatic restart on crash (client-initiated)
- No data loss on graceful shutdown
- Recovery time <5s

#### 5.2.2 Connection Recovery

- Automatic reconnection
- Request retry with backoff
- Connection pooling
- Graceful degradation

### 5.3 Security

#### 5.3.1 Transport Security

- Unix socket permissions 0o600
- TCP localhost-only
- No authentication on local socket (trusted)
- Optional TLS for remote (future)

#### 5.3.2 Input Validation

- Schema validation for all inputs
- Size limits on all inputs
- Sanitization of paths/names
- Rate limiting (future)

---

## 6. User Stories

### 6.1 Primary User Stories

#### US-001: Skill Registration

**As a** tool developer  
**I want** to register my tool with the daemon  
**So that** other tools can discover and use it

**Acceptance Criteria**:
- Given a skill manifest
- When I call skill.register
- Then the skill is stored in registry
- And I receive the skill ID
- With validation of manifest

**Priority**: P0

#### US-002: Dependency Resolution

**As an** IDE developer  
**I want** to resolve skill dependencies  
**So that** I can load all required tools

**Acceptance Criteria**:
- Given a set of skill IDs
- When I call resolve
- Then I get topologically sorted list
- With all transitive dependencies
- And any conflicts reported

**Priority**: P0

#### US-003: Client Auto-Spawn

**As a** Python developer  
**I want** automatic daemon startup  
**So that** I don't need to manage the daemon

**Acceptance Criteria**:
- Given client creation
- When daemon is not running
- Then client spawns it automatically
- And connects successfully
- Within 5 seconds

**Priority**: P1

#### US-004: Fast Skill Lookup

**As an** IDE developer  
**I want** instant skill lookups  
**So that** completions feel responsive

**Acceptance Criteria**:
- Given a running daemon
- When I lookup a skill
- Then response time is <1ms
- For 1000+ registered skills

**Priority**: P0

### 6.2 Secondary User Stories

#### US-005: Cross-Platform Support

**As a** Windows developer  
**I want** the daemon on Windows  
**So that** I can use the same tools

**Priority**: P2

#### US-006: Persistence

**As a** platform engineer  
**I want** skills to persist across restarts  
**So that** I don't re-register everything

**Priority**: P2

---

## 7. Feature Specifications

### 7.1 Skill Manifest Schema

```json
{
  "$schema": "http://phenotype.io/schemas/skill-manifest-v1.json",
  "type": "object",
  "required": ["name", "version"],
  "properties": {
    "name": {
      "type": "string",
      "pattern": "^[a-z0-9-]+$",
      "maxLength": 64
    },
    "version": {
      "type": "string",
      "format": "semver"
    },
    "description": {
      "type": "string",
      "maxLength": 256
    },
    "capabilities": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": [
          "lsp",
          "completion",
          "diagnostics",
          "formatting",
          "code-action",
          "hover",
          "signature-help",
          "custom"
        ]
      }
    },
    "dependencies": {
      "type": "object",
      "additionalProperties": {
        "type": "string",
        "description": "Semver constraint"
      }
    },
    "metadata": {
      "type": "object"
    }
  }
}
```

### 7.2 Dependency Resolution Algorithm

```rust
fn resolve_dependencies(skills: Vec<SkillId>) -> Result<ResolutionResult> {
    // 1. Collect all transitive dependencies
    let all_deps = collect_transitive(skills)?;
    
    // 2. Check for version conflicts
    let conflicts = check_version_conflicts(&all_deps)?;
    if !conflicts.is_empty() {
        return Err(ResolutionError::Conflicts(conflicts));
    }
    
    // 3. Detect circular dependencies
    if let Some(cycle) = detect_cycle(&all_deps) {
        return Err(ResolutionError::Circular(cycle));
    }
    
    // 4. Topological sort
    let sorted = topological_sort(&all_deps)?;
    
    Ok(ResolutionResult { ordered: sorted })
}
```

---

## 8. Success Metrics

### 8.1 Adoption Metrics

| Metric | Target | Timeline |
|--------|--------|----------|
| Client downloads | 10K | 6 months |
| Skills registered | 1000 | 12 months |
| Average lookup latency | <1ms | Always |
| Uptime | 99.9% | Always |

### 8.2 Performance Metrics

| Metric | Target |
|--------|--------|
| Lookup p99 | <1ms |
| Registration p99 | <1ms |
| Resolution p99 | <10ms |
| Memory footprint | <50MB |

---

## 9. Release Criteria

### 9.1 MVP (v0.1.0)

- [ ] Rust daemon core
- [ ] Unix socket transport
- [ ] Core RPC methods
- [ ] TypeScript client
- [ ] Python client
- [ ] Auto-spawn

### 9.2 Beta (v0.5.0)

- [ ] TCP transport
- [ ] Dependency resolution
- [ ] All client SDKs
- [ ] Persistence
- [ ] Complete documentation

### 9.3 Production (v1.0.0)

- [ ] All P0/P1 requirements
- [ ] Windows support
- [ ] Production runbook
- [ ] Performance benchmarks
- [ ] Security review

---

## 10. Implementation Details

### 10.1 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Client SDKs (TypeScript, Python, etc.)        │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  • Auto-spawn • Connection pooling • Type-safe API     │  │
│  └─────────────────────────┬───────────────────────────────┘  │
└────────────────────────────┼────────────────────────────────────┘
                             │ IPC (Unix socket / TCP / Named pipes)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Rust Daemon Core                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   RPC        │  │   Skill      │  │   Dependency │         │
│  │   Server     │  │   Registry   │  │   Resolver   │         │
│  │              │  │              │  │              │         │
│  │ • Framing    │  │ • In-memory  │  │ • Topo sort  │         │
│  │ • Routing    │  │   storage    │  │ • Cycle detect│         │
│  │ • Protocol   │  │ • Persistence│  │ • Versioning │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
└─────────┼─────────────────┼─────────────────┼───────────────────┘
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Transport Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Unix       │  │   TCP        │  │   Named      │         │
│  │   Socket     │  │   (fallback) │  │   Pipes      │         │
│  │              │  │              │  │   (Windows)  │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

### 10.2 Technology Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Daemon | Rust + Tokio | Performance, safety, async |
| Serialization | MessagePack | Fast, compact, typed |
| Protocol | Custom RPC | Tailored for use case |
| Storage | DashMap (in-mem) | Concurrent, fast |
| Persistence | SQLite (optional) | Reliable, zero-config |

---

## 11. Testing Strategy

### 11.1 Test Categories

| Category | Focus |
|----------|-------|
| Unit | Core logic, resolution |
| Integration | Transport, protocol |
| E2E | Full client-daemon flow |
| Performance | Benchmarks, load |

### 11.2 Test Scenarios

1. **Skill lifecycle**: Register, get, list, unregister
2. **Resolution**: Various dependency graphs
3. **Circular detection**: Correct identification
4. **Transport**: Socket creation, connection
5. **Protocol**: Request/response, errors
6. **Client SDKs**: All language clients

---

## 12. Deployment and Operations

### 12.1 Installation

| Platform | Method |
|----------|--------|
| macOS | Homebrew: `brew install phenotype-daemon` |
| Linux | curl install script |
| Windows | Scoop/Chocolatey |
| Cargo | `cargo install phenotype-daemon` |

### 12.2 Operational Runbook

**Daemon not responding**:
1. Check if process running (`ps` or Task Manager)
2. Check socket/pipe exists
3. Try manual ping
4. Restart if needed

**High memory usage**:
1. Check number of registered skills
2. Review for memory leaks
3. Consider persistence settings

---

## 13. Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Socket conflicts | Medium | Medium | Unique paths, cleanup |
| Client compatibility | Medium | Low | Version negotiation |
| Performance regression | High | Low | Benchmarks in CI |
| Platform differences | Medium | Medium | CI on all platforms |

---

## 14. Appendix

### 14.1 Glossary

| Term | Definition |
|------|------------|
| **Skill** | Registered tool/capability |
| **Manifest** | Skill metadata and requirements |
| **Resolution** | Determining dependency order |
| **IPC** | Inter-process communication |
| **Transport** | Communication mechanism |

### 14.2 References

- [MessagePack](https://msgpack.org/)
- [Tokio](https://tokio.rs/)
- [JSON-RPC 2.0](https://www.jsonrpc.org/specification)

---

*End of Phenotype Daemon PRD v1.0.0*
