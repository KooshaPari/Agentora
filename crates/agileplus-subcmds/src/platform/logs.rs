use std::process::Command;

use anyhow::{Result, anyhow};

use crate::platform::args::PlatformLogsArgs;
use crate::platform::process_compose::find_process_compose;
use crate::platform::workspace::resolve_platform_compose;

/// Display service logs (via the running process-compose daemon).
///
/// Modern process-compose uses `process logs`, not a top-level `logs` command.
pub fn run_platform_logs(args: PlatformLogsArgs) -> Result<()> {
    let pc = find_process_compose().ok_or_else(|| {
        anyhow!(
            "process-compose not found.\nInstall from: https://github.com/F1bonacc1/process-compose"
        )
    })?;

    // Validate repo / compose file exists (same project as `platform up`).
    let (_workdir, _compose) = resolve_platform_compose(&args.config)?;

    let mut cmd = Command::new(&pc);
    cmd.args(["process", "logs"]);
    if let Some(ref svc) = args.service {
        cmd.arg(svc);
    }
    if args.follow {
        cmd.arg("--follow");
    }
    cmd.arg("-n").arg(args.lines.to_string());
    if args.since.is_some() {
        eprintln!(
            "Note: --since is not passed to this process-compose build (no matching flag); use shell history or omit."
        );
    }

    let status = cmd
        .status()
        .map_err(|e| anyhow!("Failed to run process-compose process logs: {e}"))?;

    if !status.success() {
        return Err(anyhow!(
            "process-compose process logs exited with status: {}",
            status
        ));
    }
    Ok(())
}
