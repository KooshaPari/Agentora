# Apache-2.0 Metadata Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish PR #200's owner-approved Apache-2.0 publication change without altering source code or nested component licenses.

**Architecture:** Treat root `Cargo.toml` as the package-license authority and make the four root identity documents agree with it. Add a stdlib-only Python validator that parses TOML structurally, identifies each authoritative identity field, rejects missing or duplicate declarations, and runs in pull requests before merge.

**Tech Stack:** GitHub Actions, Python 3.11+ stdlib (`tomllib`, `unittest`), Cargo metadata, Markdown, Citation File Format YAML

---

## Task 1: Add the failing root-license consistency validator

**Files:**

- Modify: `.github/workflows/governance.yml`
- Create: `scripts/validate_root_license_metadata.py`
- Create: `tests/test_validate_root_license_metadata.py`

- [ ] **Step 1: Add negative validator tests**

Cover a preceding workspace license with a wrong package license, a missing package license, duplicate TOML keys, unrelated Apache mentions, alternate/reordered dual-license spellings, and duplicate authoritative identity fields.

- [ ] **Step 2: Run the tests and verify RED**

Run `python3.11 -m unittest -v tests/test_validate_root_license_metadata.py` locally.

Expected: FAIL because the validator is not implemented.

- [ ] **Step 3: Implement structural validation**

Parse `Cargo.toml` with `tomllib` and require exactly `[package].license = "Apache-2.0"`. Validate exactly one authoritative License field in each of `AGENTS.md`, `CLAUDE.md`, `CITATION.cff`, and `ORIGIN.md`, with the exact value `Apache-2.0`.

- [ ] **Step 4: Run the tests and verify GREEN**

Expected: all negative fixtures are rejected for the intended reason and the exact valid fixture passes.

- [ ] **Step 5: Wire the validator into pre-merge governance**

Run the validator tests and validator from the governance workflow, and trigger that workflow for pull requests targeting `main` as well as pushes, schedules, and manual dispatches.

## Task 2: Align omitted root identity surfaces

**Files:**

- Modify: `AGENTS.md:10`
- Modify: `CLAUDE.md:12`
- Modify: `CITATION.cff:10`
- Modify: `ORIGIN.md:21`

- [ ] **Step 1: Replace the four stale dual-license declarations**

Use the exact SPDX identifier `Apache-2.0` in all four root identity surfaces. Do not alter nested crates, absorbed projects, source files, or their independent license records.

- [ ] **Step 2: Run the assertion and verify GREEN**

Run `python3.11 scripts/validate_root_license_metadata.py`.

Expected: PASS with `Root package license metadata is consistent: Apache-2.0`.

- [ ] **Step 3: Run focused quality checks**

Run:

```bash
actionlint .github/workflows/governance.yml
python3.11 -m unittest -v tests/test_validate_root_license_metadata.py
python3.11 scripts/validate_root_license_metadata.py
cargo metadata --locked --no-deps --format-version 1 >/dev/null
cargo deny check advisories licenses sources
npx --yes prettier --check .github/workflows/governance.yml CITATION.cff docs/superpowers/plans/2026-09-01-license-metadata-reconciliation.md
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

## Cross-Project Reuse Opportunities

None. This assertion intentionally governs Agentora's root publication metadata only; nested absorbed components retain their own license authorities.
