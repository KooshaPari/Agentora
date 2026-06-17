# ADR-003: Health Check Pattern

## Status
**Accepted**

## Date
2026-04-04

## Context

The Phenotype Router Monitor's core responsibility is determining router health. This decision defines how health checks are performed, how results are aggregated, and how failures are handled.

### Requirements

1. **Multiple Check Types:** Support liveness, readiness, and custom deep checks
2. **Concurrent Execution:** Check multiple routes simultaneously without blocking
3. **Configurable Thresholds:** Support consecutive failures, error percentages, and timeouts
4. **Resilience:** Prevent health check storms and cascading failures
5. **Observability:** Rich metrics and logging for health check operations

### Options Considered

| Pattern | Pros | Cons |
|---------|------|------|
| **Sequential Polling** | Simple, predictable | Slow, doesn't scale |
| **Parallel with JoinAll** | Fast, concurrent | Resource exhaustion risk |
| **Parallel with Semaphore** | Controlled concurrency | More complex |
| **Parallel with Circuit Breaker** | Resilient | Most complex |
| **Event-Driven (Reactive)** | Efficient for high scale | Complex mental model |

## Decision

We will implement a **controlled parallelism pattern with circuit breaker protection**:

1. **Concurrency Control:** Semaphore-limited concurrent checks
2. **Resilience:** Circuit breaker per route for failure isolation
3. **Aggregation:** Weighted health scoring for graduated degradation
4. **Backoff:** Exponential backoff with jitter for failing routes

### Architecture

```
+-------------------+     +------------------+     +------------------+
|   Route Config    | --> |  Check Scheduler | --> |  Semaphore Pool  |
|  (routes.toml)    |     |  (tokio::spawn)  |     | (max_concurrent) |
+-------------------+     +--------+---------+     +--------+---------+
                                   |                        |
                                   v                        v
                          +------------------+     +------------------+
                          |  Per-Route Check | <-- |  Acquire Permit  |
                          |  + Circuit Breaker|     |                  |
                          +--------+---------+     +------------------+
                                   |
                    +--------------+--------------+
                    |                             |
                    v                             v
           +-------------------+         +-------------------+
           |  Check Result     |         |  Metrics Export   |
           |  (pass/fail/degraded)|      |  (OpenTelemetry)  |
           +--------+---------+         +-------------------+
                    |
                    v
           +-------------------+
           |  Health Aggregator|
           |  (weighted score) |
           +--------+---------+
                    |
                    v
           +-------------------+
           |  API Response      |
           | /health, /ready    |
           +-------------------+
```

### Rationale

1. **Controlled Parallelism:** Semaphores prevent resource exhaustion during high route counts or slow checks.

2. **Circuit Breaker Isolation:** Per-route circuit breakers prevent a single failing route from affecting others.

3. **Graduated Degradation:** Binary healthy/unhealthy models miss nuanced failure states. Weighted scoring enables partial traffic shifting.

4. **Backoff Protection:** Exponential backoff prevents thundering herd during recovery.

## Consequences

### Positive

- Predictable resource usage under all load conditions
- Fast failure detection and isolation
- Graceful degradation support
- Rich operational metrics

### Negative

- More complex than simple polling
- Requires careful tuning of semaphore limits
- Circuit breaker state adds memory overhead

### Mitigations

- Provide sensible defaults for all tunables
- Auto-tune semaphore limits based on route count
- Document tuning guide with workload examples

## Implementation Details

### Core Types

```rust
// src/health/types.rs

/// Health state with graduated degradation
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum HealthState {
    /// All checks passing
    Healthy,
    /// Some non-critical checks failing
    Degraded,
    /// Critical checks failing
    Unhealthy,
    /// Insufficient data to determine health
    Unknown,
}

/// Individual check result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CheckResult {
    pub route_id: String,
    pub state: HealthState,
    pub latency: Duration,
    pub timestamp: DateTime<Utc>,
    pub error: Option<String>,
    pub metadata: HashMap<String, String>,
}

/// Aggregated health for a router
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthSnapshot {
    pub router_id: String,
    pub overall_state: HealthState,
    pub score: f64,  // 0.0 - 1.0
    pub checks: Vec<CheckResult>,
    pub last_updated: DateTime<Utc>,
}
```

