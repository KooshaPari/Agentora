//! Port definitions for rate limiting

use crate::error::Result;
use crate::types::{Quota, RateLimitStatus};
use async_trait::async_trait;

#[async_trait]
pub trait RateLimiterPort: Send + Sync {
    async fn acquire(&self, key: &str, permits: u32) -> Result<RateLimitStatus>;
    async fn check(&self, key: &str, permits: u32) -> Result<RateLimitStatus>;
    fn quota(&self) -> Quota;
    async fn reset(&self, key: &str) -> Result<()>;
    async fn reset_all(&self) -> Result<()>;
}

pub trait RateLimiterBuilder: Default {
    type Limiter: RateLimiterPort;
    fn quota(self, quota: Quota) -> Self;
    fn build(self) -> Self::Limiter;
}
