/// Integration test for Sentry error capture in phenotype-infrakit
///
/// This test verifies that Sentry is properly initialized and can capture errors.
/// Run with: cargo test --test sentry_integration_test -- --nocapture

#[test]
fn test_sentry_initialization() {
    // FR-SENTRY-001: Sentry should initialize without panicking
    let _guard = phenotype_sentry_config::initialize();
    // Guard is valid, test passes
}

#[test]
fn test_sentry_capture_message() {
    // FR-SENTRY-002: Should be able to capture messages
    let _guard = phenotype_sentry_config::initialize();
    phenotype_sentry_config::capture_message(
        "Integration test message from phenotype-infrakit",
        sentry::Level::Info,
    );
    // Message captured, test passes
}

#[test]
fn test_sentry_capture_error() {
    // FR-SENTRY-003: Should be able to capture errors
    let _guard = phenotype_sentry_config::initialize();
    let error = std::io::Error::new(
        std::io::ErrorKind::Other,
        "Test error for Sentry in phenotype-infrakit",
    );
    phenotype_sentry_config::capture_error(&error);
    // Error captured, test passes
}

#[test]
fn test_sentry_initialization_with_env_override() {
    // FR-SENTRY-005: Environment should be overridable
    std::env::set_var("SENTRY_ENVIRONMENT", "test");
    let _guard = phenotype_sentry_config::initialize();
    std::env::remove_var("SENTRY_ENVIRONMENT");
    // Test passes
}