### Circuit Breaker Configuration

```rust
// src/health/circuit_breaker.rs

pub struct CircuitBreakerConfig {
    /// Consecutive failures before opening
    pub failure_threshold: u32,
    /// Error percentage threshold (0.0 - 1.0)
    pub error_percentage_threshold: f64,
    /// Time window for error percentage calculation
    pub window_duration: Duration,
    /// Time before attempting reset (half-open)
    pub reset_timeout: Duration,
    /// Number of successes required to close
    pub success_threshold: u32,
    /// Maximum concurrent requests in half-open state
    pub half_open_max_calls: u32,
}

impl Default for CircuitBreakerConfig {
    fn default() -> Self {
        Self {
            failure_threshold: 5,
            error_percentage_threshold: 0.5,
            window_duration: Duration::from_secs(60),
            reset_timeout: Duration::from_secs(30),
            success_threshold: 3,
            half_open_max_calls: 1,
        }
    }
}
```

### Check Execution

```rust
// src/health/executor.rs

pub struct CheckExecutor {
    semaphore: Arc<Semaphore>,
    breakers: Arc<RwLock<HashMap<String, CircuitBreaker>>>,
    metrics: Arc<RouterMetrics>,
    client: reqwest::Client,
}

impl CheckExecutor {
    pub async fn execute_check(&self, route: &Route) -> CheckResult {
        let start = Instant::now();
        
        // Acquire concurrency permit
        let _permit = match self.semaphore.acquire().await {
            Ok(p) => p,
            Err(_) => {
                return CheckResult::error(
                    route.id.clone(),
                    "Too many concurrent checks"
                );
            }
        };
        
        // Check circuit breaker state
        let breaker = self.get_breaker(&route.id).await;
        if !breaker.can_execute() {
            return CheckResult::circuit_open(route.id.clone());
        }
        
        // Execute check with timeout
        let result = self.perform_check(route).await;
        let latency = start.elapsed();
        
        // Update circuit breaker
        match &result {
            Ok(_) => breaker.record_success(),
            Err(_) => breaker.record_failure(),
        }
        
        // Record metrics
        self.metrics.checks_total.add(1, &[
            KeyValue::new("route", route.id.clone()),
            KeyValue::new("result", result.is_ok().to_string()),
        ]);
        
        self.metrics.check_latency_ms.record(
            latency.as_millis() as u64,
            &[KeyValue::new("route", route.id.clone())],
        );
        
        CheckResult::from_result(route.id.clone(), result, latency)
    }
    
    async fn perform_check(&self, route: &Route) -> Result<(), CheckError> {
        let response = tokio::time::timeout(
            route.timeout,
            self.client
                .request(route.method.clone(), route.url.clone())
                .headers(route.headers.clone())
                .send()
        ).await??;
        
        if !route.expected_statuses.contains(&response.status().as_u16()) {
            return Err(CheckError::UnexpectedStatus(response.status()));
        }
        
        Ok(())
    }
}
```

### Health Aggregation

```rust
// src/health/aggregator.rs

pub struct HealthAggregator {
    /// Weight configuration per check type
    weights: HashMap<CheckType, f64>,
}

impl HealthAggregator {
    pub fn aggregate(&self, checks: &[CheckResult]) -> HealthSnapshot {
        let total_weight: f64 = checks.iter()
            .map(|c| self.weights.get(&c.check_type).copied().unwrap_or(1.0))
            .sum();
        
        let weighted_score: f64 = checks.iter()
            .map(|c| {
                let weight = self.weights.get(&c.check_type).copied().unwrap_or(1.0);
                let score = match c.state {
                    HealthState::Healthy => 1.0,
                    HealthState::Degraded => 0.5,
                    HealthState::Unhealthy => 0.0,
                    HealthState::Unknown => 0.5,
                };
                weight * score
            })
            .sum::<f64>() / total_weight;
        
        let overall_state = self.score_to_state(weighted_score);
        
        HealthSnapshot {
            router_id: self.router_id.clone(),
            overall_state,
            score: weighted_score,
            checks: checks.to_vec(),
            last_updated: Utc::now(),
        }
    }
    
    fn score_to_state(&self, score: f64) -> HealthState {
        match score {
            s if s >= 0.9 => HealthState::Healthy,
            s if s >= 0.5 => HealthState::Degraded,
            _ => HealthState::Unhealthy,
        }
    }
}
```

