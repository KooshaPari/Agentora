//! Tracing infrastructure

use tracing_subscriber::{fmt, EnvFilter};

const DEFAULT_FILTER: &str = "info,clikit=debug";

pub fn init_tracing() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    init_tracing_with_filter(DEFAULT_FILTER)
}

pub fn init_tracing_with_filter(
    filter: impl AsRef<str>,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let env_filter =
        EnvFilter::try_new(filter.as_ref()).unwrap_or_else(|_| EnvFilter::new(DEFAULT_FILTER));

    fmt().with_env_filter(env_filter).try_init()
}
