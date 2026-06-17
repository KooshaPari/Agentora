# SPECIFICATION: Phenotype Router Monitor

## Overview

HTTP router monitoring and diagnostics library for Rust services in the Phenotype ecosystem.

## Architecture

### Core Components

| Component | Responsibility |
|-----------|----------------|
| `Monitor` | Orchestrates monitoring operations |
| `Checker` | Executes health checks against routes |
| `Collector` | Aggregates metrics from checks |
| `Exporter` | Exports metrics to external systems |

### Data Flow

```
Config → Monitor → Checker → Route → Response
                          ↓
                    Collector → Exporter → Prometheus/OTel
```

## Configuration

### TOML Format

```toml
[monitor]
interval_seconds = 30
metrics_enabled = true

[[routes]]
name = "health_endpoint"
path = "/health"
method = "GET"
expected_status = 200
timeout_ms = 5000

[[routes]]
name = "api_users"
path = "/api/v1/users"
method = "GET"
headers = { Authorization = "Bearer ${TOKEN}" }
```

## API Surface

### Monitor

```rust
pub struct Monitor {
    config: Config,
    collectors: Vec<Box<dyn Collector>>,
}

impl Monitor {
    pub async fn new(config: Config) -> Result<Self, Error>;
    pub async fn start(&self) -> Result<(), Error>;
    pub async fn stop(&self) -> Result<(), Error>;
}
```

### Health Check

```rust
pub trait Checker: Send + Sync {
    async fn check(&self, route: &Route) -> Result<CheckResult, Error>;
}

pub struct CheckResult {
    pub latency_ms: u64,
    pub status: Status,
    pub timestamp: DateTime<Utc>,
}
```

## Metrics

### Collected Metrics

- `router_check_latency_ms` - Histogram of check latency
- `router_check_failures_total` - Counter of failed checks
- `router_routes_configured` - Gauge of configured routes

### Labels

- `route_name` - Route identifier
- `method` - HTTP method
- `status` - Check result status

## Dependencies

- `tokio` - Async runtime
- `reqwest` - HTTP client
- `serde` - Configuration serialization
- `chrono` - Timestamp handling
- `thiserror` - Error handling
