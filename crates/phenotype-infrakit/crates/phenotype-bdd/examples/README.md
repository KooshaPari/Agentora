# Example Feature Files for phenotype-bdd

This directory contains example Gherkin feature files demonstrating BDD testing
patterns for various Phenotype infrastructure components.

## Files

- `analytics.feature` - Analytics event tracking scenarios
- `http_client.feature` - HTTP client behavior scenarios
- `validation.feature` - Data validation scenarios

## Usage

```rust
use phenotype_bdd::{FeatureParser, StepRegistry, Runner};

#[tokio::test]
async fn test_analytics_features() {
    let feature = FeatureParser::parse_file("tests/features/analytics.feature").await.unwrap();
    let registry = analytics_step_registry().await;
    let runner = Runner::new(registry);
    let result = runner.run(feature).await.unwrap();
    assert_eq!(result.failed, 0);
}
```
