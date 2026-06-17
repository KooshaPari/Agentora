//! Rule-based intent classifier for triage.
//!
//! Classifies free-text input into one of: Bug, Feature, Idea, Task.
//! Uses keyword matching and pattern rules. Defaults to Task when ambiguous.
//!
//! Traceability: WP17-T098b, T100

pub use agileplus_domain::domain::backlog::Intent;
use serde::{Deserialize, Serialize};

/// Result of classifying input text.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TriageResult {
    pub intent: Intent,
    pub confidence: f64,
    pub matched_keywords: Vec<String>,
    pub raw_input: String,
}

/// Rule-based triage classifier.
#[derive(Debug, Default)]
pub struct TriageClassifier {
    rules: Vec<ClassifierRule>,
}

#[derive(Debug)]
struct ClassifierRule {
    intent: Intent,
    keywords: Vec<&'static str>,
    weight: f64,
}

impl TriageClassifier {
    pub fn new() -> Self {
        Self {
            rules: vec![
                ClassifierRule {
                    intent: Intent::Bug,
                    keywords: vec![
                        "bug",
                        "error",
                        "crash",
                        "panic",
                        "broken",
                        "fix",
                        "regression",
                        "failing",
                        "failed",
                        "segfault",
                        "exception",
                        "stack trace",
                        "null pointer",
                        "undefined",
                        "404",
                        "500",
                        "timeout",
                        "does not work",
                        "doesn't work",
                        "not working",
                    ],
                    weight: 1.0,
                },
                ClassifierRule {
                    intent: Intent::Feature,
                    keywords: vec![
                        "feature",
                        "add",
                        "implement",
                        "create",
                        "build",
                        "new",
                        "support",
                        "enable",
                        "integrate",
                        "endpoint",
                        "api",
                        "should be able to",
                        "want to",
                        "need to",
                    ],
                    weight: 0.9,
                },
                ClassifierRule {
                    intent: Intent::Idea,
                    keywords: vec![
                        "idea",
                        "maybe",
                        "could",
                        "what if",
                        "consider",
                        "explore",
                        "brainstorm",
                        "suggestion",
                        "proposal",
                        "experiment",
                        "would be nice",
                        "nice to have",
                        "someday",
                    ],
                    weight: 0.8,
                },
                ClassifierRule {
                    intent: Intent::Task,
                    keywords: vec![
                        "task",
                        "todo",
                        "refactor",
                        "cleanup",
                        "update",
                        "upgrade",
                        "migrate",
                        "rename",
                        "move",
                        "reorganize",
                        "document",
                        "test",
                        "benchmark",
                        "optimize",
                        "deploy",
                    ],
                    weight: 0.7,
                },
            ],
        }
    }

    /// Classify input text into an intent.
    pub fn classify(&self, input: &str) -> TriageResult {
        let lower = input.to_lowercase();
        let mut best_intent = Intent::Task;
        let mut best_score = 0.0;
        let mut best_keywords = Vec::new();

        for rule in &self.rules {
            let mut matches = Vec::new();
            for &kw in &rule.keywords {
                if lower.contains(kw) {
                    matches.push(kw.to_string());
                }
            }
            if !matches.is_empty() {
                let score = matches.len() as f64 * rule.weight;
                if score > best_score {
                    best_score = score;
                    best_intent = rule.intent;
                    best_keywords = matches;
                }
            }
        }

        let confidence = if best_keywords.is_empty() {
            0.3 // Default to task with low confidence
        } else {
            (best_score / 3.0).clamp(0.4, 1.0)
        };

        TriageResult {
            intent: best_intent,
            confidence,
            matched_keywords: best_keywords,
            raw_input: input.to_string(),
        }
    }

    /// Classify with an explicit override intent.
    pub fn classify_with_override(&self, input: &str, override_intent: Intent) -> TriageResult {
        TriageResult {
            intent: override_intent,
            confidence: 1.0,
            matched_keywords: vec!["user-override".to_string()],
            raw_input: input.to_string(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn classify_bug() {
        let c = TriageClassifier::new();
        let r = c.classify("There's a crash when I click the button");
        assert_eq!(r.intent, Intent::Bug);
        assert!(r.confidence > 0.3);
    }

    #[test]
    fn classify_feature() {
        let c = TriageClassifier::new();
        let r = c.classify("Add a new endpoint for user profiles");
        assert_eq!(r.intent, Intent::Feature);
    }

    #[test]
    fn classify_idea() {
        let c = TriageClassifier::new();
        let r = c.classify("What if we could explore a different approach");
        assert_eq!(r.intent, Intent::Idea);
    }

    #[test]
    fn classify_task_default() {
        let c = TriageClassifier::new();
        let r = c.classify("something generic with no keywords");
        assert_eq!(r.intent, Intent::Task);
        assert!(r.confidence <= 0.3);
    }

    #[test]
    fn classify_override() {
        let c = TriageClassifier::new();
        let r = c.classify_with_override("some text", Intent::Bug);
        assert_eq!(r.intent, Intent::Bug);
        assert_eq!(r.confidence, 1.0);
    }

    #[test]
    fn classify_multi_keyword_bug() {
        let c = TriageClassifier::new();
        let r = c.classify("error: panic crash in production, stack trace attached");
        assert_eq!(r.intent, Intent::Bug);
        assert!(r.matched_keywords.len() >= 3);
    }

    #[test]
    fn classify_task_explicit() {
        let c = TriageClassifier::new();
        let r = c.classify("refactor the authentication module and update tests");
        assert_eq!(r.intent, Intent::Task);
    }
}
