//! Domain ports (trait interfaces)

use crate::domain::entities::*;
use crate::BddError;

pub trait FeatureParserPort: Send + Sync {
    fn parse_feature(&self, content: &str, source: Option<&str>) -> Result<Feature, BddError>;
}

pub trait StepMatcherPort: Send + Sync {
    fn find_match(&self, text: &str) -> Result<&dyn StepDefinitionPort, BddError>;
}

pub trait StepDefinitionPort: Send + Sync {
    fn execute(&self, context: &StepContext) -> Result<(), BddError>;
    fn pattern(&self) -> &str;
}

pub struct StepContext {
    pub text: String,
    pub parameters: std::collections::HashMap<String, String>,
}

impl StepContext {
    pub fn new(text: impl Into<String>) -> Self {
        Self {
            text: text.into(),
            parameters: std::collections::HashMap::new(),
        }
    }
}

pub trait ReportWriterPort: Send + Sync {
    fn write_report(&self, result: &FeatureResult) -> Result<String, BddError>;
    fn write_report_to_file(&self, result: &FeatureResult, path: &str) -> Result<(), BddError>;
}

pub trait FeatureLoaderPort: Send + Sync {
    fn load_feature(&self, path: &str) -> Result<String, BddError>;
    fn load_features_in_dir(&self, dir: &str) -> Result<Vec<(String, String)>, BddError>;
}

pub trait MetricsPort: Send + Sync {
    fn record_scenario(&self, result: &ScenarioResult);
    fn record_feature(&self, result: &FeatureResult);
    fn summary(&self) -> MetricsSummary;
}

#[derive(Debug, Default)]
pub struct MetricsSummary {
    pub total_scenarios: usize,
    pub passed: usize,
    pub failed: usize,
    pub pending: usize,
    pub duration_ms: u64,
}
