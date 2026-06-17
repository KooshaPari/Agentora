//! Phenotype event sourcing with blake3 hash chains.
//!
//! Provides append-only event storage with cryptographic hash chain verification
//! for audit-heavy domains.
//!
//! # Core Types
//!
//! - [`EventEnvelope<T>`]: Immutable event wrapper with blake3 hash chain
//! - [`EventStore`]: Synchronous event store trait
//! - [`AsyncEventStore`]: Async event store trait
//! - [`InMemoryEventStore`]: Reference implementation

pub mod async_store;
pub mod error;
pub mod event;
pub mod hash;
pub mod memory;
pub mod snapshot;
pub mod store;

pub use error::{EventSourcingError, HashError, Result};
pub use event::EventEnvelope;
pub use hash::{compute_hash, verify_chain, ZERO_HASH};
pub use memory::InMemoryEventStore;
pub use snapshot::{Snapshot, SnapshotConfig};
pub use store::EventStore;

use std::sync::atomic::{AtomicU64, Ordering};

/// Initialize telemetry for the event-sourcing crate.
/// Call this once in your application main (or test setup).
pub fn init_telemetry(service_name: &str) {
    phenotype_infrakit::phenotype_observability::init_tracer(service_name);
}

/// A simple counter for events appended (for quick metrics without full Observability setup).
static EVENT_APPEND_COUNT: AtomicU64 = AtomicU64::new(0);

/// Record an event append metric.
pub fn record_event_append() {
    let count = EVENT_APPEND_COUNT.fetch_add(1, Ordering::Relaxed) + 1;
    if count % 100 == 0 {
        // Every 100 events, increment a counter via the observability facade.
        phenotype_infrakit::phenotype_observability::increment_counter("event_store.append_batch");
    }
}

/// Append an event and record metrics.
/// This is a convenience wrapper around EventStore::append with instrumentation.
pub fn append_with_metrics<S: EventStore, E: serde::Serialize + Clone>(
    store: &mut S,
    aggregate_id: &str,
    event: E,
) -> Result<u64> {
    record_event_append();
    store.append(aggregate_id, event)
}
