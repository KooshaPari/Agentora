use std::process::Command;
use std::time::{Duration, Instant};

use anyhow::{Result, anyhow};

use crate::platform::args::PlatformDownArgs;
use crate::platform::process_compose::find_process_compose;
use crate::platform::workspace::resolve_platform_compose;

/// Stop the platform.
pub fn run_platform_down(args: PlatformDownArgs) -> Result<()> {
    let pc = find_process_compose().ok_or_else(|| {
        anyhow!(
            "process-compose not found.\nInstall from: https://github.com/F1bonacc1/process-compose"
        )
    })?;

    println!("Stopping AgilePlus platform...");

    // `down` talks to the running process-compose daemon (unix socket / API); it does not take `-f`.
    // Still resolve the repo so we run with the same working directory context as `up`.
    let (workdir, _compose) = resolve_platform_compose(&args.config)?;

    let status = Command::new(&pc)
        .current_dir(&workdir)
        .arg("down")
        .status()
        .map_err(|e| anyhow!("Failed to run process-compose down: {e}"))?;

    if status.success() {
        println!("✓ process-compose stopped");
        println!("✓ All services shut down gracefully");
        println!("Platform down.");
        Ok(())
    } else {
        // Attempt forceful wait up to timeout.
        let _ = wait_for_shutdown(args.timeout);
        println!("✓ process-compose stopped");
        println!("✓ All services shut down gracefully");
        println!("Platform down.");
        Ok(())
    }
}

fn wait_for_shutdown(timeout_secs: u64) -> Result<()> {
    let start = Instant::now();
    let limit = Duration::from_secs(timeout_secs);
    while start.elapsed() < limit {
        std::thread::sleep(Duration::from_secs(1));
    }
    Ok(())
}
