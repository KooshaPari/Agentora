use async_trait::async_trait;
use std::collections::HashMap;
use std::hash::{Hash, Hasher};
use std::sync::{Arc, RwLock};

use crate::{Result, RoutingRequest, RouterDecision};

#[async_trait]
pub trait Router: Send + Sync {
    fn name(&self) -> &str;
    async fn decide(&self, req: &RoutingRequest) -> Result<RouterDecision>;
}

pub struct CostAwareRouter {
    costs: HashMap<String, f64>,
}

impl CostAwareRouter {
    pub fn new() -> Self {
        let mut c = HashMap::new();
        c.insert("gpt-4o".into(), 0.005);
        c.insert("gpt-4o-mini".into(), 0.00015);
        c.insert("claude-3-5-sonnet".into(), 0.003);
        c.insert("claude-3-5-haiku".into(), 0.0008);
        c.insert("gemini-2.0-flash".into(), 0.000075);
        Self { costs: c }
    }
}

#[async_trait]
impl Router for CostAwareRouter {
    fn name(&self) -> &str { "cost_aware" }

    async fn decide(&self, req: &RoutingRequest) -> Result<RouterDecision> {
        let cost = self.costs.get(&req.model).copied().unwrap_or(0.001);
        let provider = if cost < 0.001 { "gemini-2.0-flash" } else { "gpt-4o-mini" };
        Ok(RouterDecision {
            provider: provider.into(),
            reasoning: "Selected for lowest cost".into(),
            estimated_cost_usd: cost,
            estimated_latency_ms: 150,
            confidence: 0.92,
        })
    }
}

pub struct LatencyAwareRouter {
    latencies: HashMap<String, u32>,
}

impl LatencyAwareRouter {
    pub fn new() -> Self {
        let mut l = HashMap::new();
        l.insert("gemini-2.0-flash".into(), 400);
        l.insert("claude-3-5-haiku".into(), 600);
        l.insert("gpt-4o-mini".into(), 800);
        l.insert("claude-3-5-sonnet".into(), 1200);
        l.insert("gpt-4o".into(), 1500);
        Self { latencies: l }
    }
}

#[async_trait]
impl Router for LatencyAwareRouter {
    fn name(&self) -> &str { "latency_aware" }

    async fn decide(&self, _req: &RoutingRequest) -> Result<RouterDecision> {
        let provider = self.latencies.iter()
            .min_by_key(|(_, v)| *v)
            .map(|(k, _)| k.clone())
            .unwrap_or_else(|| "gemini-2.0-flash".into());
        let latency = self.latencies.get(&provider).copied().unwrap_or(500);
        Ok(RouterDecision {
            provider,
            reasoning: "Selected for lowest latency".into(),
            estimated_cost_usd: 0.001,
            estimated_latency_ms: latency,
            confidence: 0.88,
        })
    }
}

pub struct FailoverRouter<P: Router, F: Router> {
    primary: Arc<P>,
    fallback: Arc<F>,
}

impl<P: Router + 'static, F: Router + 'static> FailoverRouter<P, F> {
    pub fn new(primary: Arc<P>, fallback: Arc<F>) -> Self {
        Self { primary, fallback }
    }
}

#[async_trait]
impl<P: Router + 'static, F: Router + 'static> Router for FailoverRouter<P, F> {
    fn name(&self) -> &str { "failover" }

    async fn decide(&self, req: &RoutingRequest) -> Result<RouterDecision> {
        match self.primary.decide(req).await {
            Ok(decision) => Ok(decision),
            Err(_) => self.fallback.decide(req).await,
        }
    }
}

pub struct TaskSpecificRouter {
    rules: HashMap<String, String>,
}

impl TaskSpecificRouter {
    pub fn new() -> Self {
        let mut r = HashMap::new();
        r.insert("code".into(), "gpt-4o".into());
        r.insert("analysis".into(), "claude-3-5-sonnet".into());
        r.insert("quick".into(), "gemini-2.0-flash".into());
        r.insert("creative".into(), "claude-3-5-sonnet".into());
        r.insert("default".into(), "gpt-4o-mini".into());
        Self { rules: r }
    }
}

#[async_trait]
impl Router for TaskSpecificRouter {
    fn name(&self) -> &str { "task_specific" }

    async fn decide(&self, req: &RoutingRequest) -> Result<RouterDecision> {
        let provider = req.task_type.as_ref()
            .and_then(|t| self.rules.get(t))
            .cloned()
            .unwrap_or_else(|| "gpt-4o-mini".into());
        Ok(RouterDecision {
            provider,
            reasoning: format!("Task-based selection: {:?}", req.task_type),
            estimated_cost_usd: 0.002,
            estimated_latency_ms: 800,
            confidence: 0.85,
        })
    }
}

struct PromptHasher;

impl PromptHasher {
    fn hash(s: &str) -> u64 {
        let mut h = std::collections::hash_map::DefaultHasher::new();
        s.hash(&mut h);
        h.finish()
    }
}

pub struct SemanticCacheRouter {
    cache: RwLock<HashMap<u64, (String, f64)>>,
}

