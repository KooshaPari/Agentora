//! Counters and histograms for AgilePlus operational metrics.
//!
//! Instruments are stored as a [`MetricsRecorder`] and exported via the
//! OpenTelemetry Meter.  A [`MetricSnapshot`] type captures point-in-time
//! values for persistence to SQLite.

use std::{
    sync::atomic::{AtomicU64, Ordering},
    time::Duration,
};

use chrono::{DateTime, Utc};
use opentelemetry::{
    KeyValue,
    metrics::{Counter, Gauge, Histogram, Meter},
};

// ---------------------------------------------------------------------------
// Instruments
// ---------------------------------------------------------------------------

/// Holds the OpenTelemetry metric instruments for AgilePlus.
///
/// Not `Clone`: includes `AtomicU64` snapshot fields; share via `Arc` if needed.
pub struct MetricsRecorder {
    agent_runs: Counter<u64>,
    review_cycles: Counter<u64>,
    command_duration: Histogram<f64>,
    /// Internal delta tracking for snapshot (monotonic).
    agent_runs_total: AtomicU64,
    review_cycles_total: AtomicU64,
    /// Last snapshot baseline (for delta calculation).
    agent_runs_snapshot: AtomicU64,
    review_cycles_snapshot: AtomicU64,
    // T093: domain-level instruments
    events_processed: Counter<u64>,
    sync_duration_ms: Histogram<f64>,
    cache_hit_rate: Gauge<f64>,
    api_request_duration_ms: Histogram<f64>,
    active_features: Gauge<u64>,
}

impl MetricsRecorder {
    /// Construct using a configured `Meter`.
    pub fn new(meter: &Meter) -> Self {
        let agent_runs = meter
            .u64_counter("agileplus.agent.runs")
            .with_description("Number of agent invocations")
            .build();

        let review_cycles = meter
            .u64_counter("agileplus.review.cycles")
            .with_description("Number of review-fix loop iterations")
            .build();

        let command_duration = meter
            .f64_histogram("agileplus.command.duration_ms")
            .with_description("CLI command execution duration in milliseconds")
            .with_boundaries(vec![
                10.0, 50.0, 100.0, 500.0, 1_000.0, 5_000.0, 30_000.0, 60_000.0,
            ])
            .build();

        // T093: domain-level instruments
        let events_processed = meter
            .u64_counter("events_processed")
            .with_description("Total events appended to the event store")
            .build();

        let sync_duration_ms = meter
            .f64_histogram("sync_duration_ms")
            .with_description("Duration in milliseconds for sync operations")
            .with_boundaries(vec![1.0, 5.0, 10.0, 50.0, 100.0, 500.0, 1_000.0, 5_000.0])
            .build();

        let cache_hit_rate = meter
            .f64_gauge("cache_hit_rate")
            .with_description("Cache hit/miss ratio (0.0 to 1.0)")
            .build();

        let api_request_duration_ms = meter
            .f64_histogram("api_request_duration_ms")
            .with_description("API request latency in milliseconds")
            .with_boundaries(vec![1.0, 5.0, 10.0, 50.0, 100.0, 250.0, 500.0, 1_000.0])
            .build();

        let active_features = meter
            .u64_gauge("active_features")
            .with_description("Count of non-terminal features")
            .build();

        Self {
            agent_runs,
            review_cycles,
            command_duration,
            agent_runs_total: AtomicU64::new(0),
            review_cycles_total: AtomicU64::new(0),
            agent_runs_snapshot: AtomicU64::new(0),
            review_cycles_snapshot: AtomicU64::new(0),
            events_processed,
            sync_duration_ms,
            cache_hit_rate,
            api_request_duration_ms,
            active_features,
        }
    }

    // -----------------------------------------------------------------------
    // Recording methods
    // -----------------------------------------------------------------------

