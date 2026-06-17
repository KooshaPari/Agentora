use clap::{Args, Subcommand};

/// `agileplus sync` dispatcher.
#[derive(Debug, Args)]
pub struct SyncArgs {
    #[command(subcommand)]
    pub subcommand: SyncSubcommand,
}

/// Available sync subcommands.
#[derive(Debug, Subcommand)]
pub enum SyncSubcommand {
    /// Push local features/WPs to Plane.so.
    Push(SyncPushArgs),
    /// Pull Plane.so changes locally.
    Pull(SyncPullArgs),
    /// Toggle or query auto-sync mode.
    Auto(SyncAutoArgs),
    /// Display sync status table for all tracked entities.
    Status(SyncStatusArgs),
    /// Interactively resolve a sync conflict.
    Resolve(SyncResolveArgs),
}

/// Arguments for `agileplus sync push`.
#[derive(Debug, Args)]
pub struct SyncPushArgs {
    /// Restrict push to a single feature (by slug).
    #[arg(long, value_name = "SLUG")]
    pub feature: Option<String>,

    /// Show what would be pushed without actually pushing.
    #[arg(long)]
    pub dry_run: bool,
}

/// Arguments for `agileplus sync pull`.
#[derive(Debug, Args)]
pub struct SyncPullArgs {
    /// Restrict pull to a single feature (by slug).
    #[arg(long, value_name = "SLUG")]
    pub feature: Option<String>,

    /// Show what would be pulled without actually applying changes.
    #[arg(long)]
    pub dry_run: bool,
}

/// Arguments for `agileplus sync auto`.
#[derive(Debug, Args)]
pub struct SyncAutoArgs {
    /// Action: on | off | status.
    #[arg(default_value = "status")]
    pub action: super::auto::AutoSyncAction,
}

/// Arguments for `agileplus sync status`.
#[derive(Debug, Args)]
pub struct SyncStatusArgs {
    /// Output format: table (default) or json.
    #[arg(long, default_value = "table")]
    pub output: String,
}

/// Arguments for `agileplus sync resolve`.
#[derive(Debug, Args)]
pub struct SyncResolveArgs {
    /// Entity type to resolve (feature | wp).
    pub entity_type: String,

    /// Entity ID.
    pub entity_id: String,
}
