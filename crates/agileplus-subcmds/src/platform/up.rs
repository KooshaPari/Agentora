use std::process::Command;
use std::time::Duration;

use anyhow::{Result, anyhow};

use crate::platform::args::PlatformUpArgs;
use crate::platform::health::{DEFAULT_API_URL, print_status_table_up, wait_for_health};
use crate::platform::process_compose::find_process_compose;
use crate::platform::workspace::resolve_platform_compose;

/// Start the platform.
pub fn run_platform_up(args: PlatformUpArgs) -> Result<()> {
    let pc = find_process_compose().ok_or_else(|| {
        anyhow!(
            "process-compose not found.\nInstall from: https://github.com/F1bonacc1/process-compose"
        )
    })?;

    println!("Starting AgilePlus platform...");

    let (workdir, compose) = resolve_platform_compose(&args.config)?;
    println!("  workdir: {}", workdir.display());
    println!("  compose: {}", compose.display());

    let child = Command::new(&pc)
        .current_dir(&workdir)
        .args(["up", "-f"])
        .arg(&compose)
        .spawn()
        .map_err(|e| anyhow!("Failed to start process-compose: {e}"))?;

    println!("process-compose starting (pid {})", child.id());
    println!();
    println!("Waiting for services to be ready...");

    // Poll /health until all pass or timeout.
    let health = wait_for_health(
        DEFAULT_API_URL,
        Duration::from_secs(args.poll_interval),
        Duration::from_secs(args.timeout),
    );

    match health {
        Ok(h) => {
            println!();
            println!("✓ All services healthy!");
            println!();
            print_status_table_up(&h.services);
            println!();
            println!("Platform ready. Dashboard: {DEFAULT_API_URL}/dashboard");
            Ok(())
        }
        Err(e) => Err(anyhow!("Platform did not become healthy: {e}")),
    }
}
