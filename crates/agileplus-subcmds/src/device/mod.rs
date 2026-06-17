//! Device management CLI commands for AgilePlus.
//!
//! Provides three subcommands:
//!   - `agileplus device discover` — enumerate peers on the Tailscale network
//!   - `agileplus device sync`     — replicate events with one or more peers
//!   - `agileplus device status`   — show local device identity and sync state
//!
//! Traceability: WP18 / T104, T105, T106

mod args;
mod discover;
mod status;
mod sync;
mod types;

#[cfg(test)]
mod tests;

pub use args::{DeviceArgs, DeviceSubcommand, DiscoverArgs, StatusArgs, SyncArgs, SyncStrategy};
pub use discover::run_discover;
pub use status::run_status;
pub use sync::run_sync;
pub use types::{
    DeviceStatusReport, KnownPeerEntry, LocalDeviceInfo, PeerRow, PeerSyncReport, VectorEntry,
};

/// Dispatch a `DeviceArgs` to the appropriate handler.
#[cfg(unix)]
pub async fn run(args: &DeviceArgs) -> anyhow::Result<()> {
    match &args.command {
        DeviceSubcommand::Discover(a) => run_discover(a).await,
        DeviceSubcommand::Sync(a) => run_sync(a).await,
        DeviceSubcommand::Status(a) => run_status(a).await,
    }
}

/// Dispatch a `DeviceArgs` to the appropriate handler.
#[cfg(not(unix))]
pub async fn run(_args: &DeviceArgs) -> anyhow::Result<()> {
    anyhow::bail!("Device commands require Unix (Tailscale UNIX socket)")
}
