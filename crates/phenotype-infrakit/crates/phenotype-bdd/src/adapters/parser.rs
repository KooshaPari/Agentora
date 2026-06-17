use crate::domain::entities::*;
use crate::BddError;
use gherkin::{Feature as GherkinFeature, GherkinEnv};

pub struct GherkinParser;

impl std::fmt::Debug for GherkinParser {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("GherkinParser").finish()
    }
}

impl GherkinParser {
    pub fn new() -> Self {
        Self
    }

    pub fn parse_feature(&self, content: &str, source: Option<&str>) -> Result<Feature, BddError> {
        let env = GherkinEnv::default();
        let gherkin_feature = GherkinFeature::parse(content, env)
            .map_err(|e| BddError::ParseError(format!("{}", e)))?;

        let mut feature = Feature::new(&gherkin_feature.name);

        if let Some(desc) = &gherkin_feature.description {
            let trimmed = desc.trim().to_string();
            if !trimmed.is_empty() {
                feature = feature.with_description(trimmed);
            }
        }

        if let Some(file) = source {
            feature = feature.with_source(file, gherkin_feature.position.line);
        }

        if let Some(bg) = &gherkin_feature.background {
            let steps: Vec<Step> = bg.steps.iter().map(convert_step).collect();
            feature = feature.with_background(Background::new(steps));
        }

        for scenario in &gherkin_feature.scenarios {
            let mut domain_scenario = Scenario::new(&scenario.name);

            for tag in &scenario.tags {
                domain_scenario = domain_scenario.with_tag(tag.clone());
            }

            for step in &scenario.steps {
                domain_scenario = domain_scenario.with_step(convert_step(step));
            }

            for examples in &scenario.examples {
                if let Some(table) = &examples.table {
                    if table.rows.len() >= 2 {
                        let headers = table.rows[0].clone();
                        let rows: Vec<Vec<String>> = table.rows[1..].to_vec();
                        domain_scenario =
                            domain_scenario.with_examples(Examples::new(headers, rows));
                    }
                }
            }

            feature = feature.with_scenario(domain_scenario);
        }

        Ok(feature)
    }
}

impl Default for GherkinParser {
    fn default() -> Self {
        Self::new()
    }
}

fn convert_step(step: &gherkin::Step) -> Step {
    let step_type = match step.ty {
        gherkin::StepType::Given => StepType::Given,
        gherkin::StepType::When => StepType::When,
        gherkin::StepType::Then => StepType::Then,
    };

    let mut s = Step::new(step_type, &step.value);

    if let Some(table) = &step.table {
        s = s.with_data_table(DataTable::new(table.rows.clone()));
    }

    if let Some(doc) = &step.docstring {
        s = s.with_doc_string(DocString::new(doc));
    }

    s
}

#[cfg(test)]
mod tests {
    use super::*;

    // Traces to: FR-BDD-030 - Parse simple feature
    #[test]
    fn test_parse_simple_feature() {
        let content = r#"
Feature: Calculator
  Scenario: Add two numbers
    Given I have a calculator
    When I add 2 and 3
    Then the result is 5
"#;
        let parser = GherkinParser::new();
        let feature = parser.parse_feature(content, Some("test.feature")).unwrap();
        assert_eq!(feature.name, "Calculator");
        assert_eq!(feature.scenarios.len(), 1);
        assert_eq!(feature.scenarios[0].steps.len(), 3);
    }

    // Traces to: FR-BDD-031 - Parse feature with tags
    #[test]
    fn test_parse_feature_with_tags() {
        let content = r#"
Feature: Login
  @smoke @auth
  Scenario: Valid login
    Given I am on login page
    When I enter valid credentials
    Then I see the dashboard
"#;
        let parser = GherkinParser::new();
        let feature = parser.parse_feature(content, None).unwrap();
        assert!(feature.scenarios[0].tags.contains(&"smoke".to_string()));
        assert!(feature.scenarios[0].tags.contains(&"auth".to_string()));
    }

    // Traces to: FR-BDD-032 - Parse feature with background
    #[test]
    fn test_parse_feature_with_background() {
        let content = r#"
Feature: Shopping
  Background:
    Given I am logged in

  Scenario: View cart
    When I go to cart
    Then cart is empty
"#;
        let parser = GherkinParser::new();
        let feature = parser.parse_feature(content, None).unwrap();
        assert!(feature.background.is_some());
    }

    // Traces to: FR-BDD-033 - Parse scenario outline
    #[test]
    fn test_parse_scenario_outline() {
        let content = r#"
Feature: Math
  Scenario Outline: Add
    Given I have <a> and <b>
    Then result is <sum>

    Examples:
      | a | b | sum |
      | 1 | 2 | 3   |
      | 4 | 5 | 9   |
"#;
        let parser = GherkinParser::new();
        let feature = parser.parse_feature(content, None).unwrap();
        let expanded = feature.scenarios[0].expand();
        assert_eq!(expanded.len(), 2);
    }
}
