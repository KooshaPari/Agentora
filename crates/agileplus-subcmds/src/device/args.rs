use clap::{Args, Subcommand, ValueEnum};

/// Arguments for the `device` command group.
#[derive(Debug, Args)]
pub struct DeviceArgs {
    #[command(subcommand)]
    pub command: DeviceSubcommand,
}

/// Subcommands available under `agileplus device`.
#[derive(Debug, Subcommand)]
pub enum DeviceSubcommand {
    /// Discover AgilePlus peers on the Tailscale network.
    Discover(DiscoverArgs),
    /// Synchronise events with one or more peers.
    Sync(SyncArgs),
    /// Show local device identity and sync vector state.
    Status(StatusArgs),
}

/// Arguments for `agileplus device discover`.
#[derive(Debug, Args)]
pub struct DiscoverArgs {
    /// Timeout in seconds for the discovery operation.
    #[arg(long, default_value = "10")]
    pub timeout: u64,

    /// Port used to probe whether AgilePlus is running on a peer.
    #[arg(long, default_value = "3000")]
    pub port: u16,

    /// Output results as JSON instead of a human-readable table.
    #[arg(long)]
    pub json: bool,
}

/// Conflict-resolution strategy for the sync operation.
#[derive(Debug, Clone, ValueEnum)]
pub enum SyncStrategy {
    /// Last-write wins (default).
    LastWriteWins,
    /// Manual conflict resolution — flag conflicts for review.
    Manual,
}

impl std::fmt::Display for SyncStrategy {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            SyncStrategy::LastWriteWins => write!(f, "last-write-wins"),
            SyncStrategy::Manual => write!(f, "manual"),
        }
    }
}

/// Arguments for `agileplus device sync`.
#[derive(Debug, Args)]
pub struct SyncArgs {
    /// Sync with all online peers.
    #[arg(long, conflicts_with = "peer")]
    pub all: bool,

    /// Sync with a specific peer identified by device ID or Tailscale IP.
    #[arg(long)]
    pub peer: Option<String>,

    /// Conflict-resolution strategy.
    #[arg(long, value_enum, default_value = "last-write-wins")]
    pub strategy: SyncStrategy,

    /// Preview what would be synced without transferring any data.
    #[arg(long)]
    pub dry_run: bool,

    /// Print detailed progress information.
    #[arg(long)]
    pub verbose: bool,
}

/// Arguments for `agileplus device status`.
#[derive(Debug, Args)]
pub struct StatusArgs {
    /// Output as JSON.
    #[arg(long)]
    pub json: bool,

    /// Show only the known peers section.
    #[arg(long, conflicts_with = "vectors_only")]
    pub peers_only: bool,

    /// Show only the sync vector section.
    #[arg(long, conflicts_with = "peers_only")]
    pub vectors_only: bool,
}
