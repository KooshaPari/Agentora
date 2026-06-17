use anyhow::Result;

use crate::platform::args::PlatformStatusArgs;
use crate::platform::health::{fetch_platform_health, print_status_table};
use crate::platform::types::{OverallStatus, ServiceStatus};

/// Display platform service health.
pub fn run_platform_status(args: PlatformStatusArgs) -> Result<()> {
    let health = fetch_platform_health(&args.api_url);
    print_status_table(&health.services);
    println!();

    let degraded_count = health
        .services
        .iter()
        .filter(|s| s.status == ServiceStatus::Degraded)
        .count();
    let down_count = health
        .services
        .iter()
        .filter(|s| s.status == ServiceStatus::Unhealthy)
        .count();

    let overall_msg = match &health.overall {
        OverallStatus::Healthy => "HEALTHY".to_string(),
        OverallStatus::Degraded => format!(
            "DEGRADED ({} service{} slow, {} service{} down)",
            degraded_count,
            if degraded_count == 1 { "" } else { "s" },
            down_count,
            if down_count == 1 { "" } else { "s" },
        ),
        OverallStatus::Down => "DOWN".to_string(),
    };
    println!("Overall Status: {overall_msg}");
    Ok(())
}
