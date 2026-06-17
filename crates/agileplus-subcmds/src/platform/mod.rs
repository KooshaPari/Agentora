//! CLI platform subcommands for AgilePlus platform management.
//!
//! Provides:
//! - `platform up`     — T084: start all platform services
//! - `platform down`   — T085: stop all platform services
//! - `platform status` — T086: query service health
//! - `platform logs`   — T087: display/follow service logs
//!
//! **process-compose:** resolves `process-compose.yml` via repo walk or `AGILEPLUS_ROOT`, sets **cwd**, and
//! uses `up -f <path>`. `down` uses the daemon (no `-f`). `logs` maps to **`process-compose process logs`**
//! (current CLI; no top-level `logs` command).
//!
//! Traceability: WP14-T084, T085, T086, T087

mod args;
mod down;
mod health;
mod logs;
mod process_compose;
mod status;
mod types;
mod up;
mod workspace;

pub use args::{
    PlatformArgs, PlatformDownArgs, PlatformLogsArgs, PlatformStatusArgs, PlatformSubcommand,
    PlatformUpArgs,
};
pub use down::run_platform_down;
pub use logs::run_platform_logs;
pub use status::run_platform_status;
pub use types::{OverallStatus, PlatformHealth, ServiceHealth, ServiceStatus};
pub use up::run_platform_up;

use anyhow::Result;

/// Run a `platform` subcommand.
pub fn run_platform(args: PlatformArgs) -> Result<()> {
    match args.subcommand {
        PlatformSubcommand::Up(a) => run_platform_up(a),
        PlatformSubcommand::Down(a) => run_platform_down(a),
        PlatformSubcommand::Status(a) => run_platform_status(a),
        PlatformSubcommand::Logs(a) => run_platform_logs(a),
    }
}

#[cfg(test)]
mod tests;
