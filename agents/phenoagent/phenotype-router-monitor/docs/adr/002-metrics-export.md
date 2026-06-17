# ADR-002: Metrics Export Strategy

## Status
**Accepted**

## Date
2026-04-04

## Context

The Phenotype Router Monitor must collect and export metrics about router health, latency, and errors. This decision impacts how operators observe and alert on the system.

### Requirements

1. **Prometheus Compatibility:** Must work with existing Prometheus infrastructure in Phenotype deployments
2. **OpenTelemetry Support:** Should align with modern observability standards
3. **Low Overhead:** Must not significantly impact router performance
4. **Flexible Export:** Support both pull (scrape) and push (OTLP) models
5. **Rich Metrics:** Support counters, gauges, and histograms

### Options Considered

| Approach | Pros | Cons |
|----------|------|------|
| **Prometheus Client Only** | Simple, battle-tested, pull model | Vendor lock-in, limited ecosystem |
| **OpenTelemetry Only** | Future-proof, vendor-neutral | Less mature, more complex |
| **Prometheus + OpenTelemetry** | Best of both worlds | More dependencies, complex configuration |
| **Custom Format** | Minimal dependencies | Reinventing the wheel, no ecosystem |

## Decision

We will implement a **hybrid strategy using OpenTelemetry SDK with Prometheus exporter**:

1. **Primary API:** OpenTelemetry metrics API for instrumentation
2. **Default Export:** Prometheus-compatible HTTP endpoint (`/metrics`)
3. **Optional Export:** OTLP push to OpenTelemetry Collector

### Architecture

```
                    +------------------+
                    |  Instrumentation |
                    |   (OpenTelemetry) |
                    +--------+---------+
                             |
              +--------------+--------------+
              |                             |
              v                             v
    +-------------------+         +-------------------+
    | Prometheus Exporter|         | OTLP Exporter    |
    | (Default)         |         | (Optional)       |
    +--------+---------+         +--------+---------+
             |                             |
             v                             v
    +-------------------+         +-------------------+
    | /metrics endpoint |         | OTEL Collector    |
    | (Prometheus scrapes)|       | (routing, filtering)|
    +-------------------+         +-------------------+
```

### Rationale

1. **Future-Proofing:** OpenTelemetry is becoming the industry standard. Major vendors (Datadog, New Relic, AWS) support it.

2. **Prometheus Compatibility:** The Prometheus exporter ensures compatibility with existing infrastructure without requiring changes.

3. **Ecosystem Alignment:** Using OpenTelemetry SDK enables easy integration with distributed tracing later.

4. **Vendor Neutrality:** Applications can switch between observability backends without code changes.

5. **Standard Semantic Conventions:** OpenTelemetry's semantic conventions ensure consistent metric naming.

## Consequences

### Positive

- Single instrumentation API for all metric types
- Easy migration path from Prometheus-only setups
- Built-in support for metric views and aggregations
- Exemplar support (linking metrics to traces)

### Negative

- Additional abstraction layer compared to direct Prometheus
- Slightly higher memory overhead from OpenTelemetry SDK
- More complex initial setup

### Mitigations

- Provide simple "Prometheus mode" that hides OpenTelemetry complexity
- Document clear migration path for existing Prometheus users
- Benchmark overhead to ensure it meets SLOs

## Implementation Details

### Metric Types Mapping

| OpenTelemetry | Prometheus | Use Case |
|--------------|------------|----------|
| Counter | Counter | Request counts, error totals |
| UpDownCounter | Gauge | Active connections, queue depth |
| Histogram | Histogram | Latency distributions |
| ObservableGauge | Gauge | Current temperature, memory |

### Default Metrics

```rust
// src/metrics.rs
use opentelemetry::metrics::{Counter, Histogram, UpDownCounter};

pub struct RouterMetrics {
    /// Total number of health checks performed
    pub checks_total: Counter<u64>,
    
    /// Failed health check counter
    pub check_failures_total: Counter<u64>,
    
    /// Health check latency histogram
    pub check_latency_ms: Histogram<u64>,
    
    /// Currently configured routes
    pub routes_configured: UpDownCounter<i64>,
    
    /// Active health check goroutines
    pub active_checks: UpDownCounter<i64>,
}

impl RouterMetrics {
    pub fn new(meter: &Meter) -> Self {
        Self {
            checks_total: meter
                .u64_counter("router_checks_total")
                .with_description("Total health checks executed")
                .build(),
            
            check_failures_total: meter
                .u64_counter("router_check_failures_total")
                .with_description("Failed health checks")
                .build(),
            
            check_latency_ms: meter
                .u64_histogram("router_check_latency_ms")
                .with_description("Health check latency in milliseconds")
                .with_unit("ms")
                .with_boundaries(vec![
                    5.0, 10.0, 25.0, 50.0, 100.0, 
                    250.0, 500.0, 1000.0, 2500.0, 5000.0
                ])
                .build(),
            
            routes_configured: meter
                .i64_up_down_counter("router_routes_configured")
                .with_description("Number of configured routes")
                .build(),
            
            active_checks: meter
                .i64_up_down_counter("router_active_checks")
                .with_description("Active concurrent health checks")
                .build(),
        }
    }
}
```

### Prometheus Export Setup

