//! Domain entities representing Gherkin language constructs

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Feature {
    pub id: Uuid,
    pub name: String,
    pub description: Option<String>,
    pub tags: Vec<String>,
    pub scenarios: Vec<Scenario>,
    pub background: Option<Background>,
    pub source_file: Option<String>,
    pub line_number: usize,
    pub parsed_at: DateTime<Utc>,
}

impl Feature {
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            id: Uuid::new_v4(),
            name: name.into(),
            description: None,
            tags: Vec::new(),
            scenarios: Vec::new(),
            background: None,
            source_file: None,
            line_number: 0,
            parsed_at: Utc::now(),
        }
    }

    pub fn with_description(mut self, description: impl Into<String>) -> Self {
        self.description = Some(description.into());
        self
    }

    pub fn with_tags(mut self, tags: Vec<String>) -> Self {
        self.tags = tags;
        self
    }

    pub fn with_scenario(mut self, scenario: Scenario) -> Self {
        self.scenarios.push(scenario);
        self
    }

    pub fn with_background(mut self, background: Background) -> Self {
        self.background = Some(background);
        self
    }

    pub fn with_source(mut self, file: impl Into<String>, line: usize) -> Self {
        self.source_file = Some(file.into());
        self.line_number = line;
        self
    }

    pub fn scenarios_with_tags(&self, tags: &[String]) -> Vec<&Scenario> {
        if tags.is_empty() {
            return self.scenarios.iter().collect();
        }
        self.scenarios
            .iter()
            .filter(|s| tags.iter().any(|t| s.tags.contains(t)))
            .collect()
    }

    pub fn total_steps(&self) -> usize {
        self.scenarios.iter().map(|s| s.steps.len()).sum()
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Background {
    pub description: Option<String>,
    pub steps: Vec<Step>,
    pub line_number: usize,
}

impl Background {
    pub fn new(steps: Vec<Step>) -> Self {
        Self {
            description: None,
            steps,
            line_number: 0,
        }
    }

    pub fn with_description(mut self, desc: impl Into<String>) -> Self {
        self.description = Some(desc.into());
        self
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Scenario {
    pub id: Uuid,
    pub name: String,
    pub tags: Vec<String>,
    pub steps: Vec<Step>,
    pub examples: Option<Examples>,
    pub line_number: usize,
}

impl Scenario {
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            id: Uuid::new_v4(),
            name: name.into(),
            tags: Vec::new(),
            steps: Vec::new(),
            examples: None,
            line_number: 0,
        }
    }

    pub fn with_step(mut self, step: Step) -> Self {
        self.steps.push(step);
        self
    }

    pub fn with_tags(mut self, tags: Vec<String>) -> Self {
        self.tags = tags;
        self
    }

    pub fn with_tag(mut self, tag: impl Into<String>) -> Self {
        self.tags.push(tag.into());
        self
    }

    pub fn with_examples(mut self, examples: Examples) -> Self {
        self.examples = Some(examples);
        self
    }

    pub fn scenario_type(&self) -> ScenarioType {
        if self.examples.is_some() {
            ScenarioType::Outline
        } else {
            ScenarioType::Regular
        }
    }

    pub fn expand(&self) -> Vec<Scenario> {
        match &self.examples {
            None => vec![self.clone()],
            Some(examples) => examples
                .rows
                .iter()
                .map(|row| {
                    let mut expanded = self.clone();
                    expanded.id = Uuid::new_v4();
                    expanded.examples = None;
                    expanded.steps = self
                        .steps
                        .iter()
                        .map(|step| {
                            let mut new_step = step.clone();
                            new_step.text = examples.replace_parameters(&step.text, row);
                            new_step
                        })
                        .collect();
                    expanded
                })
                .collect(),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ScenarioType {
    Regular,
    Outline,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Step {
    pub id: Uuid,
    pub step_type: StepType,
    pub text: String,
    pub data_table: Option<DataTable>,
    pub doc_string: Option<DocString>,
    pub line_number: usize,
}

impl Step {
    pub fn new(step_type: StepType, text: impl Into<String>) -> Self {
        Self {
            id: Uuid::new_v4(),
            step_type,
            text: text.into(),
            data_table: None,
            doc_string: None,
            line_number: 0,
        }
    }

    pub fn with_data_table(mut self, table: DataTable) -> Self {
        self.data_table = Some(table);
        self
    }

    pub fn with_doc_string(mut self, doc: DocString) -> Self {
        self.doc_string = Some(doc);
        self
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum StepType {
    Given,
    When,
    Then,
    And,
    But,
    Star,
}

impl StepType {
    pub fn keyword(&self) -> &'static str {
        match self {
            StepType::Given => "Given",
            StepType::When => "When",
            StepType::Then => "Then",
            StepType::And => "And",
            StepType::But => "But",
            StepType::Star => "*",
        }
    }

    pub fn resolve(&self, context: Option<StepType>) -> StepType {
        match self {
            StepType::And | StepType::But | StepType::Star => context.unwrap_or(StepType::Given),
            concrete => *concrete,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DataTable {
    pub rows: Vec<Vec<String>>,
}

impl DataTable {
    pub fn new(rows: Vec<Vec<String>>) -> Self {
        Self { rows }
    }

    pub fn headers(&self) -> Option<&Vec<String>> {
        self.rows.first()
    }

    pub fn data_rows(&self) -> &[Vec<String>] {
        if self.rows.len() > 1 {
            &self.rows[1..]
        } else {
            &[]
        }
    }

    pub fn as_maps(&self) -> Vec<HashMap<String, String>> {
        match self.headers() {
            None => Vec::new(),
            Some(headers) => self
                .data_rows()
                .iter()
                .map(|row| {
                    headers
                        .iter()
                        .zip(row.iter())
                        .map(|(h, v)| (h.clone(), v.clone()))
                        .collect()
                })
                .collect(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DocString {
    pub content_type: Option<String>,
    pub content: String,
}

impl DocString {
    pub fn new(content: impl Into<String>) -> Self {
        Self {
            content_type: None,
            content: content.into(),
        }
    }

    pub fn with_content_type(mut self, ct: impl Into<String>) -> Self {
        self.content_type = Some(ct.into());
        self
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Examples {
    pub headers: Vec<String>,
    pub rows: Vec<Vec<String>>,
}

impl Examples {
    pub fn new(headers: Vec<String>, rows: Vec<Vec<String>>) -> Self {
        Self { headers, rows }
    }

    pub fn replace_parameters(&self, text: &str, row: &[String]) -> String {
        let mut result = text.to_string();
        for (i, header) in self.headers.iter().enumerate() {
            if let Some(value) = row.get(i) {
                let placeholder = format!("<{}>", header);
                result = result.replace(&placeholder, value);
            }
        }
        result
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum StepResult {
    Passed,
    Failed { error: String, location: String },
    Skipped { reason: String },
    Pending { reason: String },
    Ambiguous { matches: Vec<String> },
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ScenarioResult {
    pub scenario_id: Uuid,
    pub scenario_name: String,
    pub step_results: Vec<(Uuid, StepResult)>,
    pub duration_ms: u64,
    pub started_at: DateTime<Utc>,
    pub completed_at: DateTime<Utc>,
}

impl ScenarioResult {
    pub fn status(&self) -> ExecutionStatus {
        if self
            .step_results
            .iter()
            .any(|(_, r)| matches!(r, StepResult::Failed { .. } | StepResult::Ambiguous { .. }))
        {
            ExecutionStatus::Failed
        } else if self
            .step_results
            .iter()
            .all(|(_, r)| matches!(r, StepResult::Passed))
        {
            ExecutionStatus::Passed
        } else if self
            .step_results
            .iter()
            .any(|(_, r)| matches!(r, StepResult::Pending { .. }))
        {
            ExecutionStatus::Pending
        } else {
            ExecutionStatus::Skipped
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct FeatureResult {
    pub feature_id: Uuid,
    pub feature_name: String,
    pub scenario_results: Vec<ScenarioResult>,
    pub status: ExecutionStatus,
    pub started_at: DateTime<Utc>,
    pub completed_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ExecutionStatus {
    Passed,
    Failed,
    Pending,
    Skipped,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_feature_creation() {
        let feature = Feature::new("Calculator Addition")
            .with_description("Basic arithmetic")
            .with_tags(vec!["math".to_string()]);
        assert_eq!(feature.name, "Calculator Addition");
    }

    #[test]
    fn test_scenario_with_steps() {
        let scenario = Scenario::new("Add two numbers")
            .with_step(Step::new(StepType::Given, "I have a calculator"))
            .with_step(Step::new(StepType::When, "I add 1 and 2"))
            .with_step(Step::new(StepType::Then, "the result should be 3"));
        assert_eq!(scenario.steps.len(), 3);
    }

    #[test]
    fn test_data_table_as_maps() {
        let table = DataTable::new(vec![
            vec!["name".to_string(), "age".to_string()],
            vec!["Alice".to_string(), "30".to_string()],
        ]);
        let maps = table.as_maps();
        assert_eq!(maps.len(), 1);
        assert_eq!(maps[0].get("name"), Some(&"Alice".to_string()));
    }

    #[test]
    fn test_scenario_outline_expansion() {
        let examples = Examples::new(
            vec!["x".to_string(), "y".to_string(), "sum".to_string()],
            vec![vec!["1".to_string(), "2".to_string(), "3".to_string()]],
        );
        let scenario = Scenario::new("Add <x> and <y>")
            .with_step(Step::new(StepType::Given, "I have <x> and <y>"))
            .with_examples(examples);
        let expanded = scenario.expand();
        assert_eq!(expanded.len(), 1);
    }

    #[test]
    fn test_step_type_resolution() {
        assert_eq!(
            StepType::And.resolve(Some(StepType::Given)),
            StepType::Given
        );
        assert_eq!(StepType::When.resolve(None), StepType::When);
    }
}
