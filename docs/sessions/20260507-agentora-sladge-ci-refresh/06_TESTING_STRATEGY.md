# Testing Strategy

## Planned Checks

- `git diff --check` passed.
- README badge search with `rg` passed.
- `cargo fmt --check` blocked on pre-existing Rust formatting drift outside
  this change.
- `cargo clippy --all-targets --all-features --offline -- -D warnings` passed.
- `cargo test --offline` passed.

## Scope

This is a README/session-doc governance update. Rust gate failures are recorded
as blockers if they come from pre-existing code or environment state.
