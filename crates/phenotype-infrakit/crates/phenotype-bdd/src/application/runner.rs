use std::sync::{Arc, RwLock};

use crate::adapters::parser::GherkinParser;
use crate::adapters::reporter::JsonReporter;
use crate::domain::entities::FeatureResult;
use crate::domain::services::{FeatureRunner, ScenarioExecutor, StepRegistry};
use crate::BddError;

pub struct BddAppRunner {
    parser: GherkinParser,
    reporter: JsonReporter,
    step_registry: Arc<RwLock<StepRegistry>>,
}

impl std::fmt::Debug for BddAppRunner {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("BddAppRunner").finish()
    }
}

impl BddAppRunner {
    pub fn new(step_registry: StepRegistry) -> Self {
        Self {
            parser: GherkinParser::new(),
            reporter: JsonReporter::new(),
            step_registry: Arc::new(RwLock::new(step_registry)),
        }
    }

    pub fn run_feature_content(
        &self,
        content: &str,
        source: Option<&str>,
    ) -> Result<FeatureResult, BddError> {
        let feature = self.parser.parse_feature(content, source)?;
        let executor = ScenarioExecutor::new(self.step_registry.clone());
        let runner = FeatureRunner::new(executor);
        Ok(runner.run(&feature))
    }

    pub fn run_and_report(&self, content: &str, source: Option<&str>) -> Result<String, BddError> {
        let result = self.run_feature_content(content, source)?;
        self.reporter.write_report(&result)
    }

    pub fn run_and_write_report(
        &self,
        content: &str,
        source: Option<&str>,
        output_path: &str,
    ) -> Result<FeatureResult, BddError> {
        let result = self.run_feature_content(content, source)?;
        self.reporter.write_report_to_file(&result, output_path)?;
        Ok(result)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::domain::ports::{StepContext, StepDefinitionPort};

    struct PassDef(&'static str);
    impl StepDefinitionPort for PassDef {
        fn execute(&self, _: &StepContext) -> Result<(), BddError> {
            Ok(())
        }
        fn pattern(&self) -> &str {
            self.0
        }
    }

    // Traces to: FR-BDD-060 - App runner executes feature
    #[test]
    fn test_app_runner_execute() {
        let mut registry = StepRegistry::new();
        registry.register_step(PassDef("I have a calculator"));
        let runner = BddAppRunner::new(registry);
        let content = r#"
Feature: Calc
  Scenario: Add
    Given I have a calculator
"#;
        let result = runner.run_feature_content(content, None).unwrap();
        assert_eq!(result.scenario_results.len(), 1);
    }

    // Traces to: FR-BDD-061 - App runner returns JSON report
    #[test]
    fn test_app_runner_report() {
        let mut registry = StepRegistry::new();
        registry.register_step(PassDef("step one"));
        let runner = BddAppRunner::new(registry);
        let content = r#"
Feature: Rpt
  Scenario: A
    Given step one
"#;
        let json = runner.run_and_report(content, None).unwrap();
        assert!(json.contains("Rpt"));
    }

    // Traces to: FR-BDD-062 - App runner handles parse error
    #[test]
    fn test_app_runner_parse_error() {
        let registry = StepRegistry::new();
        let runner = BddAppRunner::new(registry);
        let result = runner.run_feature_content("@@@ invalid @@@", None);
        assert!(result.is_err());
    }
}
