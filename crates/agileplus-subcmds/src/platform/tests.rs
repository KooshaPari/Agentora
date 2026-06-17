use super::*;

#[test]
fn test_service_status_display() {
    assert_eq!(ServiceStatus::Healthy.to_string(), "Healthy");
    assert_eq!(ServiceStatus::Degraded.to_string(), "Degraded");
    assert_eq!(ServiceStatus::Unhealthy.to_string(), "Unhealthy");
    assert_eq!(ServiceStatus::Unknown.to_string(), "Unknown");
}

#[test]
fn test_overall_status_display() {
    assert_eq!(OverallStatus::Healthy.to_string(), "HEALTHY");
    assert_eq!(OverallStatus::Degraded.to_string(), "DEGRADED");
    assert_eq!(OverallStatus::Down.to_string(), "DOWN");
}

#[test]
fn test_synthetic_platform_health() {
    let h = health::synthetic_platform_health();
    assert_eq!(h.services.len(), 6);
    assert_eq!(h.overall, OverallStatus::Healthy);
    assert!(
        h.services
            .iter()
            .all(|s| s.status == ServiceStatus::Healthy || s.status == ServiceStatus::Ready)
    );
}

#[test]
fn test_platform_status_down_when_api_unreachable() {
    let health = health::fetch_platform_health("http://127.0.0.1:19999");
    assert_eq!(health.overall, OverallStatus::Down);
    assert_eq!(health.services[0].status, ServiceStatus::Unknown);
}

#[test]
fn test_print_status_table_does_not_panic() {
    let health = health::synthetic_platform_health();
    // Should not panic — just print.
    health::print_status_table(&health.services);
    health::print_status_table_up(&health.services);
}

#[test]
fn test_platform_down_args_defaults() {
    let args = PlatformDownArgs {
        config: "process-compose.yml".to_string(),
        timeout: 30,
    };
    assert_eq!(args.timeout, 30);
}

#[test]
fn test_platform_logs_args() {
    let args = PlatformLogsArgs {
        config: "process-compose.yml".to_string(),
        service: Some("nats".to_string()),
        follow: true,
        lines: 50,
        since: Some("1h".to_string()),
    };
    assert_eq!(args.service.as_deref(), Some("nats"));
    assert!(args.follow);
    assert_eq!(args.lines, 50);
    assert_eq!(args.since.as_deref(), Some("1h"));
}

#[test]
fn test_find_process_compose_returns_path_in_test_cfg() {
    // In test cfg, which_process_compose always returns Some.
    let result = process_compose::find_process_compose();
    assert!(result.is_some());
}
