//! Phenotype Rate Limiter
//!
//! A hexagonal rate limiting crate with multiple algorithm backends.
//!
//! ## Features
//!
//! - **Token Bucket**: Classic token bucket with configurable capacity and refill rate
//! - **Sliding Window**: Sliding window counter for smooth rate limiting
//!
//! ## Architecture
//!
//! This crate follows hexagonal architecture:
//! - `ports`: Core interfaces (RateLimiterPort)
//! - `types`: Domain types for rate limit configuration
//! - `adapters`: Algorithm implementations
//!
//! ## Example
//!
//! ```rust
//! use phenotype_rate_limiter::{TokenBucketAdapter, RateLimiterPort, Quota};
//!
//! #[tokio::main]
//! async fn main() {
//!     let limiter = TokenBucketAdapter::new(Quota::per_second(100));
//!     
//!     match limiter.acquire("user:123", 1).await {
//!         Ok(_) => println!("Request allowed"),
//!         Err(_) => println!("Rate limited"),
//!     }
//! }
//! ```

pub mod adapters;
pub mod error;
pub mod ports;
pub mod types;

// Re-export commonly used items
pub use adapters::{SlidingWindowAdapter, TokenBucketAdapter};
pub use error::{RateLimitError, Result};
pub use ports::RateLimiterPort;
pub use types::{Quota, RateLimitConfig, RateLimitStatus};

/// Default key for global rate limiting
pub const DEFAULT_KEY: &str = "global";

/// Default burst capacity multiplier
pub const DEFAULT_BURST_MULTIPLIER: u32 = 2;
