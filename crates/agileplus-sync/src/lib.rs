//! AgilePlus sync orchestrator — conflict detection, resolution, and NATS integration.
//!
//! Traceability: FR-SYNC-* / WP09

pub mod conflict;
pub mod error;
pub mod nats;
pub mod report;
pub mod resolution;
pub mod store;

pub use conflict::SyncConflict;
pub use error::SyncError;
pub use nats::NatsSyncBridge;
pub use report::SyncReport;
pub use resolution::{FieldSource, ResolutionStrategy};
pub use store::SyncMappingStore;
