//! CLAUDE.md and AGENTS.md prompt router generation.
//!
//! Generates project-aware governance files from detected project config.
//!
//! Traceability: WP17-T101, T102

use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;
use std::fmt::Write;

/// Project configuration detected during init/scan.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ProjectConfig {
    pub name: String,
    pub languages: BTreeSet<String>,
    pub frameworks: BTreeSet<String>,
    pub has_tests: bool,
    pub has_ci: bool,
    pub test_command: Option<String>,
    pub lint_command: Option<String>,
}

/// Router generator for governance files.
#[derive(Debug)]
pub struct RouterGenerator {
    config: ProjectConfig,
}

impl RouterGenerator {
    pub fn new(config: ProjectConfig) -> Self {
        Self { config }
    }

    /// Generate CLAUDE.md content.
    pub fn generate_claude_md(&self) -> String {
        let mut out = String::new();
        writeln!(out, "# Project Governance — {}", self.config.name).unwrap();
        writeln!(out).unwrap();
        writeln!(out, "## Overview").unwrap();
        writeln!(out).unwrap();
        writeln!(
            out,
            "This project is managed by AgilePlus spec-driven development."
        )
        .unwrap();
        writeln!(out).unwrap();

        if !self.config.languages.is_empty() {
            let langs: Vec<&str> = self.config.languages.iter().map(|s| s.as_str()).collect();
            writeln!(out, "**Languages**: {}", langs.join(", ")).unwrap();
        }
        if !self.config.frameworks.is_empty() {
            let fws: Vec<&str> = self.config.frameworks.iter().map(|s| s.as_str()).collect();
            writeln!(out, "**Frameworks**: {}", fws.join(", ")).unwrap();
        }
        writeln!(out).unwrap();

        writeln!(out, "## Rules").unwrap();
        writeln!(out).unwrap();
        writeln!(out, "- Follow the spec-driven workflow: specify → research → plan → implement → validate → ship → retro.").unwrap();
        writeln!(out, "- Never commit directly to `main`. All work goes through feature branches via `agileplus implement`.").unwrap();
        writeln!(
            out,
            "- Run `agileplus validate --feature <slug>` before shipping."
        )
        .unwrap();
        writeln!(
            out,
            "- Prefer existing patterns and conventions found in the codebase."
        )
        .unwrap();
        writeln!(out, "- Write tests for new functionality.").unwrap();
        writeln!(
            out,
            "- Keep commits atomic and well-described (imperative mood)."
        )
        .unwrap();

        if let Some(ref cmd) = self.config.test_command {
            writeln!(out, "- Run `{cmd}` before committing.").unwrap();
        }
        if let Some(ref cmd) = self.config.lint_command {
            writeln!(out, "- Run `{cmd}` for linting.").unwrap();
        }

        writeln!(out).unwrap();
        writeln!(out, "## Agent Coordination").unwrap();
        writeln!(out).unwrap();
        writeln!(
            out,
            "- Use `.agileplus/` for project state (SQLite DB, configs)."
        )
        .unwrap();
        writeln!(
            out,
            "- Do not modify `.agileplus/agileplus.db` directly — use CLI commands."
        )
        .unwrap();
        writeln!(
            out,
            "- Worktrees are managed via `agileplus implement` and live in `.worktrees/`."
        )
        .unwrap();

        // Phase-based first-action routing
        writeln!(out).unwrap();
        writeln!(out, "## First-Action Routing").unwrap();
        writeln!(out).unwrap();
        writeln!(out, "When starting work on a feature, select the appropriate command based on its current state:").unwrap();
        writeln!(out).unwrap();
        writeln!(out, "| State | Action | Command |").unwrap();
        writeln!(out, "|-------|--------|---------|").unwrap();
        writeln!(
            out,
            "| New | Create spec | `agileplus specify --feature <slug>` |"
        )
        .unwrap();
        writeln!(
            out,
            "| Specified | Research feasibility | `agileplus research --feature <slug>` |"
        )
        .unwrap();
        writeln!(
            out,
            "| Researched | Generate plan | `agileplus plan --feature <slug>` |"
        )
        .unwrap();
        writeln!(
            out,
            "| Planned | Implement WPs | `agileplus implement --feature <slug> --wp <id>` |"
        )
        .unwrap();
        writeln!(
            out,
            "| Implementing | Validate governance | `agileplus validate --feature <slug>` |"
        )
        .unwrap();
        writeln!(
            out,
            "| Validated | Ship feature | `agileplus ship --feature <slug>` |"
        )
        .unwrap();
        writeln!(
            out,
            "| Shipped | Run retrospective | `agileplus retrospective --feature <slug>` |"
        )
        .unwrap();

        out
    }

