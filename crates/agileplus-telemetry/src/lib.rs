//! AgilePlus telemetry — OpenTelemetry traces, metrics, and structured logs.
//!
//! # Quick-start
//!
//! ```no_run
//! use agileplus_telemetry::{TelemetryAdapter, config::TelemetryConfig};
//!
//! #[tokio::main]
//! async fn main() {
//!     let cfg = TelemetryConfig::load().unwrap_or_default();
//!     let adapter = TelemetryAdapter::new(cfg).expect("telemetry init");
//!     // adapter is `ObservabilityPort`-compatible
//! }
//! ```

pub mod config;
pub mod logs;
pub mod metrics;
pub mod traces;

use agileplus_domain::ports::observability::{LogEntry, LogLevel, ObservabilityPort, SpanContext};
use opentelemetry::global;
use opentelemetry::metrics::MeterProvider as _MeterProvider;
use opentelemetry_sdk::metrics::SdkMeterProvider;
use tracing_appender::non_blocking::WorkerGuard;

use crate::{config::TelemetryConfig, logs::LogError, metrics::MetricsRecorder};

// ---------------------------------------------------------------------------
// Error
// ---------------------------------------------------------------------------

#[derive(Debug, thiserror::Error)]
pub enum TelemetryError {
    #[error("logging init error: {0}")]
    Log(#[from] LogError),
    #[error("config error: {0}")]
    Config(#[from] crate::config::ConfigError),
    #[error("opentelemetry error: {0}")]
    Otel(String),
}

// ---------------------------------------------------------------------------
// TelemetryAdapter
// ---------------------------------------------------------------------------

/// Primary adapter implementing [`ObservabilityPort`].
///
/// Holds OpenTelemetry global state, a metrics recorder, and owns the
/// non-blocking log writer guard.
pub struct TelemetryAdapter {
    /// Tracer from the global provider (kept alive to maintain provider registration).
    #[allow(dead_code)]
    tracer: opentelemetry::global::BoxedTracer,
    /// Metrics recorder (wraps OTel instruments).
    metrics: MetricsRecorder,
    /// Configuration snapshot (kept for introspection / shutdown).
    config: TelemetryConfig,
    /// `WorkerGuard` for the non-blocking log writer — must be held for the
    /// process lifetime to prevent log loss.
    _log_guard: Option<WorkerGuard>,
    /// Whether the adapter was created in no-op mode.
    noop: bool,
}

// Safety: the OTel types in use are `Send + Sync`.
unsafe impl Send for TelemetryAdapter {}
unsafe impl Sync for TelemetryAdapter {}

impl TelemetryAdapter {
    // -----------------------------------------------------------------------
    // Constructors
    // -----------------------------------------------------------------------

    /// Initialise a fully functional telemetry adapter from `config`.
    ///
    /// OTLP pipeline initialisation is attempted lazily: if the endpoint is
    /// unreachable the adapter falls back to a no-op exporter and logs a
    /// warning.
    pub fn new(config: TelemetryConfig) -> Result<Self, TelemetryError> {
        // Set up trace provider.
        init_trace_provider(&config);

        // Set up metrics provider.
        let meter_provider = SdkMeterProvider::builder().build();
        global::set_meter_provider(meter_provider);

        let meter = global::meter("agileplus");
        let metrics = MetricsRecorder::new(&meter);

        let tracer = global::tracer("agileplus");

        // Set up structured logging.
        let guard = logs::init_logging(&config.logging).ok(); // non-fatal

        Ok(Self {
            tracer,
            metrics,
            config,
            _log_guard: guard,
            noop: false,
        })
    }

    /// Create a no-op adapter that succeeds on every call but produces no
    /// output.  Intended for tests and minimal configurations.
    pub fn noop() -> Self {
        let provider = SdkMeterProvider::builder().build();
        let meter = _MeterProvider::meter(&provider, "agileplus-noop");
        let metrics = MetricsRecorder::new(&meter);
        let tracer = opentelemetry::global::tracer("agileplus-noop");

        Self {
            tracer,
            metrics,
            config: TelemetryConfig::default(),
            _log_guard: None,
            noop: true,
        }
    }

    // -----------------------------------------------------------------------
    // Accessors
    // -----------------------------------------------------------------------

    /// Return a reference to the metrics recorder for advanced usage.
    pub fn metrics(&self) -> &MetricsRecorder {
        &self.metrics
    }

    /// Return the active telemetry configuration.
    pub fn config(&self) -> &TelemetryConfig {
        &self.config
    }

    /// Whether this adapter was created in no-op mode.
    pub fn is_noop(&self) -> bool {
        self.noop
    }
}

impl Drop for TelemetryAdapter {
    fn drop(&mut self) {
        // `_log_guard` is dropped here, which flushes the non-blocking writer.
        // Note: TracerProvider shutdown is handled by the global provider on drop
        // in OTel 0.28+ (shutdown_tracer_provider was removed from the global API).
    }
}

// ---------------------------------------------------------------------------
// ObservabilityPort impl
// ---------------------------------------------------------------------------

impl ObservabilityPort for TelemetryAdapter {
    // -- Tracing --

    fn start_span(&self, name: &str, parent: Option<&SpanContext>) -> SpanContext {
        if self.noop {
            return noop_span_context();
        }
        let span = match parent {
            Some(p) => tracing::info_span!(
                "agileplus.span",
                name = name,
                parent_span_id = %p.span_id,
                trace_id = %p.trace_id,
            ),
            None => tracing::info_span!("agileplus.span", name = name),
        };

        // Derive IDs from the tracing span metadata.
        let span_id = format!("{:?}", span.id().map(|id| id.into_u64()).unwrap_or(0));
        let trace_id = parent
            .map(|p| p.trace_id.clone())
            .unwrap_or_else(|| span_id.clone());

        // Keep span entered so it propagates; the caller ends it via `end_span`.
        let _ = span.enter();

        SpanContext {
            trace_id,
            span_id,
            parent_span_id: parent.map(|p| p.span_id.clone()),
        }
    }

    fn end_span(&self, ctx: &SpanContext) {
        if self.noop {
            return;
        }
        tracing::trace!(span_id = %ctx.span_id, "span ended");
    }

    fn add_span_event(&self, ctx: &SpanContext, name: &str, attributes: &[(&str, &str)]) {
        if self.noop {
            return;
        }
        let fields: Vec<String> = attributes.iter().map(|(k, v)| format!("{k}={v}")).collect();
        tracing::info!(
            span_id = %ctx.span_id,
            event = name,
            fields = ?fields,
        );
    }

    fn set_span_error(&self, ctx: &SpanContext, error: &str) {
        if self.noop {
            return;
        }
        tracing::error!(span_id = %ctx.span_id, error = error);
    }

    // -- Metrics --

    fn record_counter(&self, name: &str, value: u64, labels: &[(&str, &str)]) {
        if self.noop {
            return;
        }
        let kv: Vec<opentelemetry::KeyValue> = labels
            .iter()
            .map(|(k, v)| opentelemetry::KeyValue::new(k.to_string(), v.to_string()))
            .collect();
        let meter = global::meter("agileplus");
        let counter = meter.u64_counter(name.to_owned()).build();
        counter.add(value, &kv);
    }

    fn record_histogram(&self, name: &str, value: f64, labels: &[(&str, &str)]) {
        if self.noop {
            return;
        }
        let kv: Vec<opentelemetry::KeyValue> = labels
            .iter()
            .map(|(k, v)| opentelemetry::KeyValue::new(k.to_string(), v.to_string()))
            .collect();
        let meter = global::meter("agileplus");
        let hist = meter.f64_histogram(name.to_owned()).build();
        hist.record(value, &kv);
    }

    fn record_gauge(&self, name: &str, value: f64, labels: &[(&str, &str)]) {
        if self.noop {
            return;
        }
        let kv: Vec<opentelemetry::KeyValue> = labels
            .iter()
            .map(|(k, v)| opentelemetry::KeyValue::new(k.to_string(), v.to_string()))
            .collect();
        let meter = global::meter("agileplus");
        let gauge = meter.f64_gauge(name.to_owned()).build();
        gauge.record(value, &kv);
    }

    // -- Logging --

    fn log(&self, entry: &LogEntry) {
        if self.noop {
            return;
        }
        let fields_str = format!("{:?}", entry.fields);
        match entry.level {
            LogLevel::Trace => tracing::trace!(message = %entry.message, fields = %fields_str),
            LogLevel::Debug => tracing::debug!(message = %entry.message, fields = %fields_str),
            LogLevel::Info => tracing::info!(message = %entry.message, fields = %fields_str),
            LogLevel::Warn => tracing::warn!(message = %entry.message, fields = %fields_str),
            LogLevel::Error => tracing::error!(message = %entry.message, fields = %fields_str),
        }
    }

    fn log_info(&self, message: &str) {
        if !self.noop {
            tracing::info!("{}", message);
        }
    }

    fn log_warn(&self, message: &str) {
        if !self.noop {
            tracing::warn!("{}", message);
        }
    }

    fn log_error(&self, message: &str) {
        if !self.noop {
            tracing::error!("{}", message);
        }
    }
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/// Initialise the global OTel trace provider.
///
/// If an OTLP endpoint is configured we attempt to connect; on failure we
/// fall back to a no-op exporter and emit a warning.
fn init_trace_provider(config: &TelemetryConfig) {
    use opentelemetry_sdk::trace::SdkTracerProvider;

    if let Some(otlp) = &config.otlp {
        match build_otlp_provider(otlp) {
            Ok(provider) => {
                global::set_tracer_provider(provider);
                return;
            }
            Err(e) => {
                tracing::warn!(
                    "OTLP trace provider unavailable ({}): falling back to no-op exporter",
                    e
                );
            }
        }
    }

    // No OTLP configured or connection failed — use SDK default (no export).
    let provider = SdkTracerProvider::builder().build();
    global::set_tracer_provider(provider);
}

/// Attempt to build an OTLP trace exporter.
fn build_otlp_provider(
    otlp: &crate::config::OtlpConfig,
) -> Result<opentelemetry_sdk::trace::SdkTracerProvider, String> {
    use opentelemetry_otlp::WithExportConfig;
    use opentelemetry_sdk::trace::SdkTracerProvider;

    let exporter = opentelemetry_otlp::SpanExporter::builder()
        .with_http()
        .with_endpoint(&otlp.endpoint)
        .with_timeout(std::time::Duration::from_millis(otlp.timeout_ms))
        .build()
        .map_err(|e| e.to_string())?;

    let provider = SdkTracerProvider::builder()
        .with_batch_exporter(exporter)
        .build();

    Ok(provider)
}

/// Generate a sentinel `SpanContext` for no-op mode.
fn noop_span_context() -> SpanContext {
    SpanContext {
        trace_id: "00000000000000000000000000000000".into(),
        span_id: "0000000000000000".into(),
        parent_span_id: None,
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use agileplus_domain::ports::observability::LogEntry;
    use std::collections::HashMap;

    #[test]
    fn noop_adapter_does_not_panic() {
        let adapter = TelemetryAdapter::noop();
        assert!(adapter.is_noop());
        adapter.log_info("hello");
        adapter.log_warn("warn");
        adapter.log_error("error");
        let ctx = adapter.start_span("test", None);
        adapter.add_span_event(&ctx, "event", &[("k", "v")]);
        adapter.set_span_error(&ctx, "oops");
        adapter.end_span(&ctx);
        adapter.record_counter("agileplus.test", 1, &[("label", "value")]);
        adapter.record_histogram("agileplus.hist", 42.0, &[]);
        adapter.record_gauge("agileplus.gauge", 1.0, &[]);
    }

    #[test]
    fn noop_adapter_noop_span_context_sentinel() {
        let adapter = TelemetryAdapter::noop();
        let ctx = adapter.start_span("op", None);
        assert_eq!(ctx.trace_id, "00000000000000000000000000000000");
        assert_eq!(ctx.span_id, "0000000000000000");
        assert!(ctx.parent_span_id.is_none());
    }

    #[test]
    fn noop_adapter_log_entry() {
        let adapter = TelemetryAdapter::noop();
        let entry = LogEntry {
            level: LogLevel::Info,
            message: "test".into(),
            fields: HashMap::new(),
            span_context: None,
        };
        adapter.log(&entry); // must not panic
    }
}