### Exponential Backoff

```rust
// src/health/backoff.rs

pub struct ExponentialBackoff {
    base: Duration,
    max: Duration,
    jitter: f64,  // 0.0 - 1.0
    attempt: u32,
}

impl ExponentialBackoff {
    pub fn next_delay(&mut self) -> Duration {
        let exponential = self.base * 2_u32.pow(self.attempt);
        let capped = std::cmp::min(exponential, self.max);
        
        let jitter_range = capped.mul_f64(self.jitter);
        let jitter = Duration::from_millis(
            rand::random::<u64>() % jitter_range.as_millis() as u64
        );
        
        self.attempt += 1;
        capped + jitter
    }
    
    pub fn reset(&mut self) {
        self.attempt = 0;
    }
}

impl Default for ExponentialBackoff {
    fn default() -> Self {
        Self {
            base: Duration::from_secs(1),
            max: Duration::from_secs(60),
            jitter: 0.1,
            attempt: 0,
        }
    }
}
```

### Configuration

```toml
# health.toml
[health]
# Global settings
max_concurrent_checks = 100
default_timeout_seconds = 5

# Aggregation weights
[health.weights]
liveness = 1.0
readiness = 2.0
custom_critical = 3.0
custom_non_critical = 0.5

# Circuit breaker defaults
[health.circuit_breaker]
failure_threshold = 5
error_percentage = 50.0  # percent
window_seconds = 60
reset_timeout_seconds = 30
success_threshold = 3
half_open_max_calls = 1

# Backoff configuration
[health.backoff]
base_seconds = 1
max_seconds = 60
jitter = 0.1  # 10% randomization

# Per-route overrides
[[health.routes]]
id = "api-gateway"
url = "http://api.internal/health"
timeout_seconds = 3
check_interval_seconds = 10

[health.routes.circuit_breaker]
failure_threshold = 3  # More sensitive for critical path
reset_timeout_seconds = 15  # Faster recovery attempt

[[health.routes]]
id = "analytics-service"
url = "http://analytics.internal/ready"
timeout_seconds = 10
check_interval_seconds = 30
non_critical = true  # Degraded, not unhealthy on failure
```

## API Design

### Health Endpoints

```rust
// src/api/health.rs

/// Liveness probe - returns 200 if service is running
async fn liveness() -> impl IntoResponse {
    StatusCode::OK
}

/// Readiness probe - returns 200 if ready to serve traffic
async fn readiness(State(state): State<Arc<AppState>>) -> impl IntoResponse {
    let snapshot = state.health_aggregator.get_snapshot().await;
    
    let status = match snapshot.overall_state {
        HealthState::Healthy => StatusCode::OK,
        HealthState::Degraded => StatusCode::OK, // Still serving traffic
        HealthState::Unhealthy => StatusCode::SERVICE_UNAVAILABLE,
        HealthState::Unknown => StatusCode::SERVICE_UNAVAILABLE,
    };
    
    (status, Json(snapshot))
}

/// Detailed health check for operators
async fn health_details(State(state): State<Arc<AppState>>) -> impl IntoResponse {
    let details = state.health_aggregator.get_detailed_snapshot().await;
    Json(details)
}
```

### Response Format

```json
{
  "router_id": "production-router-1",
  "overall_state": "degraded",
  "score": 0.75,
  "last_updated": "2026-04-04T12:00:00Z",
  "checks": [
    {
      "route_id": "api-gateway",
      "state": "healthy",
      "latency_ms": 15,
      "timestamp": "2026-04-04T12:00:00Z"
    },
    {
      "route_id": "database",
      "state": "degraded",
      "latency_ms": 2500,
      "timestamp": "2026-04-04T12:00:00Z",
      "error": "Elevated latency detected"
    }
  ],
  "circuit_breakers": [
    {
      "route_id": "external-api",
      "state": "open",
      "failures": 5,
      "last_failure": "2026-04-04T11:59:30Z"
    }
  ]
}
```

