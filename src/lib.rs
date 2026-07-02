//! agentkit - Agent Framework
//!
//! A hexagonal architecture framework for building AI agents with
//! skill systems, tool registries, and memory management.

pub mod adapters;
pub mod application;
pub mod domain;
pub mod infrastructure;

pub mod prelude {
    pub use crate::adapters::substrate::{SkillRegistry, ToolRegistry};
    pub use crate::application::*;
    pub use crate::domain::agents::*;
    pub use crate::domain::context::*;
    pub use crate::domain::memory::*;
    pub use crate::domain::skills::*;
    pub use crate::domain::tools::*;
}

pub use adapters::substrate::{SkillRegistry, ToolRegistry};
pub use domain::agents::Agent;
pub use domain::context::{Context, Output};
pub use domain::memory::{MemoryEntry, MemoryStore};
pub use domain::skills::{Skill, SkillResult};
pub use domain::tools::{Tool, ToolCall, ToolResponse};
pub use infrastructure::error::{Error, Result};
pub use domain::errors::ErrorEnvelope;
