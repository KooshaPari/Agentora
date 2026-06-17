use anyhow::{Context, Result};
use clap::ValueEnum;

use super::{args::SyncAutoArgs, config::SyncConfig};

/// Action for `agileplus sync auto`.
#[derive(Debug, Clone, ValueEnum)]
pub enum AutoSyncAction {
    On,
    Off,
    Status,
}

/// Run `agileplus sync auto`.
pub fn run_sync_auto(args: SyncAutoArgs) -> Result<()> {
    let project_root = std::env::current_dir().context("getting current directory")?;
    let mut config = SyncConfig::load(&project_root)?;

    match args.action {
        AutoSyncAction::Status => {
            if config.auto_sync_enabled {
                println!("Auto-sync is ON");
            } else {
                println!("Auto-sync is OFF");
            }
        }
        AutoSyncAction::On => {
            config.auto_sync_enabled = true;
            config.save(&project_root)?;
            println!("Auto-sync enabled");
        }
        AutoSyncAction::Off => {
            config.auto_sync_enabled = false;
            config.save(&project_root)?;
            println!("Auto-sync disabled");
        }
    }
    Ok(())
}
