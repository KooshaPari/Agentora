//! Phenotype BDD - Gherkin-style testing framework with hexagonal architecture
//! @trace INFRA-001: Multi-Cloud Support
//! @trace INFRA-002: State Management
//! @trace INFRA-003: Resource Provisioning
//! @trace INFRA-004: Secret Management
//! @trace INFRA-005: Drift Detection
//! @trace INFRA-006: Plan Generation

#![allow(missing_docs)]
#![warn(clippy::all)]

pub mod adapters;
pub mod application;
pub mod domain;
pub mod error;

pub use adapters::loader::FileLoader;
pub use adapters::parser::GherkinParser;
pub use adapters::reporter::JsonReporter;
pub use application::runner::BddAppRunner;
pub use domain::entities::*;
pub use domain::ports::{StepContext, StepDefinitionPort};
pub use domain::services::{FeatureRunner, ScenarioExecutor, StepMatcher, StepRegistry};
pub use error::BddError;

pub const VERSION: &str = env!("CARGO_PKG_VERSION");

pub mod prelude {
    pub use crate::adapters::{loader::FileLoader, parser::GherkinParser, reporter::JsonReporter};
    pub use crate::application::runner::BddAppRunner;
    pub use crate::domain::entities::*;
    pub use crate::domain::ports::{StepContext, StepDefinitionPort};
    pub use crate::domain::services::{FeatureRunner, ScenarioExecutor, StepMatcher, StepRegistry};
    pub use crate::error::BddError;
}

#[cfg(test)]
mod tests {
    use super::*;

    // Traces to: FR-BDD-001 - Core domain types exist
    #[test]
    fn test_version_available() {
        assert!(!VERSION.is_empty());
    }

    // Traces to: FR-BDD-002 - Public API exports
    // Traces to: FR-BDD-002 - Public API exports
    #[test]
    #[allow(unused_imports)]
    fn test_prelude_imports() {
        use prelude::*;
    }
}