```rust
// src/exporter/prometheus.rs
use opentelemetry_prometheus::PrometheusExporter;
use prometheus::{Encoder, TextEncoder};

pub fn init_prometheus_exporter() -> PrometheusExporter {
    let exporter = opentelemetry_prometheus::exporter()
        .with_namespace("phenotype_router")
        .build()
        .expect("Failed to create Prometheus exporter");
    
    // Register with global provider
    let provider = SdkMeterProvider::builder()
        .with_reader(exporter.clone())
        .build();
    
    global::set_meter_provider(provider);
    
    exporter
}

// HTTP endpoint handler
pub async fn metrics_endpoint() -> impl IntoResponse {
    let encoder = TextEncoder::new();
    let metric_families = prometheus::gather();
    let mut buffer = Vec::new();
    
    encoder.encode(&metric_families, &mut buffer)
        .expect("Failed to encode metrics");
    
    (
        StatusCode::OK,
        [(header::CONTENT_TYPE, "text/plain; charset=utf-8")],
        buffer
    )
}
```

### OTLP Export Setup (Optional)

```rust
// src/exporter/otlp.rs
use opentelemetry_otlp::{Protocol, WithExportConfig};

pub fn init_otlp_exporter(endpoint: &str) -> Result<()> {
    let exporter = opentelemetry_otlp::new_exporter()
        .tonic()
        .with_endpoint(endpoint)
        .with_protocol(Protocol::Grpc)
        .with_timeout(Duration::from_secs(10));
    
    let provider = SdkMeterProvider::builder()
        .with_periodic_exporter(exporter)
        .build();
    
    global::set_meter_provider(provider);
    
    Ok(())
}
```

### Configuration

```toml
# Config file
[metrics]
# Primary export format: "prometheus" or "otlp"
format = "prometheus"

# Prometheus endpoint settings
[metrics.prometheus]
enabled = true
path = "/metrics"
port = 9090

# OTLP settings (optional)
[metrics.otlp]
enabled = false
endpoint = "http://localhost:4317"
protocol = "grpc"
export_interval_seconds = 60

# Metric filtering
[metrics.views]
# Exclude high-cardinality routes from latency histogram
exclude_labels = ["request_id", "user_id"]
```

## Metric Design Guidelines

### Naming Conventions

Follow OpenTelemetry semantic conventions:

```
# Domain-specific prefix
phenotype_router_{metric}_{unit}

# Examples
phenotype_router_checks_total          # counter
phenotype_router_check_latency_ms      # histogram
phenotype_router_routes_configured     # updowncounter
```

### Label Cardinality

**Critical:** Control label cardinality to prevent performance issues:

```rust
// BAD - Unbounded cardinality
counter.add(1, &[
    KeyValue::new("route", full_path),  // /users/12345, /users/67890
    KeyValue::new("user_id", user_id),
]);

// GOOD - Bounded cardinality
counter.add(1, &[
    KeyValue::new("route", route_template),  // /users/:id
    KeyValue::new("status", status_code),
]);
```

### Histogram Buckets

Choose buckets appropriate for expected values:

| Metric Type | Suggested Buckets (ms) |
|------------|----------------------|
| API latency | 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000 |
| Health checks | 10, 25, 50, 100, 250, 500, 1000, 5000 |
| Database queries | 1, 5, 10, 25, 50, 100, 250, 500 |

## Testing Strategy

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use opentelemetry_sdk::metrics::data::Sum;
    use opentelemetry_sdk::metrics::InMemoryMetricExporter;
    
    #[tokio::test]
    async fn test_metrics_collection() {
        // Set up in-memory exporter for testing
        let exporter = InMemoryMetricExporter::default();
        let provider = SdkMeterProvider::builder()
            .with_reader(exporter.clone())
            .build();
        
        let meter = provider.meter("test");
        let metrics = RouterMetrics::new(&meter);
        
        // Record metrics
        metrics.checks_total.add(1, &[]);
        
        // Force flush
        provider.force_flush().unwrap();
        
        // Verify
        let metrics = exporter.get_finished_metrics().unwrap();
        assert!(!metrics.is_empty());
    }
}
```

## Alternatives Considered in Detail

### Prometheus Client Only

**Why not chosen:**
- Locks us into Prometheus ecosystem
- Harder to add distributed tracing later
- No support for exemplars

**When it would be better:**
- Simple deployments with no plans for tracing
- When minimizing dependencies is critical

### OpenTelemetry Only (No Prometheus)

**Why not chosen:**
- Would require all users to run OpenTelemetry Collector
- Prometheus is ubiquitous in existing infrastructure
- Pull model (scrape) is preferred by many operators

**When it would be better:**
- Greenfield deployments with OpenTelemetry Collector
- When push model is required (serverless)

## Related Decisions

- ADR-001: Async Runtime Architecture (OTLP export requires async runtime)
- ADR-003: Health Check Pattern (metrics collected during checks)

## References

1. OpenTelemetry Metrics Specification: https://opentelemetry.io/docs/specs/otel/metrics/
2. Prometheus Best Practices: https://prometheus.io/docs/practices/
3. OpenTelemetry Rust SDK: https://github.com/open-telemetry/opentelemetry-rust
4. Semantic Conventions: https://opentelemetry.io/docs/specs/semconv/

## History

| Date | Author | Change |
|------|--------|--------|
| 2026-04-04 | Phenotype Team | Initial decision |
