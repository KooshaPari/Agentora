use std::sync::Arc;

use phenotype_observability::{init_tracer, increment_counter};
use phenotype_cache_adapter::{TwoTierCache, MetricsHook};

#[derive(Debug)]
struct ObsHook;

impl MetricsHook for ObsHook {
    fn record_hit(&self, tier: &str) {
        let name = format!("cache.hit.{}", tier);
        increment_counter(&name);
    }
    fn record_miss(&self, tier: &str) {
        let name = format!("cache.miss.{}", tier);
        increment_counter(&name);
    }
}

fn main() {
    // Initialize tracing (no-op minimal implementation provided by phenotype-observability)
    init_tracer();

    let hook = Arc::new(ObsHook);
    let cache = TwoTierCache::new_with_metrics(100, 1000, Some(hook));

    cache.put("key1".to_string(), "value1".to_string());
    let _ = cache.get(&"key1".to_string());
}
