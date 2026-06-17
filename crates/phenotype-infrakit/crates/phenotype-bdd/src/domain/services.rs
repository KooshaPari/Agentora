use std::sync::{Arc, RwLock};

use crate::domain::entities::*;
use crate::domain::ports::{StepContext, StepDefinitionPort};
use crate::BddError;
use uuid::Uuid;

pub trait StepMatcher: Send + Sync {
    fn find_match(&self, text: &str) -> Result<&dyn StepDefinitionPort, BddError>;
    fn register(&mut self, pattern: &str, definition: Box<dyn StepDefinitionPort>);
}

struct RegisteredStep {
    pattern: String,
    definition: Box<dyn StepDefinitionPort>,
}

pub struct StepRegistry {
    steps: Vec<RegisteredStep>,
}

impl std::fmt::Debug for StepRegistry {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("StepRegistry")
            .field("count", &self.steps.len())
            .finish()
    }
}

impl StepRegistry {
    pub fn new() -> Self {
        Self { steps: Vec::new() }
    }

    pub fn register_step<D: StepDefinitionPort + 'static>(&mut self, definition: D) {
        let pattern = definition.pattern().to_string();
        self.steps.push(RegisteredStep {
            pattern,
            definition: Box::new(definition),
        });
    }

    pub fn find_definition(&self, text: &str) -> Result<&dyn StepDefinitionPort, BddError> {
        let matches: Vec<&RegisteredStep> =
            self.steps.iter().filter(|s| s.pattern == text).collect();
        match matches.len() {
            0 => Err(BddError::NoMatch { text: text.into() }),
            1 => Ok(matches[0].definition.as_ref()),
            _ => Err(BddError::AmbiguousMatch { text: text.into() }),
        }
    }
}

impl Default for StepRegistry {
    fn default() -> Self {
        Self::new()
    }
}

pub struct ScenarioExecutor {
    step_registry: Arc<RwLock<StepRegistry>>,
}

impl std::fmt::Debug for ScenarioExecutor {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("ScenarioExecutor").finish()
    }
}

impl ScenarioExecutor {
    pub fn new(step_registry: Arc<RwLock<StepRegistry>>) -> Self {
        Self { step_registry }
    }

    pub fn execute(&self, scenario: &Scenario, background: Option<&Background>) -> ScenarioResult {
        let started_at = chrono::Utc::now();
        let mut step_results = Vec::new();
        let mut failed = false;

        let mut run_step = |step: &Step| -> (Uuid, StepResult) {
            if failed {
                return (
                    step.id,
                    StepResult::Skipped {
                        reason: "previous step failed".into(),
                    },
                );
            }
            let registry = self.step_registry.read().unwrap();
            match registry.find_definition(&step.text) {
                Ok(def) => {
                    let ctx = StepContext::new(&step.text);
                    match def.execute(&ctx) {
                        Ok(()) => (step.id, StepResult::Passed),
                        Err(e) => {
                            failed = true;
                            (
                                step.id,
                                StepResult::Failed {
                                    error: e.to_string(),
                                    location: format!("line {}", step.line_number),
                                },
                            )
                        }
                    }
                }
                Err(BddError::NoMatch { text }) => {
                    failed = true;
                    (
                        step.id,
                        StepResult::Pending {
                            reason: format!("no definition for: {}", text),
                        },
                    )
                }
                Err(BddError::AmbiguousMatch { text }) => {
                    failed = true;
                    (
                        step.id,
                        StepResult::Ambiguous {
                            matches: vec![text],
                        },
                    )
                }
                Err(_) => {
                    failed = true;
                    (
                        step.id,
                        StepResult::Failed {
                            error: "unexpected error".into(),
                            location: format!("line {}", step.line_number),
                        },
                    )
                }
            }
        };

        if let Some(bg) = background {
            for step in &bg.steps {
                step_results.push(run_step(step));
            }
        }
        for step in &scenario.steps {
            step_results.push(run_step(step));
        }

        let completed_at = chrono::Utc::now();
        let duration_ms = (completed_at - started_at).num_milliseconds().max(0) as u64;

        ScenarioResult {
            scenario_id: scenario.id,
            scenario_name: scenario.name.clone(),
            step_results,
            duration_ms,
            started_at,
            completed_at,
        }
    }
}

