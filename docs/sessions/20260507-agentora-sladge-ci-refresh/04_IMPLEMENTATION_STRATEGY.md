# Implementation Strategy

Use a fresh current-head worktree:

- Preserve older `docs/agentora-sladge-current` as stale evidence.
- Reapply the README Sladge badge near the existing badge block.
- Keep canonical Agentora unchanged because it contains unrelated untracked
  work.
- Record exact validation blockers for any pre-existing Rust drift.
