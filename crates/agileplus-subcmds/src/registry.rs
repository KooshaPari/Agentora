//! Sub-command registry with ~25 variants across 7 categories.
//!
//! Traceability: WP20-T114, T115, T116, T117, T118, T119

use std::collections::HashMap;

use serde::{Deserialize, Serialize};

/// Sub-command category.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum SubCommandCategory {
    Triage,
    Governance,
    Sync,
    Git,
    DevOps,
    Context,
    Escape,
    Meta,
}

impl std::fmt::Display for SubCommandCategory {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let s = match self {
            Self::Triage => "triage",
            Self::Governance => "governance",
            Self::Sync => "sync",
            Self::Git => "git",
            Self::DevOps => "devops",
            Self::Context => "context",
            Self::Escape => "escape",
            Self::Meta => "meta",
        };
        write!(f, "{s}")
    }
}

/// A registered sub-command.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SubCommand {
    pub name: String,
    pub category: SubCommandCategory,
    pub description: String,
    pub usage: String,
    pub hidden: bool,
}

/// Registry of all sub-commands.
#[derive(Debug)]
pub struct SubCommandRegistry {
    commands: HashMap<String, SubCommand>,
}

impl SubCommandRegistry {
    /// Create registry with all built-in sub-commands.
    pub fn new() -> Self {
        let mut commands = HashMap::new();

        let all = vec![
            // Triage (3)
            cmd(
                "triage:classify",
                SubCommandCategory::Triage,
                "Classify input text as bug/feature/idea/task",
                "triage:classify <text>",
            ),
            cmd(
                "triage:file-bug",
                SubCommandCategory::Triage,
                "File a bug report to the backlog",
                "triage:file-bug --title <title> --description <desc>",
            ),
            cmd(
                "triage:queue-idea",
                SubCommandCategory::Triage,
                "Queue an idea for later consideration",
                "triage:queue-idea --title <title> --description <desc>",
            ),
            // Governance (3)
            cmd(
                "governance:check-gates",
                SubCommandCategory::Governance,
                "Check all governance gates for a feature",
                "governance:check-gates --feature <slug>",
            ),
            cmd(
                "governance:evaluate-policy",
                SubCommandCategory::Governance,
                "Evaluate a specific policy rule",
                "governance:evaluate-policy --policy <id> --feature <slug>",
            ),
            cmd(
                "governance:verify-chain",
                SubCommandCategory::Governance,
                "Verify the audit chain integrity",
                "governance:verify-chain --feature <slug>",
            ),
            // Sync (3)
            cmd(
                "sync:push-plane",
                SubCommandCategory::Sync,
                "Push feature/WP state to Plane.so",
                "sync:push-plane --feature <slug>",
            ),
            cmd(
                "sync:push-github",
                SubCommandCategory::Sync,
                "Push bug to GitHub Issues",
                "sync:push-github --item <id>",
            ),
            cmd(
                "sync:pull-status",
                SubCommandCategory::Sync,
                "Pull status updates from external trackers",
                "sync:pull-status",
            ),
            // Git (3)
            cmd(
                "git:create-worktree",
                SubCommandCategory::Git,
                "Create a git worktree for a work package",
                "git:create-worktree --feature <slug> --wp <id>",
            ),
            cmd(
                "git:branch-from-wp",
                SubCommandCategory::Git,
                "Create a branch from a work package worktree",
                "git:branch-from-wp --feature <slug> --wp <id>",
            ),
            cmd(
                "git:merge-and-cleanup",
                SubCommandCategory::Git,
                "Merge WP branch and remove worktree",
                "git:merge-and-cleanup --feature <slug> --wp <id>",
            ),
            // DevOps (3)
            cmd(
                "devops:lint-and-format",
                SubCommandCategory::DevOps,
                "Run project-specific lint and format checks",
                "devops:lint-and-format",
            ),
            cmd(
                "devops:conventional-commit",
                SubCommandCategory::DevOps,
                "Validate commit message format",
                "devops:conventional-commit --message <msg>",
            ),
            cmd(
                "devops:run-ci-checks",
                SubCommandCategory::DevOps,
                "Run CI check suite locally",
                "devops:run-ci-checks",
            ),
            // Context (4)
            cmd(
                "context:load-spec",
                SubCommandCategory::Context,
                "Load feature specification into context",
                "context:load-spec --feature <slug>",
            ),
            cmd(
                "context:load-plan",
                SubCommandCategory::Context,
                "Load feature plan into context",
                "context:load-plan --feature <slug>",
            ),
            cmd(
                "context:load-constitution",
                SubCommandCategory::Context,
                "Load project constitution",
                "context:load-constitution",
            ),
            cmd(
                "context:scan-codebase",
                SubCommandCategory::Context,
                "Scan codebase for conventions and patterns",
                "context:scan-codebase",
            ),
            // Escape (3)
            cmd(
                "escape:quick-fix",
                SubCommandCategory::Escape,
                "Apply a quick fix bypassing full workflow (logged as governance exception)",
                "escape:quick-fix --description <desc>",
            ),
            cmd(
                "escape:hotfix",
                SubCommandCategory::Escape,
                "Create a hotfix branch directly on main",
                "escape:hotfix --description <desc>",
            ),
            cmd(
                "escape:skip-with-warning",
                SubCommandCategory::Escape,
                "Skip a governance gate with explicit warning",
                "escape:skip-with-warning --gate <name> --reason <reason>",
            ),
            // Meta (3)
            cmd(
                "meta:generate-router",
                SubCommandCategory::Meta,
                "Regenerate CLAUDE.md and AGENTS.md from project config",
                "meta:generate-router",
            ),
            cmd(
                "meta:update-agents-md",
                SubCommandCategory::Meta,
                "Update AGENTS.md with current agent rules",
                "meta:update-agents-md",
            ),
            cmd(
                "meta:list-commands",
                SubCommandCategory::Meta,
                "List all available sub-commands",
                "meta:list-commands",
            ),
        ];

        for c in all {
            commands.insert(c.name.clone(), c);
        }

        Self { commands }
    }