    /// Increment the `agileplus.agent.runs` counter.
    pub fn record_agent_run(&self, feature_slug: &str, wp_id: &str, agent_type: &str) {
        let labels = [
            KeyValue::new("feature_slug", feature_slug.to_owned()),
            KeyValue::new("wp_id", wp_id.to_owned()),
            KeyValue::new("agent_type", agent_type.to_owned()),
        ];
        self.agent_runs.add(1, &labels);
        self.agent_runs_total.fetch_add(1, Ordering::Relaxed);
    }

    /// Increment the `agileplus.review.cycles` counter.
    pub fn record_review_cycle(&self, feature_slug: &str, wp_id: &str, cycle: u32) {
        let labels = [
            KeyValue::new("feature_slug", feature_slug.to_owned()),
            KeyValue::new("wp_id", wp_id.to_owned()),
            KeyValue::new("cycle", cycle as i64),
        ];
        self.review_cycles.add(1, &labels);
        self.review_cycles_total.fetch_add(1, Ordering::Relaxed);
    }

    // -----------------------------------------------------------------------
    // T093: Domain-level instruments
    // -----------------------------------------------------------------------

    /// Increment `events_processed` counter.
    pub fn record_event_processed(&self, labels: &[KeyValue]) {
        self.events_processed.add(1, labels);
    }

    /// Record a sync operation duration in milliseconds.
    pub fn record_sync_duration(&self, duration_ms: f64, labels: &[KeyValue]) {
        self.sync_duration_ms.record(duration_ms, labels);
    }

    /// Set the cache hit rate (0.0 to 1.0).
    pub fn set_cache_hit_rate(&self, ratio: f64, labels: &[KeyValue]) {
        self.cache_hit_rate.record(ratio, labels);
    }

    /// Record an API request duration in milliseconds.
    pub fn record_api_request_duration(&self, duration_ms: f64, labels: &[KeyValue]) {
        self.api_request_duration_ms.record(duration_ms, labels);
    }

    /// Set the count of active (non-terminal) features.
    pub fn set_active_features(&self, count: u64, labels: &[KeyValue]) {
        self.active_features.record(count, labels);
    }

    /// Record an observation in the `agileplus.command.duration_ms` histogram.
    pub fn record_command_duration(
        &self,
        command: &str,
        feature_slug: Option<&str>,
        duration: Duration,
    ) {
        let ms = duration.as_secs_f64() * 1_000.0;
        let mut labels = vec![KeyValue::new("command", command.to_owned())];
        if let Some(slug) = feature_slug {
            labels.push(KeyValue::new("feature_slug", slug.to_owned()));
        }
        self.command_duration.record(ms, &labels);
    }

    // -----------------------------------------------------------------------
    // Snapshot
    // -----------------------------------------------------------------------

    /// Capture a point-in-time snapshot with delta values since the last call.
    ///
    /// Callers persist this to SQLite via `StoragePort`.
    pub fn collect_snapshot(&self, command: &str, duration: Duration) -> MetricSnapshot {
        let total_runs = self.agent_runs_total.load(Ordering::Relaxed);
        let total_cycles = self.review_cycles_total.load(Ordering::Relaxed);

        let prev_runs = self.agent_runs_snapshot.swap(total_runs, Ordering::Relaxed);
        let prev_cycles = self
            .review_cycles_snapshot
            .swap(total_cycles, Ordering::Relaxed);

        MetricSnapshot {
            command: command.to_owned(),
            duration_ms: duration.as_millis() as u64,
            agent_runs: total_runs.saturating_sub(prev_runs),
            review_cycles: total_cycles.saturating_sub(prev_cycles),
            timestamp: Utc::now(),
        }
    }

    /// Reset internal counters — intended for test isolation only.
    pub fn reset(&self) {
        self.agent_runs_total.store(0, Ordering::Relaxed);
        self.review_cycles_total.store(0, Ordering::Relaxed);
        self.agent_runs_snapshot.store(0, Ordering::Relaxed);
        self.review_cycles_snapshot.store(0, Ordering::Relaxed);
    }
}

// ---------------------------------------------------------------------------
// T093: Standalone init helper
// ---------------------------------------------------------------------------

