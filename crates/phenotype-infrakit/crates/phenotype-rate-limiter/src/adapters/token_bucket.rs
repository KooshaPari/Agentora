//! Token bucket rate limiter adapter

use std::collections::HashMap;
use std::sync::Arc;
use std::time::{Duration, Instant};

use async_trait::async_trait;
use parking_lot::RwLock;

use crate::error::Result;
use crate::ports::RateLimiterPort;
use crate::types::{Quota, RateLimitStatus};

#[derive(Debug, Clone)]
struct BucketState {
    tokens: u64,
    last_refill: Instant,
    capacity: u64,
    refill_rate: f64,
}

#[derive(Debug)]
pub struct TokenBucketAdapter {
    buckets: Arc<RwLock<HashMap<String, BucketState>>>,
    quota: Quota,
    capacity: u64,
    refill_rate: f64,
}

impl TokenBucketAdapter {
    pub fn new(quota: Quota) -> Self {
        let capacity = quota.burst_capacity() as u64;
        let refill_rate = quota.refill_rate_per_second();
        Self {
            buckets: Arc::new(RwLock::new(HashMap::new())),
            quota,
            capacity,
            refill_rate,
        }
    }

    fn refill(state: &mut BucketState, now: Instant) {
        let elapsed = now.duration_since(state.last_refill);
        let refill_tokens = (elapsed.as_secs_f64() * state.refill_rate) as u64;
        if refill_tokens > 0 {
            state.tokens = (state.tokens + refill_tokens).min(state.capacity);
            state.last_refill = now;
        }
    }

    fn result_from_state(state: &BucketState, requested: u32) -> RateLimitStatus {
        let requested = requested as u64;
        if state.tokens >= requested {
            let remaining = (state.tokens - requested) as u32;
            let capacity = state.capacity as u32;
            let reset_after = if state.refill_rate > 0.0 {
                let needed = state.capacity - remaining as u64;
                Duration::from_secs_f64(needed as f64 / state.refill_rate)
            } else {
                Duration::from_secs(0)
            };
            RateLimitStatus::allowed(remaining, capacity, reset_after)
        } else {
            let deficit = requested - state.tokens;
            let retry_after = if state.refill_rate > 0.0 {
                Duration::from_secs_f64(deficit as f64 / state.refill_rate)
            } else {
                Duration::from_secs(u64::MAX)
            };
            RateLimitStatus::denied(state.capacity as u32, retry_after)
        }
    }
}

#[async_trait]
impl RateLimiterPort for TokenBucketAdapter {
    async fn acquire(&self, key: &str, permits: u32) -> Result<RateLimitStatus> {
        let now = Instant::now();
        let mut buckets = self.buckets.write();
        let state = buckets
            .entry(key.to_string())
            .or_insert_with(|| BucketState {
                tokens: self.capacity,
                last_refill: now,
                capacity: self.capacity,
                refill_rate: self.refill_rate,
            });
        Self::refill(state, now);
        let result = Self::result_from_state(state, permits);
        if result.is_allowed() {
            state.tokens -= permits as u64;
        }
        Ok(result)
    }

    async fn check(&self, key: &str, permits: u32) -> Result<RateLimitStatus> {
        let now = Instant::now();
        let mut buckets = self.buckets.write();
        let state = buckets
            .entry(key.to_string())
            .or_insert_with(|| BucketState {
                tokens: self.capacity,
                last_refill: now,
                capacity: self.capacity,
                refill_rate: self.refill_rate,
            });
        Self::refill(state, now);
        Ok(Self::result_from_state(state, permits))
    }

    fn quota(&self) -> Quota {
        self.quota
    }

    async fn reset(&self, key: &str) -> Result<()> {
        let mut buckets = self.buckets.write();
        buckets.insert(
            key.to_string(),
            BucketState {
                tokens: self.capacity,
                last_refill: Instant::now(),
                capacity: self.capacity,
                refill_rate: self.refill_rate,
            },
        );
        Ok(())
    }

    async fn reset_all(&self) -> Result<()> {
        self.buckets.write().clear();
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_token_bucket_acquire_allowed() {
        let adapter = TokenBucketAdapter::new(Quota::new(10, Duration::from_secs(1)));
        let result = adapter.acquire("user:1", 1).await.unwrap();
        assert!(result.is_allowed());
        assert_eq!(result.remaining, 9);
    }

    #[tokio::test]
    async fn test_token_bucket_check() {
        let adapter = TokenBucketAdapter::new(Quota::new(10, Duration::from_secs(1)));
        let result = adapter.check("user:1", 3).await.unwrap();
        assert!(result.is_allowed());
        assert_eq!(result.remaining, 7);
    }

    #[tokio::test]
    async fn test_token_bucket_exhausted() {
        let adapter = TokenBucketAdapter::new(Quota::new(2, Duration::from_secs(1)));
        adapter.acquire("user:1", 2).await.unwrap();
        let result = adapter.check("user:1", 1).await.unwrap();
        assert!(result.is_denied());
        assert!(result.retry_after.is_some());
    }

    #[tokio::test]
    async fn test_token_bucket_reset() {
        let adapter = TokenBucketAdapter::new(Quota::new(10, Duration::from_secs(1)));
        adapter.acquire("user:1", 10).await.unwrap();
        adapter.reset("user:1").await.unwrap();
        let result = adapter.acquire("user:1", 1).await.unwrap();
        assert!(result.is_allowed());
    }

    #[tokio::test]
    async fn test_token_bucket_reset_all() {
        let adapter = TokenBucketAdapter::new(Quota::new(10, Duration::from_secs(1)));
        adapter.acquire("user:1", 5).await.unwrap();
        adapter.acquire("user:2", 5).await.unwrap();
        adapter.reset_all().await.unwrap();

        let result1 = adapter.check("user:1", 1).await.unwrap();
        let result2 = adapter.check("user:2", 1).await.unwrap();
        assert!(result1.is_allowed());
        assert!(result2.is_allowed());
    }
}
