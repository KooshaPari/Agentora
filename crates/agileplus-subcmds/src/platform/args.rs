use clap::{Args, Subcommand};

/// `agileplus platform` subcommand dispatcher.
#[derive(Debug, Args)]
pub struct PlatformArgs {
    #[command(subcommand)]
    pub subcommand: PlatformSubcommand,
}

/// Available platform subcommands.
#[derive(Debug, Subcommand)]
pub enum PlatformSubcommand {
    /// Start the platform and all services.
    Up(PlatformUpArgs),
    /// Stop all platform services.
    Down(PlatformDownArgs),
    /// Query service health and display status.
    Status(PlatformStatusArgs),
    /// Display and optionally follow service logs.
    Logs(PlatformLogsArgs),
}

/// Arguments for `platform up`.
#[derive(Debug, Args)]
pub struct PlatformUpArgs {
    /// Path to process-compose config file.
    #[arg(long, default_value = "process-compose.yml")]
    pub config: String,
    /// Health check poll interval in seconds.
    #[arg(long, default_value_t = 2)]
    pub poll_interval: u64,
    /// Maximum time to wait for services to be ready (seconds).
    #[arg(long, default_value_t = 60)]
    pub timeout: u64,
}

/// Arguments for `platform down`.
#[derive(Debug, Args)]
pub struct PlatformDownArgs {
    /// Path to process-compose config file (resolved from repo root or `AGILEPLUS_ROOT`).
    #[arg(long, default_value = "process-compose.yml")]
    pub config: String,
    /// Maximum time to wait for graceful shutdown (seconds).
    #[arg(long, default_value_t = 30)]
    pub timeout: u64,
}

/// Arguments for `platform status`.
#[derive(Debug, Args)]
pub struct PlatformStatusArgs {
    /// Health endpoint base URL.
    #[arg(long, default_value = "http://localhost:3000")]
    pub api_url: String,
}

/// Arguments for `platform logs`.
#[derive(Debug, Args)]
pub struct PlatformLogsArgs {
    /// Path to process-compose config file (resolved from repo root or `AGILEPLUS_ROOT`).
    #[arg(long, default_value = "process-compose.yml")]
    pub config: String,
    /// Service to show logs for (omit for all services).
    pub service: Option<String>,
    /// Follow (stream) log output.
    #[arg(short, long)]
    pub follow: bool,
    /// Number of lines to show from end of log.
    #[arg(long, default_value_t = 100)]
    pub lines: u32,
    /// Show logs since duration (e.g. 1h, 30m).
    #[arg(long)]
    pub since: Option<String>,
}
