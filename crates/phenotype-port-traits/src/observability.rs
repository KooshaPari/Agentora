//! Observability traits

/// Counter metrics trait
pub trait CounterMetrics: Send + Sync {
    /// Increment counter
    fn increment(&self, name: &str, value: u64);
}

/// Metrics hook trait
pub trait MetricsHook: Send + Sync {
    /// Record metric
    fn record(&self, name: &str, value: f64);
}

/// No-op metrics implementation
#[derive(Debug, Clone, Copy, Default)]
pub struct NoOpMetrics;

impl CounterMetrics for NoOpMetrics {
    fn increment(&self, _name: &str, _value: u64) {}
}

impl MetricsHook for NoOpMetrics {
    fn record(&self, _name: &str, _value: f64) {}
}