pub struct FeatureRunner {
    executor: ScenarioExecutor,
}

impl std::fmt::Debug for FeatureRunner {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("FeatureRunner").finish()
    }
}

impl FeatureRunner {
    pub fn new(executor: ScenarioExecutor) -> Self {
        Self { executor }
    }

    pub fn run(&self, feature: &Feature) -> FeatureResult {
        let started_at = chrono::Utc::now();
        let mut scenario_results = Vec::new();

        for scenario in &feature.scenarios {
            let expanded = scenario.expand();
            for s in &expanded {
                let result = self.executor.execute(s, feature.background.as_ref());
                scenario_results.push(result);
            }
        }

        let completed_at = chrono::Utc::now();
        let status = if scenario_results
            .iter()
            .any(|r| r.status() == ExecutionStatus::Failed)
        {
            ExecutionStatus::Failed
        } else if scenario_results
            .iter()
            .all(|r| r.status() == ExecutionStatus::Passed)
        {
            ExecutionStatus::Passed
        } else if scenario_results
            .iter()
            .any(|r| r.status() == ExecutionStatus::Pending)
        {
            ExecutionStatus::Pending
        } else {
            ExecutionStatus::Skipped
        };

        FeatureResult {
            feature_id: feature.id,
            feature_name: feature.name.clone(),
            scenario_results,
            status,
            started_at,
            completed_at,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    struct PassStepDef(&'static str);
    impl StepDefinitionPort for PassStepDef {
        fn execute(&self, _: &StepContext) -> Result<(), BddError> {
            Ok(())
        }
        fn pattern(&self) -> &str {
            self.0
        }
    }

    struct FailStepDef(&'static str);
    impl StepDefinitionPort for FailStepDef {
        fn execute(&self, _: &StepContext) -> Result<(), BddError> {
            Err(BddError::StepFailed {
                message: "boom".into(),
            })
        }
        fn pattern(&self) -> &str {
            self.0
        }
    }

    #[test]
    fn test_step_registry_find() {
        let mut registry = StepRegistry::new();
        registry.register_step(PassStepDef("I have a calculator"));
        let found = registry.find_definition("I have a calculator");
        assert!(found.is_ok());
    }

    #[test]
    fn test_step_registry_no_match() {
        let registry = StepRegistry::new();
        let result = registry.find_definition("unknown step");
        assert!(matches!(result, Err(BddError::NoMatch { .. })));
    }

    #[test]
    fn test_scenario_executor_passing() {
        let registry = Arc::new(RwLock::new({
            let mut r = StepRegistry::new();
            r.register_step(PassStepDef("I have a calculator"));
            r
        }));
        let executor = ScenarioExecutor::new(registry);
        let scenario =
            Scenario::new("Test").with_step(Step::new(StepType::Given, "I have a calculator"));
        let result = executor.execute(&scenario, None);
        assert_eq!(result.status(), ExecutionStatus::Passed);
    }

    #[test]
    fn test_scenario_executor_failure() {
        let registry = Arc::new(RwLock::new({
            let mut r = StepRegistry::new();
            r.register_step(FailStepDef("I fail"));
            r.register_step(PassStepDef("I pass"));
            r
        }));
        let executor = ScenarioExecutor::new(registry);
        let scenario = Scenario::new("Test")
            .with_step(Step::new(StepType::When, "I fail"))
            .with_step(Step::new(StepType::Then, "I pass"));
        let result = executor.execute(&scenario, None);
        assert_eq!(result.status(), ExecutionStatus::Failed);
    }

    #[test]
    fn test_feature_runner() {
        let registry = Arc::new(RwLock::new({
            let mut r = StepRegistry::new();
            r.register_step(PassStepDef("step one"));
            r
        }));
        let executor = ScenarioExecutor::new(registry);
        let runner = FeatureRunner::new(executor);
        let feature = Feature::new("Test")
            .with_scenario(Scenario::new("A").with_step(Step::new(StepType::Given, "step one")));
        let result = runner.run(&feature);
        assert_eq!(result.status, ExecutionStatus::Passed);
    }
}
