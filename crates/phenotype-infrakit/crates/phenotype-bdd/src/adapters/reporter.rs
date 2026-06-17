use crate::domain::entities::FeatureResult;
use crate::BddError;
use serde_json;

pub struct JsonReporter;

impl std::fmt::Debug for JsonReporter {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("JsonReporter").finish()
    }
}

impl JsonReporter {
    pub fn new() -> Self {
        Self
    }

    pub fn write_report(&self, result: &FeatureResult) -> Result<String, BddError> {
        serde_json::to_string_pretty(result)
            .map_err(|e| BddError::Other(format!("serialization failed: {}", e)))
    }

    pub fn write_report_to_file(&self, result: &FeatureResult, path: &str) -> Result<(), BddError> {
        let json = self.write_report(result)?;
        std::fs::write(path, json).map_err(BddError::IoError)
    }
}

impl Default for JsonReporter {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::domain::entities::*;
    use chrono::Utc;

    fn make_result() -> FeatureResult {
        FeatureResult {
            feature_id: uuid::Uuid::new_v4(),
            feature_name: "Test".into(),
            scenario_results: vec![ScenarioResult {
                scenario_id: uuid::Uuid::new_v4(),
                scenario_name: "A".into(),
                step_results: vec![(uuid::Uuid::new_v4(), StepResult::Passed)],
                duration_ms: 10,
                started_at: Utc::now(),
                completed_at: Utc::now(),
            }],
            status: ExecutionStatus::Passed,
            started_at: Utc::now(),
            completed_at: Utc::now(),
        }
    }

    // Traces to: FR-BDD-040 - JSON serialization
    #[test]
    fn test_json_serialization() {
        let reporter = JsonReporter::new();
        let result = make_result();
        let json = reporter.write_report(&result).unwrap();
        assert!(json.contains("Test"));
    }

    // Traces to: FR-BDD-041 - JSON write to file
    #[test]
    fn test_json_write_to_file() {
        let reporter = JsonReporter::new();
        let result = make_result();
        let path = std::env::temp_dir().join("bdd-test-report.json");
        reporter
            .write_report_to_file(&result, path.to_str().unwrap())
            .unwrap();
        let content = std::fs::read_to_string(&path).unwrap();
        assert!(content.contains("Test"));
        let _ = std::fs::remove_file(&path);
    }
}
