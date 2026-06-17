//! Async trait definitions for Phenotype

use std::future::Future;
use std::pin::Pin;

/// Async trait for cancellable operations
pub trait Cancellable: Send + Sync {
    /// Cancel the operation
    fn cancel(&self) -> Pin<Box<dyn Future<Output = ()> + Send + '_>>;
}

/// Async trait for operations with timeout
pub trait Timeoutable: Send + Sync {
    /// Set timeout for the operation
    fn with_timeout(self, duration: std::time::Duration) -> Pin<Box<dyn Future<Output = Self> + Send>>
    where
        Self: Sized;
}
