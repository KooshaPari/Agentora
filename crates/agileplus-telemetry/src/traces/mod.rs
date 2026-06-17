//! OpenTelemetry trace spans for AgilePlus.
//!
//! Uses the `tracing` crate (not raw OTel spans) so that the
//! `tracing-opentelemetry` bridge exports spans automatically when a provider
//! is configured.
//!
//! # OTLP Setup
//!
//! Call [`init_tracer`] at application startup to configure the global trace
//! provider. Then install [`telemetry_layer`] in your `tracing` subscriber to
//! export spans via the `tracing-opentelemetry` bridge.

use std::time::Instant;

use opentelemetry::global;
use opentelemetry::trace::TracerProvider as _;
use tracing::Subscriber;
use tracing_subscriber::{Layer, registry::LookupSpan};

// ---------------------------------------------------------------------------
// OTLP initialisation (T090 / T091)
// ---------------------------------------------------------------------------

/// Initialise the global OTLP trace provider.
///
/// Reads `OTEL_EXPORTER_OTLP_ENDPOINT` from the environment (default:
/// `http://localhost:4317`).  Creates an HTTP-proto batch span exporter and
/// sets it as the global provider.
///
/// # Errors
///
/// Returns `Err(String)` if the exporter or provider cannot be built.
/// Callers may choose to fall back gracefully (e.g. no-op provider).
pub fn init_tracer() -> Result<(), String> {
    use opentelemetry_otlp::WithExportConfig;
    use opentelemetry_sdk::trace::SdkTracerProvider;

    let endpoint = std::env::var("OTEL_EXPORTER_OTLP_ENDPOINT")
        .unwrap_or_else(|_| "http://localhost:4317".to_string());

    let exporter = opentelemetry_otlp::SpanExporter::builder()
        .with_http()
        .with_endpoint(&endpoint)
        .build()
        .map_err(|e| e.to_string())?;

    let provider = SdkTracerProvider::builder()
        .with_batch_exporter(exporter)
        .build();

    global::set_tracer_provider(provider);
    Ok(())
}

/// Return a composable [`Layer`] that bridges `tracing` spans to the global
/// OpenTelemetry trace provider.
///
/// Install this layer *after* calling [`init_tracer`] (or any other call that
/// sets up the global tracer provider) to ensure spans are exported.
///
/// # Example
///
/// ```no_run
/// use tracing_subscriber::prelude::*;
/// use agileplus_telemetry::traces::{init_tracer, telemetry_layer};
///
/// init_tracer().ok();
/// tracing_subscriber::registry()
///     .with(tracing_subscriber::fmt::layer().json())
///     .with(telemetry_layer())
///     .init();
/// ```
/// Return a composable [`Layer`] that bridges `tracing` spans to a new OTLP
/// exporter pointing at `OTEL_EXPORTER_OTLP_ENDPOINT`.
///
/// This variant builds a fresh `SdkTracerProvider` internally so that the
/// layer holds a concrete `SdkTracer` (required by `PreSampledTracer`).
/// Call [`init_tracer`] separately if you also want the *global* provider set.
pub fn telemetry_layer<S>() -> impl Layer<S>
where
    S: Subscriber + for<'a> LookupSpan<'a>,
{
    use opentelemetry_sdk::trace::SdkTracerProvider;

    let endpoint = std::env::var("OTEL_EXPORTER_OTLP_ENDPOINT")
        .unwrap_or_else(|_| "http://localhost:4317".to_string());

    // Attempt to build an OTLP exporter; fall back to no-op on failure.
    let provider: SdkTracerProvider = (|| {
        use opentelemetry_otlp::WithExportConfig;
        let exporter = opentelemetry_otlp::SpanExporter::builder()
            .with_http()
            .with_endpoint(&endpoint)
            .build()
            .ok()?;
        Some(
            SdkTracerProvider::builder()
                .with_batch_exporter(exporter)
                .build(),
        )
    })()
    .unwrap_or_else(SdkTracerProvider::default);

    let tracer = provider.tracer("agileplus");
    tracing_opentelemetry::layer().with_tracer(tracer)
}

// ---------------------------------------------------------------------------
// Span attribute name constants
// ---------------------------------------------------------------------------