## Testing Strategy

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use tokio::time::{pause, advance, Duration};
    
    #[tokio::test]
    async fn test_circuit_breaker_opens_after_failures() {
        let mut breaker = CircuitBreaker::new(CircuitBreakerConfig {
            failure_threshold: 3,
            ..Default::default()
        });
        
        // Record failures
        breaker.record_failure();
        breaker.record_failure();
        breaker.record_failure();
        
        assert_eq!(breaker.state(), BreakerState::Open);
    }
    
    #[tokio::test]
    async fn test_exponential_backoff() {
        let mut backoff = ExponentialBackoff {
            base: Duration::from_secs(1),
            max: Duration::from_secs(10),
            jitter: 0.0,
            attempt: 0,
        };
        
        assert_eq!(backoff.next_delay(), Duration::from_secs(1));
        assert_eq!(backoff.next_delay(), Duration::from_secs(2));
        assert_eq!(backoff.next_delay(), Duration::from_secs(4));
        assert_eq!(backoff.next_delay(), Duration::from_secs(8));
        assert_eq!(backoff.next_delay(), Duration::from_secs(10)); // capped
    }
    
    #[tokio::test]
    async fn test_semaphore_limits_concurrency() {
        let semaphore = Arc::new(Semaphore::new(2));
        
        let permit1 = semaphore.try_acquire().unwrap();
        let permit2 = semaphore.try_acquire().unwrap();
        let permit3 = semaphore.try_acquire();
        
        assert!(permit3.is_err());
    }
}
```

## Performance Considerations

### Memory Usage

| Component | Per Route | 100 Routes |
|-----------|-----------|------------|
| Circuit Breaker | ~256 bytes | ~25 KB |
| Check History | ~1 KB | ~100 KB |
| Metrics | ~512 bytes | ~50 KB |
| **Total** | **~1.8 KB** | **~175 KB** |

### Latency Budget

| Operation | Budget | Notes |
|-----------|--------|-------|
| Semaphore acquire | < 1ms | Contention on high concurrency |
| Circuit breaker check | < 0.1ms | In-memory state lookup |
| HTTP check | < timeout | Network-dependent |
| Result aggregation | < 1ms | Linear in check count |
| Metrics export | < 10ms | Async, non-blocking |

## Operational Guidelines

### Tuning for Workload Types

**High-Frequency, Low-Latency (API Gateway):**
```toml
max_concurrent_checks = 50
default_timeout_seconds = 2
check_interval_seconds = 5
```

**Low-Frequency, High-Latency (Analytics):**
```toml
max_concurrent_checks = 10
default_timeout_seconds = 30
check_interval_seconds = 60
```

**Mixed Workload (Microservices):**
```toml
max_concurrent_checks = 100
default_timeout_seconds = 5
[health.routes]
# Per-service overrides as needed
```

### Alerting Recommendations

| Metric | Warning Threshold | Critical Threshold |
|--------|------------------|-------------------|
| router_health_score < | 0.8 for 5m | 0.5 for 2m |
| router_circuit_breakers_open > | 1 for 10m | 5 for 5m |
| router_check_latency_p99 > | 1000ms | 5000ms |
| router_check_failures_rate > | 1% | 5% |

## Alternatives Considered in Detail

### Pure Sequential Polling

**Why not chosen:**
- 100 routes * 5 second timeout = 500 seconds worst case
- No resilience against slow checks

**When it would be better:**
- Very small route counts (< 5)
- Simple deployments without resilience requirements

### Pure Event-Driven (Reactive Streams)

**Why not chosen:**
- Steeper learning curve for operators
- Harder to reason about ordering and consistency
- Tokio's async/await is sufficient for our scale

**When it would be better:**
- > 10,000 routes
- Complex event sourcing requirements
- When backpressure is critical

## Related Decisions

- ADR-001: Async Runtime Architecture (uses Tokio for execution)
- ADR-002: Metrics Export Strategy (exports health check metrics)

## References

1. Nygard, Michael T. *Release It!* 2nd ed., Pragmatic Bookshelf, 2018.
2. Beyer et al. *Site Reliability Engineering.* O'Reilly, 2016.
3. Polly Circuit Breaker Documentation: https://www.pollydocs.org/strategies/circuit-breaker.html
4. Kubernetes Probe Documentation: https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/

## History

| Date | Author | Change |
|------|--------|--------|
| 2026-04-04 | Phenotype Team | Initial decision |
