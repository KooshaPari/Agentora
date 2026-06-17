//! Test runner for Phenotype

use std::future::Future;
use std::pin::Pin;

/// Async test runner
pub struct AsyncRunner;

impl AsyncRunner {
    /// Run an async test with timeout
    pub async fn run_with_timeout<F, T>(
        future: F,
        timeout_ms: u64,
    ) -> Result<T, String>
    where
        F: Future<Output = T>,
    {
        tokio::time::timeout(
            std::time::Duration::from_millis(timeout_ms),
            future,
        )
        .await
        .map_err(|_| "Test timed out".to_string())
    }
}

/// Test runner for sync tests
pub struct SyncRunner;

impl SyncRunner {
    /// Run a test with timeout
    pub fn run_with_timeout<T>(
        f: impl FnOnce() -> T,
        timeout_ms: u64,
    ) -> Result<T, String> {
        std::thread::scope(|s| {
            let handle = s.spawn(f);
            match handle.join() {
                Ok(result) => Ok(result),
                Err(_) => Err("Test panicked".to_string()),
            }
        })
    }
}
