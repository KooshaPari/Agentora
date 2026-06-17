//! CLI sync subcommands for bidirectional Plane.so synchronisation.
//!
//! Provides:
//! - `sync push`    — T059: push local features/WPs to Plane.so
//! - `sync pull`    — T060: pull Plane.so changes locally
//! - `sync auto`    — T061: toggle auto-sync mode
//! - `sync status`  — T062: display sync status table
//! - `sync resolve` — T063: interactive conflict resolution
//!
//! Traceability: WP10-T059, T060, T061, T062, T063

mod args;
mod auto;
mod config;
mod helpers;
mod pull;
mod push;
mod resolve;
mod status;
#[cfg(test)]
mod tests;
mod types;

pub use args::{
    SyncArgs, SyncAutoArgs, SyncPullArgs, SyncPushArgs, SyncResolveArgs, SyncStatusArgs,
    SyncSubcommand,
};
pub use auto::{AutoSyncAction, run_sync_auto};
pub use config::SyncConfig;
pub use pull::run_sync_pull;
pub use push::run_sync_push;
pub use resolve::run_sync_resolve;
pub use status::run_sync_status;
pub use types::{
    ConflictResolution, SyncConflict, SyncDirection, SyncItemOutcome, SyncReport, SyncReportEntry,
    SyncStatusRow,
};

use anyhow::Result;

/// Dispatch `sync` subcommands.
pub async fn run_sync(args: SyncArgs) -> Result<()> {
    match args.subcommand {
        SyncSubcommand::Push(a) => run_sync_push(a).await,
        SyncSubcommand::Pull(a) => run_sync_pull(a).await,
        SyncSubcommand::Auto(a) => run_sync_auto(a),
        SyncSubcommand::Status(a) => run_sync_status(a),
        SyncSubcommand::Resolve(a) => run_sync_resolve(a),
    }
}
