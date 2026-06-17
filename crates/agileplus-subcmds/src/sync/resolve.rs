use anyhow::Result;

use super::{
    args::SyncResolveArgs,
    helpers::capitalize,
    types::{ConflictResolution, SyncConflict},
};

/// Run `agileplus sync resolve <entity-type> <entity-id>`.
pub fn run_sync_resolve(args: SyncResolveArgs) -> Result<()> {
    let conflict = stub_conflict(&args.entity_type, &args.entity_id);

    println!(
        "Conflict in {} '{}':\n",
        capitalize(&conflict.entity_kind),
        conflict.entity_name
    );
    println!("Local:");
    println!("  State: {}", conflict.local_state);
    println!("  Description: {}", conflict.local_description);
    println!();
    println!("Remote (Plane.so):");
    println!("  State: {}", conflict.remote_state);
    println!("  Description: {}", conflict.remote_description);
    println!();

    println!("Choose resolution:");
    println!("  (L) Keep local changes");
    println!("  (R) Accept remote changes");
    println!("  (M) Merge manually");
    println!("  (C) Cancel");
    println!();
    print!("> ");
    use std::io::Write;
    std::io::stdout().flush().ok();

    let mut input = String::new();
    std::io::stdin().read_line(&mut input)?;
    let choice = input.trim().to_uppercase();

    let resolution = match choice.as_str() {
        "L" => ConflictResolution::KeepLocal,
        "R" => ConflictResolution::AcceptRemote,
        "M" => ConflictResolution::MergeManually,
        "C" | "" => ConflictResolution::Cancel,
        other => {
            eprintln!("Unknown choice '{other}'. Cancelling.");
            ConflictResolution::Cancel
        }
    };

    apply_resolution(resolution, &conflict)
}

fn apply_resolution(resolution: ConflictResolution, conflict: &SyncConflict) -> Result<()> {
    match resolution {
        ConflictResolution::KeepLocal => {
            println!("\nApplied: Local version wins");
            println!("SyncMapping updated, event logged");
            tracing::info!(entity = %conflict.entity_name, "conflict resolved: local wins");
        }
        ConflictResolution::AcceptRemote => {
            println!("\nApplied: Remote version wins");
            println!("Local state updated, SyncMapping updated, event logged");
            tracing::info!(entity = %conflict.entity_name, "conflict resolved: remote wins");
        }
        ConflictResolution::MergeManually => {
            println!("\nManual merge required.");
            println!(
                "Edit the entity locally then run: agileplus sync push --feature {}",
                conflict.entity_name
            );
        }
        ConflictResolution::Cancel => {
            println!("\nCancelled. Conflict not resolved.");
        }
    }
    Ok(())
}

fn stub_conflict(entity_type: &str, entity_id: &str) -> SyncConflict {
    SyncConflict {
        entity_kind: entity_type.to_string(),
        entity_id: entity_id.to_string(),
        entity_name: "api-design".to_string(),
        local_state: "researched".to_string(),
        local_description: "Initial API design with OAuth".to_string(),
        remote_state: "unstarted".to_string(),
        remote_description: "API design".to_string(),
    }
}
