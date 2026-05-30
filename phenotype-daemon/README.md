# phenotype-daemon Documentation

Complete nanovms-level documentation for the phenotype-daemon system.

## Documentation Structure

```
phenotype-daemon/
├── SPEC.md                          # Main specification (2,545 lines)
├── docs/
│   ├── research/
│   │   └── DAEMON_SYSTEMS_SOTA.md   # State of the art research (1,518 lines)
│   └── adrs/
│       ├── ADR-001-transport-protocol.md    # 234 lines
│       ├── ADR-002-serialization-format.md  # 440 lines
│       └── ADR-003-process-lifecycle.md     # 511 lines
└── README.md                        # This file
```

**Total Documentation:** 5,248 lines

## Quick Navigation

### For New Users
1. Start with [SPEC.md](SPEC.md) - Section 1 (Overview)
2. Review client SDK documentation in Section 5
3. Follow deployment guides in Section 6

### For System Administrators
1. Read [SPEC.md](SPEC.md) - Section 6 (Deployment)
2. Review Section 9 (Operations)
3. Check Appendix B (Environment Variables)

### For Contributors
1. Study [DAEMON_SYSTEMS_SOTA.md](docs/research/DAEMON_SYSTEMS_SOTA.md)
2. Review all three ADRs
3. Read [SPEC.md](SPEC.md) - Section 2 (Architecture)
4. Check Appendix F (Implementation Details)

### For Architects
1. Read [DAEMON_SYSTEMS_SOTA.md](docs/research/DAEMON_SYSTEMS_SOTA.md) completely
2. Study all three ADRs for rationale
3. Review [SPEC.md](SPEC.md) Sections 2-4 in detail

## Document Summaries

### SPEC.md (2,545 lines)
Complete technical specification including:
- Architecture diagrams and component breakdown
- Wire protocol (MessagePack over length-prefixed framing)
- Full API reference with examples
- Client SDK documentation (TypeScript, Python, C#, Rust)
- Deployment patterns (dev, CI/CD, containers, Kubernetes, systemd, launchd)
- Performance benchmarks and optimization strategies
- Security model and threat mitigation
- Operations guide (logging, metrics, troubleshooting)
- 14 appendices with implementation details

### DAEMON_SYSTEMS_SOTA.md (1,518 lines)
Comprehensive state-of-the-art research comparing:
- **systemd** (Linux, detailed analysis)
- **launchd** (macOS/iOS)
- **Windows Service Control Manager**
- **supervisord** (Python, cross-platform)
- **s6** and emerging systems

Includes:
- Architecture comparisons
- Performance characteristics
- Security model analysis
- Lessons learned and anti-patterns
- Pattern recognition for phenotype-daemon design

### ADR-001: Transport Protocol (234 lines)
**Decision:** Unix sockets (primary), TCP (fallback), NATS (clustering)

**Rationale:**
- Unix sockets provide 2x better latency than TCP for local IPC
- Cross-platform compatibility requires TCP fallback
- NATS enables horizontal scaling for future requirements

### ADR-002: Serialization Format (440 lines)
**Decision:** MessagePack as primary, JSON for debugging

**Rationale:**
- 60-80% size reduction vs JSON
- 1.5-2x faster parsing than JSON
- No schema complexity (unlike Protobuf)
- Excellent cross-language library support

### ADR-003: Process Lifecycle (511 lines)
**Decision:** Auto-spawn with parent monitoring as primary mode

**Rationale:**
- Zero configuration for developers
- No orphaned processes (self-termination)
- Container-friendly (no init system required)
- System service mode still available for production

## Key Design Decisions

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Transport | Unix sockets + TCP | Performance + portability |
| Serialization | MessagePack | Efficiency + simplicity |
| Lifecycle | Auto-spawn | Developer experience |
| Concurrency | Tokio + DashMap | Lock-free reads, async I/O |
| Registry | In-memory | Sub-millisecond lookups |
| Protocol | Length-prefixed msgpack | Simple, efficient framing |

## Performance Targets

| Metric | Target | Achieved |
|--------|--------|----------|
| Latency (p99) | <1ms | 0.35ms |
| Throughput | 10K req/s | 45K req/s |
| Memory idle | <50MB | 15MB |
| Startup | <500ms | 200ms |

## Cross-Platform Support

| Platform | Transport | Lifecycle Mode |
|----------|-----------|----------------|
| Linux | Unix sockets | Auto-spawn / systemd |
| macOS | Unix sockets | Auto-spawn / launchd |
| Windows | TCP | Windows Service |
| Containers | TCP/Unix | Auto-spawn / health checks |

## Contributing

When contributing to phenotype-daemon:

1. Check if an ADR exists for your area of change
2. Update SPEC.md if modifying public APIs
3. Add test cases to the test suite
4. Update relevant documentation

## References

- [systemd Documentation](https://systemd.io/)
- [launchd Documentation](https://developer.apple.com/library/archive/documentation/Darwin/Reference/ManPages/man8/launchd.8.html)
- [MessagePack Specification](https://github.com/msgpack/msgpack/blob/master/spec.md)
- [Tokio Documentation](https://tokio.rs/)
- [DashMap Documentation](https://docs.rs/dashmap)

---

**Documentation Version:** 1.0.0  
**Last Updated:** 2026-04-04  
**Maintained By:** Phenotype Architecture Team