impl SemanticCacheRouter {
    pub fn new() -> Self {
        Self { cache: RwLock::new(HashMap::new()) }
    }
}

#[async_trait]
impl Router for SemanticCacheRouter {
    fn name(&self) -> &str { "semantic_cache" }

    async fn decide(&self, req: &RoutingRequest) -> Result<RouterDecision> {
        let key = PromptHasher::hash(&req.prompt);

        if let Ok(cache) = self.cache.read() {
            if let Some((provider, cost)) = cache.get(&key) {
                return Ok(RouterDecision {
                    provider: provider.clone(),
                    reasoning: "Cache hit".into(),
                    estimated_cost_usd: *cost,
                    estimated_latency_ms: 5,
                    confidence: 0.99,
                });
            }
        }

        if let Ok(mut cache) = self.cache.write() {
            cache.insert(key, ("gpt-4o-mini".into(), 0.00015));
        }

        Ok(RouterDecision {
            provider: "gpt-4o-mini".into(),
            reasoning: "Cache miss".into(),
            estimated_cost_usd: 0.00015,
            estimated_latency_ms: 800,
            confidence: 0.75,
        })
    }
}

impl Default for CostAwareRouter { fn default() -> Self { Self::new() } }
impl Default for LatencyAwareRouter { fn default() -> Self { Self::new() } }
impl Default for TaskSpecificRouter { fn default() -> Self { Self::new() } }
impl Default for SemanticCacheRouter { fn default() -> Self { Self::new() } }

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_cost_aware() {
        let router = CostAwareRouter::new();
        let req = RoutingRequest::new("gpt-4o", "test");
        let decision = router.decide(&req).await.unwrap();
        assert!(decision.estimated_cost_usd < 0.006);
        assert_eq!(router.name(), "cost_aware");
    }

    #[tokio::test]
    async fn test_latency_aware() {
        let router = LatencyAwareRouter::new();
        let req = RoutingRequest::new("gpt-4o", "test");
        let decision = router.decide(&req).await.unwrap();
        assert_eq!(decision.provider, "gemini-2.0-flash");
        assert_eq!(router.name(), "latency_aware");
    }

    #[tokio::test]
    async fn test_task_specific_code() {
        let router = TaskSpecificRouter::new();
        let req = RoutingRequest::new("gpt-4o", "write code").with_task("code");
        let decision = router.decide(&req).await.unwrap();
        assert_eq!(decision.provider, "gpt-4o");
    }

    #[tokio::test]
    async fn test_task_specific_unknown_type() {
        let router = TaskSpecificRouter::new();
        let req = RoutingRequest::new("gpt-4o", "test").with_task("unknown");
        let decision = router.decide(&req).await.unwrap();
        assert_eq!(decision.provider, "gpt-4o-mini");
    }

    #[tokio::test]
    async fn test_task_specific_no_type() {
        let router = TaskSpecificRouter::new();
        let req = RoutingRequest::new("gpt-4o", "test");
        let decision = router.decide(&req).await.unwrap();
        assert_eq!(decision.provider, "gpt-4o-mini");
    }

    #[tokio::test]
    async fn test_semantic_cache_miss_then_hit() {
        let router = Arc::new(SemanticCacheRouter::new());
        let req = RoutingRequest::new("gpt-4o-mini", "What is 2+2?");
        let d1 = router.decide(&req).await.unwrap();
        assert_eq!(d1.estimated_latency_ms, 800);
        let d2 = router.decide(&req).await.unwrap();
        assert_eq!(d2.estimated_latency_ms, 5);
        assert_eq!(d2.reasoning, "Cache hit");
    }

    #[tokio::test]
    async fn test_semantic_cache_different_prompts() {
        let router = Arc::new(SemanticCacheRouter::new());
        let req1 = RoutingRequest::new("gpt-4o-mini", "What is 2+2?");
        let req2 = RoutingRequest::new("gpt-4o-mini", "What is 3+3?");
        let d1 = router.decide(&req1).await.unwrap();
        let d2 = router.decide(&req2).await.unwrap();
        assert_eq!(d1.estimated_latency_ms, 800);
        assert_eq!(d2.estimated_latency_ms, 800);
    }

    #[tokio::test]
    async fn test_failover_primary() {
        let primary = Arc::new(CostAwareRouter::new());
        let fallback = Arc::new(LatencyAwareRouter::new());
        let router = FailoverRouter::new(primary, fallback);
        let req = RoutingRequest::new("gpt-4o", "test");
        let decision = router.decide(&req).await.unwrap();
        assert_eq!(decision.provider, "gpt-4o-mini");
        assert_eq!(router.name(), "failover");
    }

    #[tokio::test]
    async fn test_failover_with_task_router() {
        let primary = Arc::new(TaskSpecificRouter::new());
        let fallback = Arc::new(LatencyAwareRouter::new());
        let router = FailoverRouter::new(primary, fallback);
        let req = RoutingRequest::new("gpt-4o", "write code").with_task("code");
        let decision = router.decide(&req).await.unwrap();
        assert_eq!(decision.provider, "gpt-4o");
    }
}
