//! Rule-based validation engine

use crate::types::{Severity, ValidationContext, ValidationIssue, ValidationResult};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Rule {
    pub id: String,
    pub description: Option<String>,
    pub target: String,
    pub condition: Condition,
    pub severity: Severity,
    pub message: Option<String>,
    pub metadata: HashMap<String, serde_json::Value>,
}

impl Rule {
    pub fn new(id: impl Into<String>, target: impl Into<String>, condition: Condition) -> Self {
        Self {
            id: id.into(),
            description: None,
            target: target.into(),
            condition,
            severity: Severity::Error,
            message: None,
            metadata: HashMap::new(),
        }
    }

    pub fn with_description(mut self, desc: impl Into<String>) -> Self {
        self.description = Some(desc.into());
        self
    }

    pub fn with_severity(mut self, severity: Severity) -> Self {
        self.severity = severity;
        self
    }

    pub fn with_message(mut self, message: impl Into<String>) -> Self {
        self.message = Some(message.into());
        self
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum Condition {
    Required,
    NotEmpty,
    Pattern {
        regex: String,
    },
    In {
        values: Vec<serde_json::Value>,
    },
    Comparison {
        operator: Operator,
        value: serde_json::Value,
    },
    Length {
        min: Option<usize>,
        max: Option<usize>,
    },
    Range {
        min: Option<serde_json::Value>,
        max: Option<serde_json::Value>,
    },
    Type {
        expected: JsonType,
    },
    Custom {
        function: String,
        params: HashMap<String, serde_json::Value>,
    },
    Object {
        rules: Vec<Rule>,
    },
    Array {
        element_rules: Vec<Rule>,
        min_items: Option<usize>,
        max_items: Option<usize>,
    },
    And {
        conditions: Vec<Condition>,
    },
    Or {
        conditions: Vec<Condition>,
    },
    Not {
        condition: Box<Condition>,
    },
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum JsonType {
    String,
    Number,
    Integer,
    Boolean,
    Array,
    Object,
    Null,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Operator {
    Eq,
    Ne,
    Gt,
    Gte,
    Lt,
    Lte,
}

pub struct RuleEngine {
    rules: Vec<Rule>,
    custom_validators: HashMap<String, Box<dyn CustomValidator>>,
}

pub trait CustomValidator: Send + Sync {
    fn validate(
        &self,
        value: &serde_json::Value,
        params: &HashMap<String, serde_json::Value>,
    ) -> bool;
}

impl RuleEngine {
    pub fn new() -> Self {
        Self {
            rules: Vec::new(),
            custom_validators: HashMap::new(),
        }
    }

    pub fn add_rule(&mut self, rule: Rule) {
        self.rules.push(rule);
    }

    pub fn add_rules(&mut self, rules: Vec<Rule>) {
        self.rules.extend(rules);
    }

    pub fn register_validator(
        &mut self,
        name: impl Into<String>,
        validator: Box<dyn CustomValidator>,
    ) {
        self.custom_validators.insert(name.into(), validator);
    }

    pub fn evaluate(&self, context: &ValidationContext) -> ValidationResult {
        let mut result = ValidationResult::success();
        for rule in &self.rules {
            if let Some(issue) = self.evaluate_rule(rule, context) {
                if issue.is_error() {
                    result.add_error(issue);
                } else {
                    result.add_warning(issue);
                }
            }
        }
        result
    }

    fn evaluate_rule(&self, rule: &Rule, context: &ValidationContext) -> Option<ValidationIssue> {
        let value = context.get_path(&rule.target);
        let passes = match &rule.condition {
            Condition::Required => value.is_some(),
            Condition::NotEmpty => {
                if let Some(v) = value {
                    !v.is_null() && v != &serde_json::json!("")
                } else {
                    false
                }
            }
            Condition::Pattern { regex } => value
                .and_then(|v| v.as_str())
                .map(|s| {
                    regex::Regex::new(regex)
                        .ok()
                        .map(|r| r.is_match(s))
                        .unwrap_or(false)
                })
                .unwrap_or(false),
            Condition::In { values } => value.map(|v| values.contains(v)).unwrap_or(false),
            Condition::Comparison {
                operator,
                value: expected,
            } => value
                .map(|v| compare_values(v, expected, *operator))
                .unwrap_or(false),
            Condition::Length { min, max } => value
                .map(|v| {
                    let len = v.as_str().map(|s| s.len()).unwrap_or(0);
                    min.map(|m| len >= m).unwrap_or(true) && max.map(|m| len <= m).unwrap_or(true)
                })
                .unwrap_or(false),
            _ => true,
        };
        if passes {
            None
        } else {
            Some(ValidationIssue::error(
                &rule.id,
                &rule
                    .message
                    .clone()
                    .unwrap_or_else(|| format!("Rule {} failed", rule.id)),
            ))
        }
    }
}

impl Default for RuleEngine {
    fn default() -> Self {
        Self::new()
    }
}

fn compare_values(left: &serde_json::Value, right: &serde_json::Value, op: Operator) -> bool {
    match (left, right) {
        (serde_json::Value::Number(l), serde_json::Value::Number(r)) => {
            if let (Some(lf), Some(rf)) = (l.as_f64(), r.as_f64()) {
                match op {
                    Operator::Eq => (lf - rf).abs() < f64::EPSILON,
                    Operator::Ne => (lf - rf).abs() >= f64::EPSILON,
                    Operator::Gt => lf > rf,
                    Operator::Gte => lf >= rf,
                    Operator::Lt => lf < rf,
                    Operator::Lte => lf <= rf,
                }
            } else {
                false
            }
        }
        (serde_json::Value::String(l), serde_json::Value::String(r)) => match op {
            Operator::Eq => l == r,
            Operator::Ne => l != r,
            Operator::Gt => l > r,
            Operator::Gte => l >= r,
            Operator::Lt => l < r,
            Operator::Lte => l <= r,
        },
        _ => false,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_rule_creation() {
        let rule = Rule::new("email_required", "user.email", Condition::Required)
            .with_description("Email is required")
            .with_message("Please provide an email");
        assert_eq!(rule.id, "email_required");
    }

    #[test]
    fn test_rule_engine_evaluate() {
        let mut engine = RuleEngine::new();
        engine.add_rule(Rule::new("required_name", "name", Condition::Required));
        let ctx = ValidationContext::from_json(serde_json::json!({"name": "John"}));
        let result = engine.evaluate(&ctx);
        assert!(result.is_valid);
    }
}
