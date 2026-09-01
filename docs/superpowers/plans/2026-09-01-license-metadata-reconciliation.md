# Apache-2.0 Metadata Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish PR #200's owner-approved Apache-2.0 publication change without altering source code or nested component licenses.

**Architecture:** Treat root `Cargo.toml` as the package-license authority and make the four root identity documents agree with it. Add a governance workflow assertion so a future root metadata mismatch fails with the exact stale file name.

**Tech Stack:** GitHub Actions shell, Cargo metadata, Markdown, Citation File Format YAML

---

### Task 1: Add the failing root-license consistency gate

**Files:**

- Modify: `.github/workflows/governance.yml`

- [ ] **Step 1: Add a root metadata assertion**

Add a workflow step that extracts the root package license from `Cargo.toml`, requires `Apache-2.0`, rejects `MIT OR Apache-2.0` in `AGENTS.md`, `CLAUDE.md`, `CITATION.cff`, and `ORIGIN.md`, and requires `Apache-2.0` in each file.

- [ ] **Step 2: Run the assertion and verify RED**

Run the step's shell locally.

Expected: FAIL naming `AGENTS.md` first because current main still declares `MIT OR Apache-2.0`.

### Task 2: Align omitted root identity surfaces

**Files:**

- Modify: `AGENTS.md:10`
- Modify: `CLAUDE.md:12`
- Modify: `CITATION.cff:10`
- Modify: `ORIGIN.md:21`

- [ ] **Step 1: Replace the four stale dual-license declarations**

Use the exact SPDX identifier `Apache-2.0` in all four root identity surfaces. Do not alter nested crates, absorbed projects, source files, or their independent license records.

- [ ] **Step 2: Run the assertion and verify GREEN**

Run the same shell assertion.

Expected: PASS with `Root package license metadata is consistent: Apache-2.0`.

- [ ] **Step 3: Run focused quality checks**

Run:

```bash
actionlint .github/workflows/governance.yml
cargo metadata --locked --no-deps --format-version 1 >/dev/null
cargo deny check advisories licenses sources
npx --yes prettier --check CITATION.cff docs/superpowers/plans/2026-09-01-license-metadata-reconciliation.md
git diff --check
```

Expected: all commands exit 0.

`AGENTS.md`, `CLAUDE.md`, and `ORIGIN.md` have pre-existing Prettier drift on
`main`; keep their license-only edits surgical rather than bulk-formatting them
in this repair.

- [ ] **Step 4: Commit the isolated repair**

```bash
git add .github/workflows/governance.yml AGENTS.md CLAUDE.md CITATION.cff ORIGIN.md docs/superpowers/plans/2026-09-01-license-metadata-reconciliation.md
git commit -m "fix(metadata): complete Apache-2.0 alignment"
```

### Cross-Project Reuse Opportunities

None. This assertion intentionally governs Agentora's root publication metadata only; nested absorbed components retain their own license authorities.