    /// Generate AGENTS.md content.
    pub fn generate_agents_md(&self) -> String {
        let mut out = String::new();
        writeln!(out, "# Agent Behavioral Rules — {}", self.config.name).unwrap();
        writeln!(out).unwrap();
        writeln!(out, "## Binding Rules").unwrap();
        writeln!(out).unwrap();
        writeln!(out, "1. **Path references**: All file mentions must use absolute or repo-root-relative paths.").unwrap();
        writeln!(
            out,
            "2. **UTF-8 encoding**: No smart quotes, em-dashes, or Windows-1252 characters."
        )
        .unwrap();
        writeln!(
            out,
            "3. **Context management**: Build context incrementally; avoid redundant file reads."
        )
        .unwrap();
        writeln!(out, "4. **Work quality**: Code must be secure, tested, and documented. Prefer existing patterns.").unwrap();
        writeln!(
            out,
            "5. **Git discipline**: Meaningful commits in imperative mood. Never commit secrets."
        )
        .unwrap();
        writeln!(out, "6. **Agent directories**: Never commit `.claude/`, `.codex/`, `.cursor/` etc. to version control.").unwrap();
        writeln!(out).unwrap();
        writeln!(out, "## Workflow").unwrap();
        writeln!(out).unwrap();
        writeln!(out, "- All feature work uses AgilePlus CLI commands.").unwrap();
        writeln!(
            out,
            "- State transitions are tracked in `.agileplus/agileplus.db`."
        )
        .unwrap();
        writeln!(
            out,
            "- Governance contracts are enforced by `agileplus validate`."
        )
        .unwrap();
        writeln!(out).unwrap();
        writeln!(out, "## Triage").unwrap();
        writeln!(out).unwrap();
        writeln!(
            out,
            "- Use `agileplus triage` to classify incoming items (bug/feature/idea/task)."
        )
        .unwrap();
        writeln!(out, "- Use `agileplus queue list` to see the backlog.").unwrap();
        writeln!(
            out,
            "- Use `agileplus queue pop` to pick up the next highest-priority item."
        )
        .unwrap();

        out
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_config() -> ProjectConfig {
        ProjectConfig {
            name: "my-project".to_string(),
            languages: ["Rust".to_string(), "TypeScript".to_string()]
                .into_iter()
                .collect(),
            frameworks: ["Cargo".to_string()].into_iter().collect(),
            test_command: Some("cargo test".to_string()),
            lint_command: Some("cargo clippy".to_string()),
            ..Default::default()
        }
    }

    #[test]
    fn claude_md_includes_languages() {
        let rg = RouterGenerator::new(sample_config());
        let md = rg.generate_claude_md();
        assert!(md.contains("Rust"));
        assert!(md.contains("TypeScript"));
        assert!(md.contains("cargo test"));
        assert!(md.contains("cargo clippy"));
    }

    #[test]
    fn claude_md_includes_routing_table() {
        let rg = RouterGenerator::new(sample_config());
        let md = rg.generate_claude_md();
        assert!(md.contains("First-Action Routing"));
        assert!(md.contains("agileplus specify"));
        assert!(md.contains("agileplus ship"));
    }

    #[test]
    fn agents_md_includes_rules() {
        let rg = RouterGenerator::new(sample_config());
        let md = rg.generate_agents_md();
        assert!(md.contains("Binding Rules"));
        assert!(md.contains("UTF-8 encoding"));
        assert!(md.contains("agileplus triage"));
    }

    #[test]
    fn empty_config_still_generates() {
        let rg = RouterGenerator::new(ProjectConfig::default());
        let claude = rg.generate_claude_md();
        let agents = rg.generate_agents_md();
        assert!(claude.contains("AgilePlus"));
        assert!(agents.contains("Binding Rules"));
    }
}
