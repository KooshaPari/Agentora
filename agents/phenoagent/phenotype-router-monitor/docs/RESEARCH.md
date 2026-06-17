# State of the Art: Router Monitoring & Observability

## Executive Summary

This document presents a comprehensive analysis of state-of-the-art patterns, implementations, and research in router monitoring, health checking, and observability systems. It serves as the foundational research for the Phenotype Router Monitor architecture.

**Document Version:** 1.0  
**Last Updated:** 2026-04-04  
**Scope:** HTTP router monitoring, health checks, metrics collection, resilience patterns  

---

## Table of Contents

1. [Introduction](#introduction)
2. [Health Check Patterns](#health-check-patterns)
3. [Circuit Breaker & Resilience Patterns](#circuit-breaker--resilience-patterns)
4. [Metrics Collection Systems](#metrics-collection-systems)
5. [Observability Standards](#observability-standards)
6. [Async Runtime Considerations](#async-runtime-considerations)
7. [Alerting & SLO Management](#alerting--slo-management)
8. [Distributed Systems Health Checking](#distributed-systems-health-checking)
9. [Latency Profiling Techniques](#latency-profiling-techniques)
10. [Production Case Studies](#production-case-studies)
11. [Bibliography](#bibliography)

---

## Introduction

### Problem Domain

Router monitoring in modern distributed systems encompasses three primary concerns:

1. **Health Determination:** Accurately assessing whether routes are capable of serving traffic
2. **Performance Tracking:** Measuring latency, throughput, and error rates at the edge
3. **Resilience Engineering:** Preventing cascading failures through circuit breaking and graceful degradation

### Historical Evolution

The evolution of router monitoring follows three distinct eras:

**Era 1: Static Load Balancing (1990s-2000s)**
- Simple heartbeat checks at fixed intervals
- Binary up/down health states
- Little consideration for partial degradation

**Era 2: Dynamic Health Discovery (2010s)**
- Introduction of health check endpoints (/health, /ready)
- Gradual rollout patterns (canary, blue/green)
- Integration with service discovery (Consul, etcd)

**Era 3: Observability-Driven Monitoring (2020s)**
- OpenTelemetry standardization
- SLO-based alerting replacing threshold-based alerts
- eBPF-based kernel-level introspection
- ML-based anomaly detection

### Scope Boundaries

This document focuses specifically on:
- HTTP/HTTPS route monitoring
- Application-layer health checking (L7)
- Real-time metrics collection
- Client-side resilience patterns

Out of scope:
- Network-layer monitoring (L3/L4)
- Infrastructure monitoring (CPU, memory, disk)
- Business metrics and analytics

---

## Health Check Patterns

### The Health Check Endpoint Pattern

The de facto standard established by Kubernetes and popularized by the Twelve-Factor App methodology defines three distinct health probes:

#### Liveness Probe

**Purpose:** Indicates whether the application is running and should be restarted if failing.

**Characteristics:**
- Fast response time (< 1s typical)
- Minimal resource consumption
- Checks internal state only (no external dependencies)

**Implementation Pattern:**
```
GET /health/live
Response: 200 OK
Body: {"status": "alive", "timestamp": "2026-04-04T12:00:00Z"}
```

**Failure Handling:**
- Consecutive failures trigger restart
- Should be conservative to avoid flapping

#### Readiness Probe

**Purpose:** Indicates whether the application is ready to receive traffic.

**Characteristics:**
- May check external dependencies (databases, caches)
- Can be temporarily removed from load balancer rotation
- Reflects transient states (startup, warmup, draining)

**Implementation Pattern:**
```
GET /health/ready
Response: 200 OK (ready) or 503 Service Unavailable (not ready)
Body: {
  "status": "ready",
  "checks": {
    "database": {"status": "pass", "response_time_ms": 15},
    "cache": {"status": "pass", "response_time_ms": 5},
    "external_api": {"status": "degraded", "response_time_ms": 2500}
  }
}
```

#### Startup Probe

**Purpose:** Protects slow-starting containers from premature liveness/readiness checks.

**Characteristics:**
- Disables liveness/readiness until successful
- Can have longer timeouts
- Critical for JVM, .NET, and other runtime-heavy applications

### Health Check Algorithms

#### Exponential Backoff for Health Checks

Naive fixed-interval health checking creates thundering herd problems during recovery. Exponential backoff provides a more graceful approach:

**Algorithm:**
```
interval = min(base * (2 ^ failures), max_interval)
jitter = random(0, interval * 0.1)
next_check = now + interval + jitter
```

**Parameters:**
- `base`: Initial interval (e.g., 1 second)
- `max_interval`: Ceiling (e.g., 60 seconds)
- `jitter`: Randomization to prevent synchronization

#### Consecutive Failure Thresholds

Single failures should not trigger actions. The industry standard uses consecutive thresholds:

| Severity | Consecutive Failures | Action |
|----------|---------------------|--------|
| Warning | 1 | Log, increment metric |
| Critical | 3 | Circuit breaker open |
| Catastrophic | 5 | Page on-call |

#### Degraded State Detection

Binary healthy/unhealthy models miss partial degradation. Modern systems implement graduated health states:

```rust
enum HealthState {
    Healthy,      // All checks passing
    Degraded,     // Some non-critical checks failing
    Unhealthy,    // Critical checks failing
    Unknown,      // Insufficient data
}
```

**Degradation Indicators:**
- Elevated latency (p95 > baseline * 2)
- Elevated error rate (> 0.1% for 5 minutes)
- Resource pressure (connection pool exhaustion)
- Dependency degradation (cache miss rate spike)

### Health Check Implementations in the Wild

#### Kubernetes Probe Implementation

Kubernetes implements the most widely deployed health check system:

**Probe Types:**
- HTTP GET: Most common for web applications
- TCP Socket: For non-HTTP services
- gRPC: Native support since v1.24
- Exec: Custom command execution

**Configuration Parameters:**
```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
  successThreshold: 1
```

**Key Insights:**
- `initialDelaySeconds` is often set too low, causing startup failures
- `periodSeconds` should reflect the criticality of the service
- `failureThreshold * periodSeconds` = time to action

#### AWS ELB Health Checks

Application Load Balancers use a simpler model:

```
Interval: 5-300 seconds (default: 30)
Timeout: 2-120 seconds (must be < interval)
Healthy Threshold: 2-10 consecutive successes
Unhealthy Threshold: 2-10 consecutive failures
```

**Unique Features:**
- Supports HTTP/HTTPS targets
- Can use custom ports
- Returns 200 OK only for healthy

#### Google Cloud Health Checks

Google Cloud provides global health check service:

```
Check Interval: 1-300 seconds
Timeout: 1-120 seconds
Protocol: HTTP, HTTPS, HTTP/2, TCP, SSL, GRPC
```

**Advanced Features:**
- Content-based health checks (response body validation)
- Custom headers
- Proxy support

---

## Circuit Breaker & Resilience Patterns

### The Circuit Breaker Pattern

The circuit breaker pattern, popularized by Michael Nygard in "Release It!", prevents cascading failures by temporarily rejecting requests to failing services.

#### States

```
        +-----------+     failure threshold exceeded      +-----------+
        |   CLOSED  | -----------------------------------> |   OPEN    |
        | (normal)  |                                       | (failing) |
        +-----------+                                       +-----------+
              ^                                                   |
              |  success threshold reached                        | timeout
              |                                                   |
              +---------------------------------------------------+
                                    HALF-OPEN
                                 (testing recovery)
```

#### State Transitions

**CLOSED → OPEN:**
- Trigger: Failure rate exceeds threshold (e.g., 50% over 30 seconds)
- OR: Consecutive failures reach threshold (e.g., 5 in a row)
- Action: Reject requests immediately with fallback

**OPEN → HALF-OPEN:**
- Trigger: Timeout expires (e.g., 60 seconds)
- Action: Allow limited probe requests (e.g., 1 per 10 seconds)

**HALF-OPEN → CLOSED:**
- Trigger: Success rate meets threshold (e.g., 3 consecutive successes)
- Action: Resume normal operation

**HALF-OPEN → OPEN:**
- Trigger: Any failure during probing
- Action: Reset timeout, continue rejecting

### Implementation Strategies

#### Count-Based Circuit Breaker

Tracks failure count in a sliding window:

```rust
struct CountBasedBreaker {
    failure_threshold: u32,
    consecutive_failures: u32,
    state: BreakerState,
}
```

**Pros:**
- Simple to understand and implement
- Fast state transitions

**Cons:**
- Doesn't account for traffic volume
- Can flip-flop under varying load

#### Time-Based Circuit Breaker

Tracks failures within a time window:

```rust
struct TimeBasedBreaker {
    window_size: Duration,
    failure_threshold: f64,  // percentage
    minimum_throughput: u32, // prevent tripping on low traffic
}
```

**Pros:**
- Accounts for traffic patterns
- Prevents flapping during low-traffic periods

**Cons:**
- Requires window management (ring buffer)
- More complex configuration

#### Hybrid Circuit Breaker

Combines both approaches for robustness:

```rust
struct HybridBreaker {
    consecutive_threshold: u32,  // fast trip on catastrophic failure
    error_percentage_threshold: f64,  // gradual trip on degradation
    time_window: Duration,
}
```

### Production Circuit Breaker Libraries

#### Polly (.NET)

Polly is the most comprehensive resilience library, providing:

**Strategies:**
- Retry: Configurable backoff strategies
- Circuit Breaker: Advanced state management
- Timeout: Execution time limits
- Bulkhead: Concurrency limiting
- Cache: Response caching
- Fallback: Degraded responses
- Hedging: Parallel execution
- Rate Limiter: Request throttling

**Pipeline Composition:**
```csharp
ResiliencePipeline pipeline = new ResiliencePipelineBuilder()
    .AddRetry(new RetryStrategyOptions())
    .AddCircuitBreaker(new CircuitBreakerStrategyOptions())
    .AddTimeout(TimeSpan.FromSeconds(10))
    .Build();
```

**Key Innovation:**
- Policy pipelines allow combining strategies
- Context passing between policies
- Rich telemetry integration

#### Resilience4j (Java)

Resilience4j provides a lightweight, functional approach:

**Modules:**
- `resilience4j-circuitbreaker`: Core circuit breaker
- `resilience4j-retry`: Retry logic
- `resilience4j-ratelimiter`: Rate limiting
- `resilience4j-bulkhead`: Concurrency limits
- `resilience4j-cache`: Caching
- `resilience4j-timelimiter`: Timeouts

**Functional Interface:**
```java
CircuitBreaker circuitBreaker = CircuitBreaker.ofDefaults("backendName");
Supplier<String> decorated = CircuitBreaker
    .decorateSupplier(circuitBreaker, backendService::doSomething);
```

**Advantages:**
- No dependencies except Vavr
- Functional programming model
- Metrics via Actuator or Micrometer

#### Cockatiel (TypeScript)

Modern TypeScript resilience library with cancellation support:

**Features:**
- CancellationToken integration
- Policy composition
- Type-safe fallbacks
- Event-based monitoring

```typescript
const retry = handleAll
  .retry()
  .exponentialBackoff(Duration.ofSeconds(1))
  .maxAttempts(3);

const breaker = handleAll
  .circuitBreaker({
    halfOpenAfter: Duration.ofSeconds(30),
    resetAfter: Duration.ofSeconds(60),
  });

const policy = Policy.wrap(retry, breaker);
```

### Advanced Resilience Patterns

#### Bulkhead Isolation

Prevents failure propagation by limiting concurrent operations per resource:

```rust
struct Bulkhead {
    max_concurrent: usize,
    max_waiters: usize,
    semaphore: Arc<Semaphore>,
}
```

**Types:**
- Thread-pool bulkheads: Isolate thread exhaustion
- Semaphore bulkheads: Limit concurrent calls

#### Hedging

Executes multiple parallel requests and returns the fastest response:

```rust
struct HedgingPolicy {
    max_parallel_requests: usize,
    hedging_delay: Duration,
    on_slow_response: Box<dyn Fn() -> Future<Output = Response>>,
}
```

**Use Cases:**
- Cross-region redundancy
- Hot cache vs cold storage
- Leader-follower database reads

#### Chaos Engineering Integration

Modern resilience systems integrate with chaos engineering:

- **Latency Injection:** Simulate slow dependencies
- **Error Injection:** Verify circuit breaker triggers
- **Abort Injection:** Test timeout handling

---

## Metrics Collection Systems

### Prometheus Model

Prometheus has become the de facto standard for metrics collection:

#### Metric Types

**Counter:**
- Monotonically increasing (resets on restart)
- Use cases: requests served, errors occurred
- Client behavior: `counter.inc()`, `counter.inc_by(n)`

**Gauge:**
- Can go up and down
- Use cases: current temperature, queue depth, memory usage
- Client behavior: `gauge.set(value)`, `gauge.inc()`, `gauge.dec()`

**Histogram:**
- Samples observations into buckets
- Use cases: request latency, response sizes
- Client behavior: `histogram.observe(value)`
- Automatically provides: count, sum, and bucket quantiles

**Summary:**
- Like histogram but calculates quantiles client-side
- Use cases: When exact quantiles needed and cardinality is high
- Note: Being deprecated in favor of native histograms

#### Label Cardinality

Critical consideration for metric design:

```
# BAD - High cardinality
http_requests_total{path="/users/12345", status="200"}

# GOOD - Bounded cardinality
http_requests_total{route="/users/:id", status="200"}
```

**Cardinality Limits:**
- Typical limit: 100-1000 unique label combinations per metric
- High cardinality causes:
  - Memory pressure on Prometheus
  - Slow queries
  - Cardinality explosion in histograms

#### Histogram Bucket Design

Default buckets are often inappropriate:

```rust
// Default buckets (optimized for web services in seconds):
// .005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10

// Custom buckets for API latency in milliseconds:
let histogram = register_histogram!(
    "api_request_duration_ms",
    "API request latency",
    vec![5.0, 10.0, 25.0, 50.0, 100.0, 250.0, 500.0, 1000.0, 2500.0, 5000.0]
);
```

### OpenTelemetry Metrics

OpenTelemetry provides a vendor-neutral standard for telemetry:

#### Architecture

```
+-------------+     +------------+     +-----------+     +-----------+
|  Instrument | --> |  Callback  | --> |  Aggreg.  | --> |  Export   |
|   (API)     |     | (Optional) |     |  (SDK)    |     |  (OTLP)   |
+-------------+     +------------+     +-----------+     +-----------+
```

#### Instrument Types

**Synchronous Instruments (called directly):**
- `Counter`: Always increasing
- `UpDownCounter`: Can increase or decrease
- `Histogram`: Records values to buckets
- `ObservableGauge`: Read at collection time

**Asynchronous Instruments (callback-based):**
- `ObservableCounter`: Periodically observed increasing values
- `ObservableUpDownCounter`: Periodically observed values
- `ObservableGauge`: Periodically observed instantaneous values

#### Views and Aggregation

OpenTelemetry introduces Views for metric customization:

```rust
// Configure aggregation without changing instrumentation
let view = View::builder()
    .with_name("custom_latency")
    .with_aggregation(Aggregation::ExplicitBucketHistogram {
        boundaries: vec![10.0, 50.0, 100.0],
        record_min_max: true,
    })
    .build();
```

### Metrics Export Patterns

#### Pull vs Push

**Pull Model (Prometheus):**
- Server scrapes metrics from endpoint
- Advantages:
  - Simple debugging (curl localhost:9090/metrics)
  - No buffer management needed
  - Works with serverless (on-demand)
- Disadvantages:
  - Firewall/NAT traversal
  - Short-lived job metrics may be missed

**Push Model (OpenTelemetry OTLP, StatsD):**
- Client pushes metrics to collector
- Advantages:
  - Works through firewalls
  - Better for batching and aggregation
  - Supports serverless better
- Disadvantages:
  - Requires buffering and retry logic
  - Potential for data loss

#### Export Batching

Batching reduces network overhead:

```rust
struct BatchConfig {
    max_queue_size: usize,      // 2048 default
    batch_size: usize,          // 512 default
    scheduled_delay: Duration,  // 1s default
    export_timeout: Duration,   // 30s default
}
```

#### Cardinality Aggregation

Pre-aggregation reduces backend load:

```rust
// Without pre-aggregation - High cardinality
for user in users {
    counter.add(1, &[KeyValue::new("user_id", user.id)]);
}

// With pre-aggregation - Low cardinality
let total = users.len();
counter.add(total as u64, &[KeyValue::new("aggregate", "true")]);
```

---

## Observability Standards

### OpenTelemetry Specification

OpenTelemetry provides a unified standard for traces, metrics, and logs:

#### Signal Correlation

The holy grail of observability: connecting signals:

```
Trace: [Request Start] --> [Database Query] --> [Cache Lookup] --> [Response]
        |                    |                    |                  |
        v                    v                    v                  v
Log:   "Starting"          "Query: SELECT"      "Cache miss"      "Completed"
Metric: requests_total      db_query_duration    cache_hit_ratio   response_latency
```

**Correlation Mechanisms:**
- TraceID in logs
- Span context in metrics exemplars
- Baggage for request-scoped attributes

#### Semantic Conventions

Standardized attribute names for consistency:

**HTTP Server:**
- `http.request.method`: GET, POST, etc.
- `http.route`: /users/:id
- `http.response.status_code`: 200, 404, etc.
- `server.address`: server domain/IP

**HTTP Client:**
- `http.request.method`
- `http.response.status_code`
- `server.address`: target server
- `url.full`: full request URL

**System:**
- `service.name`, `service.version`, `service.namespace`
- `deployment.environment`: production, staging
- `host.name`, `host.arch`

### Distributed Tracing

#### Trace Context Propagation

W3C Trace Context standard:

```
traceparent: 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01
             ^^ ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ^^^^^^^^^^^^^^^^ ^^
             |  |                                  |                |
             |  |                                  |                flags
             |  |                                  span_id
             |  trace_id
             version
```

**Propagation Formats:**
- W3C Trace Context (header: `traceparent`)
- B3 (Zipkin): `X-B3-TraceId`, `X-B3-SpanId`
- Jaeger: `uber-trace-id`
- AWS X-Ray: `X-Amzn-Trace-Id`

#### Sampling Strategies

**Head-Based Sampling:**
- Decision made at trace start
- Consistent across all services
- Risk of missing rare events

```rust
// 1% sampling
Sampler::TraceIdRatioBased(0.01)
```

**Tail-Based Sampling:**
- Decision made after trace completes
- Can sample based on properties (errors, latency)
- Requires buffering

```rust
// Sample errors and high latency
TailBasedSampler::builder()
    .rule(|trace| trace.has_errors() || trace.duration() > Duration::from_secs(1))
    .build()
```

### Logging Integration

#### Structured Logging

JSON-structured logs enable automated processing:

```json
{
  "timestamp": "2026-04-04T12:00:00.000Z",
  "level": "ERROR",
  "message": "Database connection failed",
  "trace_id": "0af7651916cd43dd8448eb211c80319c",
  "span_id": "b7ad6b7169203331",
  "attributes": {
    "db.system": "postgresql",
    "db.connection_string": "postgres://...",
    "error.type": "ConnectionRefused"
  }
}
```

#### Log Levels in Production

Recommended production configuration:

| Environment | Default Level | Third-Party |
|-------------|---------------|-------------|
| Production | INFO | WARN |
| Staging | DEBUG | INFO |
| Development | TRACE | DEBUG |

---

## Async Runtime Considerations

### Tokio Architecture

Tokio is the dominant async runtime in Rust:

#### Runtime Flavors

**Current-Thread Scheduler:**
- Single OS thread
- No `Send` requirement for tasks
- Lower latency for I/O bound work

```rust
let runtime = tokio::runtime::Builder::new_current_thread()
    .enable_all()
    .build()?;
```

**Multi-Thread Scheduler (Work-Stealing):**
- Multiple OS threads (default: num_cpus)
- Work-stealing for load balancing
- Better for CPU-bound work

```rust
let runtime = tokio::runtime::Builder::new_multi_thread()
    .worker_threads(4)
    .enable_all()
    .build()?;
```

#### Task Scheduling

**Spawning Tasks:**
```rust
// Fire-and-forget
 tokio::spawn(async { /* background work */ });

// With handle for awaiting/completion
t let handle = tokio::spawn(async { 42 });
let result = handle.await?;
```

**Task Priorities:**
Tokio doesn't have explicit priorities, but use:
- Separate runtime instances for different priorities
- `tokio::task::spawn_blocking` for CPU work

### Async Health Check Patterns

#### Concurrent Health Checks

Check multiple dependencies in parallel:

```rust
async fn check_all(deps: &[Dependency]) -> Vec<HealthResult> {
    let checks = deps.iter().map(|d| check_dependency(d));
    futures::future::join_all(checks).await
}
```

#### Timeouts

Always use timeouts for health checks:

```rust
async fn check_with_timeout(dep: &Dependency) -> HealthResult {
    match timeout(Duration::from_secs(5), check_dependency(dep)).await {
        Ok(result) => result,
        Err(_) => HealthResult::timeout(),
    }
}
```

#### Cancellation Safety

Health checks must be cancellation-safe:

```rust
// BAD - May leave resources in bad state
async fn bad_check() {
    let conn = pool.get().await; // If cancelled here, connection leaked
    conn.query("SELECT 1").await;
}

// GOOD - Uses scope guard pattern
async fn good_check() {
    let mut conn = pool.get().await;
    scopeguard::defer! { pool.return_connection(conn); }
    conn.query("SELECT 1").await;
}
```

### Resource Management

#### Backpressure

Prevent overload through backpressure:

```rust
// Bounded channel provides backpressure
let (tx, rx) = tokio::sync::mpsc::channel(100);

// Sender blocks when full (or use try_send for dropping)
tx.send(item).await?;
```

#### Semaphores for Concurrency Limiting

```rust
// Limit concurrent health checks
let semaphore = Arc::new(Semaphore::new(10));

async fn limited_check(semaphore: &Semaphore) -> Result<()> {
    let permit = semaphore.acquire().await?;
    // ... check ...
    drop(permit); // Explicit for clarity
    Ok(())
}
```

---

## Alerting & SLO Management

### SRE Principles

Google's Site Reliability Engineering defines modern alerting:

#### SLIs, SLOs, SLAs

**Service Level Indicator (SLI):**
- A quantitative measure of service quality
- Examples: availability, latency, error rate

**Service Level Objective (SLO):**
- Target value for SLI over time
- Example: 99.9% availability over 30 days

**Service Level Agreement (SLA):**
- Business contract based on SLO
- Financial penalties for violation

#### Error Budgets

Error budget = 100% - SLO (e.g., 0.1% for 99.9%)

**Usage:**
- Feature freeze when budget exhausted
- Prioritize reliability work
- Balance velocity vs stability

### Alerting Strategies

#### Symptom-Based vs Cause-Based

**Symptom-Based (Preferred):**
- Alerts on user-observable issues
- Examples: High error rate, elevated latency
- Lower false positive rate

**Cause-Based:**
- Alerts on potential problems
- Examples: Disk full, CPU high
- Higher false positive rate

#### Multiwindow, Multi-Burn-Rate Alerts

For SLO: 99.9% over 30 days (43,200 minutes error budget = 43.2 minutes)

| Burn Rate | Lookback | Alert After | Error Budget Consumed |
|-----------|----------|-------------|----------------------|
| 2x | 1 hour | 12 minutes | 0.2% |
| 2x | 6 hours | 1 hour 36 minutes | 1.2% |
| 1x | 3 days | 3 days | 10% |

#### Alert Severity Levels

| Severity | Response Time | Escalation | Example |
|----------|---------------|------------|---------|
| P0 (Critical) | 5 minutes | Page immediately | Service down, revenue impact |
| P1 (High) | 30 minutes | Page during business hours | Degraded performance |
| P2 (Medium) | 4 hours | Ticket only | Capacity warning |
| P3 (Low) | 24 hours | Next sprint | Non-urgent issue |

---

## Distributed Systems Health Checking

### The False Positive Problem

In large systems, health checks can cause more problems than they solve:

**Scenario:**
- 1000 services, each checking 10 dependencies
- 10-second check interval
- 600,000 health checks per minute
- 1% false positive rate = 6,000 unnecessary failovers per minute

### Gossip Protocols

For large clusters, gossip-based health detection:

**SWIM Protocol:**
- Soft-state failure detection
- Suspicion mechanism before declaring failure
- Constant bandwidth per node (O(1))

**Implementation Pattern:**
```rust
struct SwimState {
    members: HashMap<NodeId, MemberState>,
    incarnation: u64, // Monotonic counter for partition recovery
}
```

### Health Check Aggregation

In microservices, health check aggregation prevents thundering herds:

```
Client --> Edge Gateway --> Aggregate Health Check --> Services
                         (caches for 5 seconds)
```

### Consensus-Based Health

For critical systems, use consensus (Raft, Paxos) for health decisions:

**Benefits:**
- Survives network partitions
- No split-brain scenarios

**Costs:**
- Higher latency
- More complex

---

## Latency Profiling Techniques

### Percentile Analysis

Averages lie. Use percentiles:

| Metric | What It Shows | Use Case |
|--------|--------------|----------|
| p50 | Median | Typical user experience |
| p95 | 95th percentile | SLA targeting |
| p99 | 99th percentile | Worst-case outliers |
| p99.9 | 99.9th percentile | System capacity planning |

### Coordinated Omission

The "coordinated omission problem" - not measuring the time spent waiting:

**Problem:**
```
Time:  0    100ms  200ms  300ms
       |      |      |      |
       v      v      v      v
Req1: [====] (100ms, recorded)
Req2:      [====] (100ms, recorded)
Req3:           [==========] (200ms, but shows as 100ms!)
       ^^^^^^^^
       This delay not measured
```

**Solution:** Use latency histograms from start time, not service time.

### Request Coalescing

Combine identical concurrent requests:

```rust
struct Coalescer<T> {
    pending: HashMap<RequestKey, Vec<oneshot::Sender<T>>>,
}

impl<T> Coalescer<T> {
    async fn request(&mut self, key: RequestKey) -> T {
        let (tx, rx) = oneshot::channel();
        if let Some(waiters) = self.pending.get_mut(&key) {
            // Join existing request
            waiters.push(tx);
        } else {
            // Start new request
            self.pending.insert(key.clone(), vec![tx]);
            spawn_backend_request(key);
        }
        rx.await.unwrap()
    }
}
```

---

## Production Case Studies

### Netflix: Zuul and Ribbon

Netflix pioneered many resilience patterns:

**Zuul (API Gateway):**
- Circuit breaker integration
- Adaptive concurrency limits (automatically adjusts based on latency)
- Canary routing

**Ribbon (Client-Side Load Balancer):**
- Server health checking
- Zone-aware load balancing
- Retry policies

**Key Insight:** Adaptive concurrency limits based on Little's Law:
```
concurrency = latency * throughput
```

### Google: SRE Practices

Google's SRE book documents their approach:

**Borgmon (Precursor to Prometheus):**
- Time-series monitoring
- Alerting rules in configuration
- PromQL-like query language

**Dapper (Distributed Tracing):**
- Low overhead (~0.01%)
- Automatic instrumentation
- Trace analysis pipeline

**Lessons:**
- Separate critical path from background monitoring
- Prefer dashboards to alerts when possible
- Practice chaos engineering regularly

### AWS: Elastic Load Balancing

ELB health check evolution:

**Classic ELB:**
- Simple TCP/HTTP checks
- Fixed thresholds

**Application Load Balancer:**
- Content-based routing
- Advanced health checks
- gRPC support

**Key Innovation:** Health checks can target specific ports (separate from traffic port)

### Meta: Gorilla Time Series Database

Meta's approach to metrics at scale:

**Gorilla Design:**
- In-memory time series database
- 10x compression using XOR delta encoding
- 65,536 samples per time series

**Results:**
- 2 billion time series
- 500 million data points per minute
- Query latency: < 1ms for recent data

---

## Bibliography

### Books

1. **Nygard, Michael T.** *Release It! Design and Deploy Production-Ready Software.* 2nd ed., Pragmatic Bookshelf, 2018.
   - Chapter 4: Stability Patterns (Circuit Breaker, Bulkhead, Timeout)

2. **Beyer, Betsy, et al.** *Site Reliability Engineering: How Google Runs Production Systems.* O'Reilly Media, 2016.
   - Chapter 2: The Production Environment at Google
   - Chapter 6: Monitoring Distributed Systems

3. **Beyer, Betsy, et al.** *The Site Reliability Workbook: Practical Ways to Implement SRE.* O'Reilly Media, 2018.
   - Implementing SLOs chapter

4. **Richardson, Chris.** *Microservices Patterns: With examples in Java.* Manning Publications, 2018.
   - Chapter 11: Developing production-ready services (health checks, metrics)

### Papers

1. **Fowler, Martin.** "Circuit Breaker." *martinfowler.com*, 2014.
   https://martinfowler.com/bliki/CircuitBreaker.html

2. **Sambasivan, Raja R., et al.** "The Mystery of the Hanging Query." *ACM SIGMETRICS*, 2016.
   - Request coalescing analysis

3. **Sigelman, Benjamin H., et al.** "Dapper, a Large-Scale Distributed Systems Tracing Infrastructure." *Google Technical Report*, 2010.

4. **Sathyanarayanan, M., et al.** "Gorilla: A Fast, Scalable, In-Memory Time Series Database." *VLDB*, 2016.

### Standards

1. **W3C.** "Trace Context." W3C Recommendation, 2021.
   https://www.w3.org/TR/trace-context/

2. **OpenTelemetry Project.** "OpenTelemetry Specification." 
   https://opentelemetry.io/docs/specs/otel/

3. **Prometheus Project.** "Prometheus Best Practices."
   https://prometheus.io/docs/practices/

### Open Source Projects

1. **Polly** (.NET Resilience Library)
   https://github.com/App-vNext/Polly

2. **Resilience4j** (Java Resilience Library)
   https://github.com/resilience4j/resilience4j

3. **OpenTelemetry Rust**
   https://github.com/open-telemetry/opentelemetry-rust

4. **Tokio** (Rust Async Runtime)
   https://github.com/tokio-rs/tokio

### Conference Talks

1. **Vora, Vivek.** "Adaptive Concurrency Control at Netflix." *QCon*, 2019.

2. **Taschner, Fabian.** "Resilient microservices with Polly." *NDC Oslo*, 2023.

3. **Fong, Luke, et al.** "How Meta Monitors 2 Billion+ Time Series at Scale." *SREcon*, 2022.

---

## Appendices

### Appendix A: Health Check Checklist

**Endpoint Design:**
- [ ] Separate liveness and readiness endpoints
- [ ] Return appropriate HTTP status codes (200, 503)
- [ ] Include response time in body
- [ ] Version the health check format

**Implementation:**
- [ ] Check critical dependencies only in readiness
- [ ] Use circuit breakers for external checks
- [ ] Implement timeouts on all checks
- [ ] Cache results to prevent thundering herd

**Operations:**
- [ ] Document health check semantics
- [ ] Configure appropriate intervals and thresholds
- [ ] Monitor health check latency
- [ ] Alert on health check failures

### Appendix B: Metrics Naming Conventions

**Format:** `{namespace}_{metric}_{unit}`

**Examples:**
```
router_requests_total          # Counter
router_request_duration_ms     # Histogram
router_active_connections      # Gauge
router_check_failures_total    # Counter
```

**Labels (dimensions):**
```
route="/api/v1/users"
method="GET"
status="200"
error="timeout"
```

### Appendix C: Circuit Breaker Configuration Guide

**Conservative (Financial Systems):**
```
failure_threshold: 5
error_percentage: 50%
time_window: 60s
timeout: 60s
half_open_requests: 1
success_threshold: 3
```

**Aggressive (Consumer Web):**
```
failure_threshold: 10
error_percentage: 75%
time_window: 30s
timeout: 30s
half_open_requests: 3
success_threshold: 2
```

**Adaptive (Using Little's Law):**
```
max_concurrency = latency_p99 * throughput_target
failure_threshold = max_concurrency * 0.5
```

---

## Emerging Technologies

### eBPF-Based Monitoring

eBPF enables kernel-level observability without instrumentation:

**Capabilities:**
- Zero-instrumentation HTTP monitoring
- Kernel-level latency measurement
- Automatic protocol detection

**Limitations:**
- Linux-only (kernel 4.18+)
- Requires CAP_BPF or root
- Learning curve for development

**Projects:**
- **Pixie:** eBPF-based observability for Kubernetes
- **Cilium:** eBPF networking with built-in metrics
- **Hubble:** Network and service observability

### WebAssembly (Wasm) for Isolation

Wasm provides sandboxed execution for health checks:

**Benefits:**
- Deterministic execution time
- Memory safety
- Fast startup

**Use Cases:**
- Custom health check logic
- Safe execution of user-provided checks
- Plugin architecture

### Rust Async Ecosystem Evolution

**Current State:**
- Tokio dominates with 85%+ market share
- Embassy gaining traction in embedded
- Glommio for io_uring on Linux

**Future Directions:**
- Native async traits (stabilized in Rust 1.75)
- Async fn in traits without async-trait
- Poll-based optimizations

### Structured Logging Standards

**OpenTelemetry Logs:**
- Unifying logs with traces and metrics
- Semantic conventions for common patterns
- Correlation through TraceId/SpanId

**Loki Alternative:**
- Label-based indexing
- Lower resource requirements than ELK
- Native Grafana integration

---

## Implementation Patterns

### The Sidecar Pattern

Deploying the monitor as a sidecar container:

```yaml
apiVersion: v1
kind: Pod
spec:
  containers:
    - name: application
      image: myapp:v1
    - name: monitor
      image: router-monitor:v2
      volumeMounts:
        - name: shared-socket
          mountPath: /var/run/monitor
```

**Benefits:**
- Co-located with application
- Shared network namespace
- Independent scaling

**Drawbacks:**
- Resource overhead
- Deployment complexity
- Data duplication

### The DaemonSet Pattern

Single monitor per node:

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: router-monitor
spec:
  template:
    spec:
      containers:
        - name: monitor
          image: router-monitor:v2
          hostNetwork: true
```

**Benefits:**
- Node-level visibility
- Lower per-pod overhead
- Shared configuration

**Drawbacks:**
- Requires hostNetwork or complex networking
- Single point of failure per node
- No application co-location

### The Centralized Pattern

Dedicated monitoring cluster:

```
┌─────────────┐     ┌─────────────────┐     ┌─────────────┐
│  Service A  │────▶│                 │     │             │
│  (us-east)  │     │    Central      │────▶│  Prometheus │
├─────────────┤     │    Monitor      │     │             │
│  Service B  │────▶│                 │     └─────────────┘
│  (us-west)  │     │   (aggregation) │
└─────────────┘     └─────────────────┘
```

**Benefits:**
- Centralized configuration
- Easier management
- Cross-region aggregation

**Drawbacks:**
- Network dependency
- Higher latency for checks
- Single point of failure

### The Agent Pattern

Distributed agents with centralized collector:

```
┌─────────┐  ┌─────────┐  ┌─────────┐
│ Agent 1 │  │ Agent 2 │  │ Agent N │
└────┬────┘  └────┬────┘  └────┬────┘
     │            │            │
     └────────────┼────────────┘
                  ▼
         ┌────────────────┐
         │   Collector    │
         │  (aggregation)   │
         └───────┬────────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
┌──────────────┐  ┌──────────────┐
│ Prometheus   │  │   Grafana    │
└──────────────┘  └──────────────┘
```

**Benefits:**
- Best of both worlds
- Local execution, global view
- Scalable architecture

**Drawbacks:**
- Complexity
- Infrastructure overhead
- Operational burden

---

## Comparative Analysis

### Health Check Libraries

| Library | Language | Circuit Breaker | Retry | Metrics | Maturity |
|---------|----------|-----------------|-------|---------|----------|
| **Polly** | C# | Excellent | Excellent | Good | Very High |
| **Resilience4j** | Java | Good | Good | Good | High |
| **Cockatiel** | TypeScript | Good | Good | Basic | Medium |
| **Hystrix** | Java | Good | Basic | Good | Deprecated |
| **Failfast** | Python | Basic | Basic | None | Low |
| **Resilience** | Rust | Good | Basic | Basic | Medium |

### Observability Backends

| Backend | Protocol | Scaling | Cost | Query Lang | Alerting |
|---------|----------|---------|------|------------|----------|
| **Prometheus** | Pull | Vertical | Low | PromQL | Good |
| **Thanos** | Pull | Horizontal | Medium | PromQL | Good |
| **Cortex** | Push/Pull | Horizontal | Medium | PromQL | Good |
| **Datadog** | Agent | SaaS | High | Custom | Excellent |
| **New Relic** | Agent | SaaS | High | NRQL | Excellent |
| **Grafana Cloud** | OTLP | SaaS | Medium | PromQL/LogQL | Good |
| **AWS CloudWatch** | Push | AWS | Medium | CloudWatch | Basic |

### Async Runtimes

| Runtime | Scheduler | Platform | Overhead | Ecosystem |
|---------|-----------|----------|----------|-----------|
| **Tokio** | Work-stealing | Cross-platform | Medium | Excellent |
| **async-std** | Work-stealing | Cross-platform | Medium | Good |
| **smol** | Single-queue | Cross-platform | Low | Basic |
| **glommio** | io_uring | Linux only | Low | Basic |
| **embassy** | Executor | Embedded | Very Low | Basic |

---

## Deep Dive: Circuit Breaker Mathematics

### Failure Rate Calculation

The circuit breaker tracks failure rate over a sliding window:

```
failure_rate = failures / (successes + failures)

Example over 60-second window:
- successes: 580
- failures: 20
- failure_rate: 20/600 = 0.033 (3.3%)
```

### Exponential Moving Average (EMA)

For smoother failure rate tracking:

```
ema_t = α * current + (1 - α) * ema_{t-1}

Where α (smoothing factor) typically 0.1 - 0.3
```

**Benefits:**
- More stable than raw counts
- Adapts to changing conditions
- Reduces noise

### Adaptive Thresholds

Thresholds that adjust based on traffic:

```python
def adaptive_threshold(baseline_error_rate, current_traffic):
    # Higher traffic = more lenient threshold
    traffic_factor = min(current_traffic / baseline_traffic, 2.0)
    
    # Base threshold increases with traffic
    return baseline_error_rate * (1 + 0.5 * (traffic_factor - 1))
```

---

## Deep Dive: Histogram Bucket Selection

### The Bucket Problem

Choosing histogram buckets is critical for accuracy:

**Too Few Buckets:**
- Lose precision
- Can't calculate accurate percentiles

**Too Many Buckets:**
- High cardinality
- Memory overhead
- Slow queries

### Apdex Buckets

Application Performance Index standard:

```
satisfied: 0-500ms
tolerating: 500-2000ms
frustrated: >2000ms

Apdex = (satisfied + 0.5 * tolerating) / total
```

### SRE-Style Buckets

Google SRE recommendations:

```
Latency buckets for web services:
0.001, 0.005, 0.015, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10
```

### Custom Bucket Strategies

**Logarithmic:**
```rust
let buckets: Vec<f64> = (1..=20)
    .map(|i| 10f64.powf(i as f64 / 4.0))
    .collect();
// 1.78, 3.16, 5.62, 10.0, 17.78, ...
```

**Geometric:**
```rust
let buckets: Vec<f64> = std::iter::successors(Some(1.0), |n| Some(n * 2.0))
    .take(10)
    .collect();
// 1, 2, 4, 8, 16, 32, 64, 128, 256, 512
```

---

## Monitoring Anti-Patterns

### The "Metrilution" Problem

Too many metrics, not enough insight:

**Symptoms:**
- Dashboards with 50+ graphs
- Alerts on every metric
- No one knows what they all mean

**Solution:**
- Focus on SLIs that matter
- Use RED method (Rate, Errors, Duration)
- Regular metric audits

### Alert Fatigue

When everything alerts, nothing alerts:

**Symptoms:**
- On-call ignores alerts
- Pages for non-issues
- Recovery without action

**Solution:**
- Symptom-based alerting
- Clear severity levels
- Runbooks for every alert

### The "Average" Lie

Using averages hides problems:

**Problem:**
```
Average latency: 50ms
Reality:
- 80% of requests: 10ms
- 19% of requests: 100ms
- 1% of requests: 5000ms
```

**Solution:**
- Always use percentiles (p50, p95, p99)
- Histograms over averages
- Tail latency awareness

---

## Glossary

**Circuit Breaker:** A pattern that prevents cascading failures by temporarily rejecting requests to failing services.

**eBPF:** Extended Berkeley Packet Filter - technology for running sandboxed programs in the Linux kernel.

**Exemplar:** A specific trace associated with a metric observation, enabling correlation.

**Health Check:** An operation to determine if a service is operational.

**Histogram:** A metric type that samples observations into buckets for distribution analysis.

**Label (Prometheus):** A dimension of a metric (e.g., route name, status code).

**Latency:** The time taken to process a request.

**Little's Law:** L = λ × W (concurrency = throughput × latency)

**Observability:** The ability to understand a system's internal state from its external outputs.

**OpenTelemetry:** A vendor-neutral standard for telemetry (metrics, traces, logs).

**Percentile:** A measure used in statistics indicating the value below which a given percentage of observations fall.

**PromQL:** Prometheus Query Language for time-series data.

**RED Method:** Rate, Errors, Duration - minimal metrics for service health.

**SLO:** Service Level Objective - target reliability for a service.

**USE Method:** Utilization, Saturation, Errors - resource analysis method.

---

## Additional References

### RFCs and Standards

1. **RFC 7231** - HTTP/1.1 Semantics and Content (status codes)
2. **RFC 7807** - Problem Details for HTTP APIs
3. **RFC 8949** - CBOR (for compact metric encoding)

### Conference Recordings

1. **"How to Monitor Kubernetes"** - KubeCon EU 2025
2. **"SRE at Google Scale"** - SREcon 2024
3. **"Resilience Patterns in Production"** - QCon 2024

### Additional Reading

1. **Honeycomb Blog:** "Observability - A Manifesto"
2. **Lightstep Blog:** "Distributed Tracing Best Practices"
3. **Prometheus Blog:** "Cardinality Explained"

---

*End of Document*