    /// Look up a sub-command by name.
    pub fn get(&self, name: &str) -> Option<&SubCommand> {
        self.commands.get(name)
    }

    /// List all sub-commands, optionally filtered by category.
    pub fn list(&self, category: Option<SubCommandCategory>) -> Vec<&SubCommand> {
        let mut cmds: Vec<_> = self
            .commands
            .values()
            .filter(|c| category.is_none() || Some(c.category) == category)
            .collect();
        cmds.sort_by(|a, b| a.name.cmp(&b.name));
        cmds
    }

    /// List all categories with command counts.
    pub fn categories(&self) -> Vec<(SubCommandCategory, usize)> {
        let mut counts: HashMap<SubCommandCategory, usize> = HashMap::new();
        for c in self.commands.values() {
            *counts.entry(c.category).or_default() += 1;
        }
        let mut result: Vec<_> = counts.into_iter().collect();
        result.sort_by_key(|(cat, _)| format!("{cat}"));
        result
    }

    /// Total number of registered sub-commands.
    pub fn len(&self) -> usize {
        self.commands.len()
    }

    pub fn is_empty(&self) -> bool {
        self.commands.is_empty()
    }
}

impl Default for SubCommandRegistry {
    fn default() -> Self {
        Self::new()
    }
}

fn cmd(name: &str, category: SubCommandCategory, description: &str, usage: &str) -> SubCommand {
    SubCommand {
        name: name.to_string(),
        category,
        description: description.to_string(),
        usage: usage.to_string(),
        hidden: true,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn registry_has_25_commands() {
        let reg = SubCommandRegistry::new();
        assert_eq!(reg.len(), 25);
    }

    #[test]
    fn lookup_by_name() {
        let reg = SubCommandRegistry::new();
        let cmd = reg.get("triage:classify").unwrap();
        assert_eq!(cmd.category, SubCommandCategory::Triage);
        assert!(reg.get("nonexistent").is_none());
    }

    #[test]
    fn filter_by_category() {
        let reg = SubCommandRegistry::new();
        let triage = reg.list(Some(SubCommandCategory::Triage));
        assert_eq!(triage.len(), 3);
        let governance = reg.list(Some(SubCommandCategory::Governance));
        assert_eq!(governance.len(), 3);
        let context = reg.list(Some(SubCommandCategory::Context));
        assert_eq!(context.len(), 4);
    }

    #[test]
    fn list_all() {
        let reg = SubCommandRegistry::new();
        let all = reg.list(None);
        assert_eq!(all.len(), 25);
        // Sorted by name
        assert!(all[0].name < all[1].name);
    }

    #[test]
    fn categories_summary() {
        let reg = SubCommandRegistry::new();
        let cats = reg.categories();
        assert!(!cats.is_empty());
        let total: usize = cats.iter().map(|(_, n)| n).sum();
        assert_eq!(total, 25);
    }

    #[test]
    fn all_commands_are_hidden() {
        let reg = SubCommandRegistry::new();
        for cmd in reg.list(None) {
            assert!(cmd.hidden, "Command {} should be hidden", cmd.name);
        }
    }

    #[test]
    fn command_serialization() {
        let reg = SubCommandRegistry::new();
        let cmd = reg.get("sync:push-plane").unwrap();
        let json = serde_json::to_string(cmd).unwrap();
        assert!(json.contains("sync:push-plane"));
        assert!(json.contains("sync"));
    }
}