/// Initialise all domain metrics instruments on the given meter.
///
/// This registers the instruments so that the OTel SDK knows about them even
/// before any observations are recorded.  Callers that use [`MetricsRecorder`]
/// directly do not need to call this function — it is provided as a
/// convenience for integrations that hold only a `&Meter` reference.
pub fn init_metrics(meter: &Meter) {
    let _ = meter.u64_counter("events_processed").build();
    let _ = meter.f64_histogram("sync_duration_ms").build();
    let _ = meter.f64_gauge("cache_hit_rate").build();
    let _ = meter.f64_histogram("api_request_duration_ms").build();
    let _ = meter.u64_gauge("active_features").build();
}

// ---------------------------------------------------------------------------
// MetricSnapshot
// ---------------------------------------------------------------------------

/// Point-in-time metric values for SQLite persistence.
#[derive(Debug, Clone)]
pub struct MetricSnapshot {
    pub command: String,
    pub duration_ms: u64,
    pub agent_runs: u64,
    pub review_cycles: u64,
    pub timestamp: DateTime<Utc>,
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use opentelemetry::metrics::MeterProvider as _;
    use opentelemetry_sdk::metrics::SdkMeterProvider;

    fn test_recorder() -> MetricsRecorder {
        let provider = SdkMeterProvider::builder().build();
        let meter = provider.meter("agileplus-test");
        MetricsRecorder::new(&meter)
    }

    #[test]
    fn counter_increments() {
        let rec = test_recorder();
        rec.record_agent_run("feature-1", "WP10", "claude-code");
        rec.record_agent_run("feature-1", "WP10", "claude-code");
        assert_eq!(rec.agent_runs_total.load(Ordering::Relaxed), 2);
    }

    #[test]
    fn snapshot_delta() {
        let rec = test_recorder();
        rec.record_agent_run("f", "WP10", "codex");
        rec.record_review_cycle("f", "WP10", 1);
        let snap = rec.collect_snapshot("implement", Duration::from_millis(100));
        assert_eq!(snap.agent_runs, 1);
        assert_eq!(snap.review_cycles, 1);

        // Second snapshot should have delta=0 since no new events.
        let snap2 = rec.collect_snapshot("implement", Duration::from_millis(50));
        assert_eq!(snap2.agent_runs, 0);
        assert_eq!(snap2.review_cycles, 0);
    }

    #[test]
    fn reset_clears_state() {
        let rec = test_recorder();
        rec.record_agent_run("f", "WP10", "codex");
        rec.reset();
        assert_eq!(rec.agent_runs_total.load(Ordering::Relaxed), 0);
    }

    #[test]
    fn histogram_records_without_panic() {
        let rec = test_recorder();
        rec.record_command_duration("implement", Some("001-sde"), Duration::from_millis(42));
        // No assertion — just verify no panic.
    }

    // T093: domain instrument tests
    #[test]
    fn events_processed_counter_does_not_panic() {
        let rec = test_recorder();
        rec.record_event_processed(&[KeyValue::new("source", "git")]);
        rec.record_event_processed(&[]);
    }

    #[test]
    fn sync_duration_histogram_does_not_panic() {
        let rec = test_recorder();
        rec.record_sync_duration(42.5, &[KeyValue::new("sync_type", "full")]);
    }

    #[test]
    fn cache_hit_rate_gauge_does_not_panic() {
        let rec = test_recorder();
        rec.set_cache_hit_rate(0.75, &[]);
        rec.set_cache_hit_rate(0.0, &[]);
        rec.set_cache_hit_rate(1.0, &[]);
    }

    #[test]
    fn api_request_duration_histogram_does_not_panic() {
        let rec = test_recorder();
        rec.record_api_request_duration(12.3, &[KeyValue::new("endpoint", "/health")]);
    }

    #[test]
    fn active_features_gauge_does_not_panic() {
        let rec = test_recorder();
        rec.set_active_features(7, &[]);
    }

    #[test]
    fn init_metrics_does_not_panic() {
        let provider = SdkMeterProvider::builder().build();
        let meter = provider.meter("agileplus-init-test");
        super::init_metrics(&meter);
    }
}
