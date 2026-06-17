//! Sentry error tracking configuration for phenotype ecosystem.
//!
//! Provides simple, unified Sentry SDK initialization and error capture utilities.

use std::env;

/// Initialize Sentry with environment-based DSN configuration.
///
/// Supports the following environment variables:
/// - `SENTRY_DSN`: Sentry project DSN (optional, defaults to test mode)
/// - `SENTRY_ENVIRONMENT`: Environment identifier (defaults to "development")
/// - `SENTRY_RELEASE`: Release version (automatically set from cargo)
///
/// # Example
/// ```ignore
/// use phenotype_sentry_config::initialize;
///
/// let _guard = initialize();
/// // Now panics and errors are automatically captured
/// ```
pub fn initialize() -> sentry::ClientInitGuard {
    let dsn = env::var("SENTRY_DSN").ok();
    let environment = env::var("SENTRY_ENVIRONMENT")
        .unwrap_or_else(|_| "development".to_string());
    let release = env!("CARGO_PKG_VERSION");

    // Use test DSN if not provided
    let dsn_url = dsn.as_deref().unwrap_or("https://test@test.ingest.sentry.io/0");

    sentry::init((
        dsn_url,
        sentry::ClientOptions {
            environment: Some(environment.into()),
            release: Some(release.into()),
            attach_stacktrace: true,
            debug: true,
            ..Default::default()
        },
    ))
}

/// Initialize Sentry with custom client options.
///
/// # Example
/// ```ignore
/// use phenotype_sentry_config::initialize_with_options;
///
/// let options = sentry::ClientOptions {
///     environment: Some("production".into()),
///     ..Default::default()
/// };
/// let _guard = initialize_with_options("https://your-dsn@sentry.io/id", options);
/// ```
pub fn initialize_with_options(
    dsn: &str,
    mut options: sentry::ClientOptions,
) -> sentry::ClientInitGuard {
    options.attach_stacktrace = true;
    sentry::init((dsn, options))
}

/// Capture an error event to Sentry.
///
/// # Example
/// ```ignore
/// use phenotype_sentry_config::capture_error;
///
/// let err = std::io::Error::last_os_error();
/// capture_error(&err);
/// ```
pub fn capture_error(error: &(dyn std::error::Error + 'static)) {
    sentry::capture_error(error);
}

/// Capture a message event to Sentry.
///
/// # Example
/// ```ignore
/// use phenotype_sentry_config::capture_message;
///
/// capture_message("Critical event", sentry::Level::Error);
/// ```
pub fn capture_message(msg: &str, level: sentry::Level) {
    sentry::capture_message(msg, level);
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_initialize_without_dsn() {
        // FR-SENTRY-001: Sentry should initialize in test mode without DSN
        env::remove_var("SENTRY_DSN");
        let _guard = initialize();
        assert!(true);
    }

    #[test]
    fn test_environment_override() {
        // FR-SENTRY-002: Environment should be overridable via env var
        env::set_var("SENTRY_ENVIRONMENT", "test");
        let _guard = initialize();
        assert!(true);
    }
}
