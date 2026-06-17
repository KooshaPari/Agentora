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
