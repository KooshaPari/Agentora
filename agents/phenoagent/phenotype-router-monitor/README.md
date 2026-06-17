# phenotype-router-monitor — HTTP Router Health & Metrics

Rust library for distributed HTTP request routing with real-time health checks, latency tracking, and circuit breaker fault tolerance. Exports Prometheus metrics for production observability.

## Overview

**phenotype-router-monitor** bridges request routing with observability, providing robust request handling with automatic fallback and degradation. It monitors route health, tracks latencies, and exposes rich metrics for distributed systems operating at scale.

**Core Mission**: Enable safe, observable request routing with automatic fault tolerance and minimal operational overhead in polyglot microservice environments.

## Technology Stack

- **Language**: Rust (Edition 2021)
- **Async Runtime**: Tokio
- **HTTP Client**: Reqwest with connection pooling
- **Metrics**: Prometheus format export
- **Configuration**: TOML-based route definitions
- **Serialization**: Serde with JSON/TOML support

## Key Features

- **Circuit Breaker Pattern**: Automatic failure detection and request fallback
- **Health Checks**: Configurable liveness and readiness probes per route
- **Latency Instrumentation**: Per-route, per-endpoint latency histograms
- **Prometheus Export**: Native metrics endpoint for Grafana/Thanos integration
- **Request Buffering**: Configurable queue and backpressure handling
- **Weighted Routing**: Load distribution across multiple backends
- **Automatic Retry**: Configurable retry logic with exponential backoff
- **Span Integration**: OpenTelemetry trace linkage for end-to-end visibility

## Quick Start

```bash
# Navigate to sub-crate
cd /Users/kooshapari/CodeProjects/Phenotype/repos/PhenoProc/phenotype-router-monitor

# Build and test
cargo build --release
cargo test --lib

# Run example router
cargo run --example monitor_routes -- --config examples/routes.toml

# Export metrics endpoint
curl http://localhost:9090/metrics
```

## Project Structure

```
phenotype-router-monitor/
├── Cargo.toml
├── src/
│   ├── lib.rs                    # Library exports, Router trait
│   ├── monitor.rs                # Health monitor orchestration
│   ├── circuit_breaker.rs        # Fault tolerance patterns
│   ├── metrics.rs                # Prometheus instrumentation
│   ├── api.rs                    # Route definition types
│   └── config.rs                 # Configuration loading
├── examples/
│   ├── monitor_routes.rs         # Route monitoring example
│   └── custom_policies.rs        # Custom circuit breaker logic
├── tests/
│   ├── integration_tests.rs      # End-to-end router tests
│   └── fixtures/
├── CLAUDE.md                     # Development guidelines
└── README.md                     # This file
```

## Related Phenotype Projects

- **PhenoProc** — Parent monorepo; process orchestration framework
- **Tracera** — Observability platform consuming router metrics
- **phenotype-validation** — Applies validation to routed request/response payloads

## License & Governance

Licensed under Apache 2.0 (note: README originally stated MIT; see LICENSE in repository root). Governance in `CLAUDE.md`. Functional requirements and FR-to-test mapping in `FUNCTIONAL_REQUIREMENTS.md`.
