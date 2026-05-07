//! agentkit - Agent Framework
//!
//! A hexagonal architecture framework for building AI agents with
//! skill systems, tool registries, and memory management.

pub mod domain;
pub mod application;
pub mod adapters;
pub mod infrastructure;

pub mod prelude {
    pub use crate::domain::agents::*;
    pub use crate::domain::skills::*;
    pub use crate::domain::tools::*;
    pub use crate::domain::memory::*;
    pub use crate::domain::context::*;
    pub use crate::application::*;
}

pub use domain::agents::Agent;
pub use domain::skills::{Skill, SkillRegistry};
pub use domain::tools::{Tool, ToolRegistry, ToolCall};
pub use domain::memory::{MemoryEntry, MemoryStore};
pub use domain::context::{Context, Output};
pub use infrastructure::error::{Error, Result};