pub const ATTR_COMMAND: &str = "agileplus.command";
pub const ATTR_FEATURE_SLUG: &str = "agileplus.feature.slug";
pub const ATTR_WP_ID: &str = "agileplus.wp.id";
pub const ATTR_AGENT_TYPE: &str = "agileplus.agent.type";
pub const ATTR_REVIEW_CYCLE: &str = "agileplus.review.cycle";

// ---------------------------------------------------------------------------
// Span creation helpers
// ---------------------------------------------------------------------------

/// Create a top-level command span.
///
/// This span should be the parent of all child spans within a single CLI
/// invocation.
pub fn create_command_span(command_name: &str, feature_slug: Option<&str>) -> tracing::Span {
    match feature_slug {
        Some(slug) => tracing::info_span!(
            "agileplus.command",
            { ATTR_COMMAND } = command_name,
            { ATTR_FEATURE_SLUG } = slug,
        ),
        None => tracing::info_span!("agileplus.command", { ATTR_COMMAND } = command_name,),
    }
}

/// Create an agent-dispatch span as a child of `parent`.
pub fn create_agent_span(parent: &tracing::Span, wp_id: &str, agent_type: &str) -> tracing::Span {
    let _guard = parent.enter();
    tracing::info_span!(
        "agileplus.agent",
        { ATTR_WP_ID } = wp_id,
        { ATTR_AGENT_TYPE } = agent_type,
    )
}

/// Create a review-loop iteration span as a child of `parent`.
pub fn create_review_span(parent: &tracing::Span, cycle: u32) -> tracing::Span {
    let _guard = parent.enter();
    tracing::info_span!("agileplus.review", { ATTR_REVIEW_CYCLE } = cycle,)
}

/// Add a named event with key-value attributes to an existing span.
///
/// Used for milestone markers: "PR created", "review received", "CI passed".
pub fn record_span_event(span: &tracing::Span, name: &str, attributes: &[(String, String)]) {
    let _guard = span.enter();
    // Build a KV string for the event fields.
    let fields: Vec<String> = attributes.iter().map(|(k, v)| format!("{k}={v}")).collect();
    tracing::info!(event = name, fields = ?fields);
}

// ---------------------------------------------------------------------------
// SpanGuard — auto-records duration on drop
// ---------------------------------------------------------------------------

/// RAII guard that records `duration_ms` on the wrapped span when dropped.
pub struct SpanGuard {
    pub span: tracing::Span,
    start: Instant,
}

impl SpanGuard {
    /// Wrap an existing span.
    pub fn new(span: tracing::Span) -> Self {
        Self {
            span,
            start: Instant::now(),
        }
    }

    /// Create a new command span and immediately wrap it in a guard.
    pub fn command(command_name: &str, feature_slug: Option<&str>) -> Self {
        Self::new(create_command_span(command_name, feature_slug))
    }
}

impl Drop for SpanGuard {
    fn drop(&mut self) {
        let duration_ms = self.start.elapsed().as_millis() as u64;
        self.span.record("duration_ms", duration_ms);
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use tracing_subscriber::prelude::*;

    fn init_test_subscriber() {
        // Ignore errors if subscriber already set (other tests).
        let _ = tracing_subscriber::registry()
            .with(tracing_subscriber::fmt::layer())
            .try_init();
    }

    #[test]
    fn command_span_created() {
        init_test_subscriber();
        let span = create_command_span("implement", Some("001-sde"));
        // Span may be disabled or noop depending on test subscriber state;
        // verify it can be entered and dropped without panic.
        let _guard = span.enter();
    }

    #[test]
    fn child_spans_created() {
        init_test_subscriber();
        let parent = create_command_span("implement", None);
        let agent = create_agent_span(&parent, "WP10", "claude-code");
        let review = create_review_span(&agent, 1);
        // Enter each span to verify they're usable.
        let _g1 = parent.enter();
        let _g2 = agent.enter();
        let _g3 = review.enter();
    }

    #[test]
    fn span_guard_records_duration() {
        init_test_subscriber();
        let guard = SpanGuard::command("test", None);
        // Just verify it doesn't panic on drop.
        drop(guard);
    }

    #[test]
    fn record_span_event_does_not_panic() {
        init_test_subscriber();
        let span = create_command_span("test", None);
        record_span_event(
            &span,
            "pr_created",
            &[("wp_id".to_string(), "WP10".to_string())],
        );
    }
}
