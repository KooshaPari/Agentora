//! BDD integration tests

use phenotype_bdd::{FeatureParser, Runner};

mod steps;

#[tokio::test]
async fn test_bdd_scenarios() {
    // Parse the feature file
    let feature = FeatureParser::parse_file("tests/features/example.feature")
        .await
        .expect("Failed to parse feature file");

    // Setup step registry
    let registry = steps::setup_registry()
        .await
        .expect("Failed to setup registry");

    // Run scenarios
    let runner = Runner::new(registry);
    let result = runner.run(feature)
        .await
        .expect("Failed to run scenarios");

    // Assert all passed
    assert_eq!(
        result.failed, 0,
        "BDD scenarios failed: {:?}",
        result.scenario_results
    );

    println!(
        "BDD Results: {} passed, {} failed, {} skipped",
        result.passed, result.failed, result.skipped
    );
}

#[tokio::test]
async fn test_inline_feature() {
    // You can also define features inline for testing
    let feature_content = r#"
Feature: Inline Test
  Scenario: Simple test
    Given the system is initialized
    When I perform an action
    Then the result should be success
"#;

    let feature = FeatureParser::parse_str(feature_content)
        .expect("Failed to parse inline feature");

    let registry = steps::setup_registry()
        .await
        .expect("Failed to setup registry");

    let runner = Runner::new(registry);
    let result = runner.run(feature)
        .await
        .expect("Failed to run scenarios");

    assert_eq!(result.failed, 0, "Inline scenarios failed");
}
