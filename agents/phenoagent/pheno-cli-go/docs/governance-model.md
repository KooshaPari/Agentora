# Governance Model: 5-Tier Release Channels

## Overview

pheno enforces a 5-tier release channel model for all Phenotype packages. Each channel represents a progressively higher confidence level, with promotion gates ensuring quality before production.

## Channels

| Tier | Channel  | Tag Suffix      | Audience           | Purpose                                |
|------|----------|-----------------|--------------------|----------------------------------------|
| 0    | `alpha`  | `-alpha.N`      | Internal           | Early integration, all breaking OK     |
| 1    | `canary` | `-canary.N`     | Internal + partners| Nightly/CI-driven validation           |
| 2    | `beta`   | `-beta.N`       | Early adopters     | Feature-complete, API stabilizing      |
| 3    | `rc`     | `-rc.N`         | All users          | Release candidate, only bug fixes      |
| 4    | `prod`   | (no suffix)     | All users          | Stable production release              |

### Version Format Examples

```
npm:      1.2.0-alpha.3, 1.2.0-canary.7, 1.2.0-beta.1, 1.2.0-rc.2, 1.2.0
PyPI:     1.2.0a3, 1.2.0b1, 1.2.0rc2, 1.2.0
crates:   1.2.0-alpha.3, 1.2.0-beta.1, 1.2.0-rc.2, 1.2.0
```

## Risk Profiles

The governance model enforces different promotion rules based on the risk profile of a package or change:

### Low Risk

Low-risk changes (documentation, internal tooling, experimental features) may skip non-mandatory channel tiers.

- Can skip any intermediate channel
- Example path: `alpha → prod` (skipping canary, beta, rc)
- Requires explicit `--risk low` flag on promote

### Medium Risk

Medium-risk changes (new features, non-breaking API additions) have limited skip allowance.

- May skip at most **2 consecutive tiers**
- **Cannot skip beta** — beta is mandatory for medium-risk changes
- Valid paths: `alpha → beta`, `alpha → canary → rc`, `canary → prod` (from rc only)
- Invalid paths: `alpha → rc` (skips both canary and beta)

### High Risk (Default)

High-risk changes (breaking changes, security patches, major refactors) must proceed sequentially.

- No channel skipping allowed
- Must pass gates at every tier: `alpha → canary → beta → rc → prod`
- All gate criteria must be met before promotion

## Promotion Workflow

### Basic Promotion

```bash
# Promote 1.0.0 from alpha to canary
pheno promote --from alpha --to canary --version 1.0.0

# Promote from canary to beta
pheno promote --from canary --to beta --version 1.0.0

# Promote to production (full gate evaluation)
pheno promote --from rc --to prod --version 1.0.0
```

### Risk-Flagged Promotion

```bash
# Skip canary for a low-risk docs-only change
pheno promote --from alpha --to beta --version 1.0.1 --risk low

# Force gate bypass (emergency hotfix, use with caution)
pheno promote --from rc --to prod --version 1.0.1 --force --reason "critical security patch"
```

### Promotion with Dry Run

```bash
# Preview what a promotion would do
pheno promote --from beta --to rc --version 1.0.0 --dry-run
```

## Gate Criteria

Each channel has a set of gate criteria that must pass before promotion is allowed.

### Alpha Gate

- Build passes (no compilation errors)
- Basic smoke tests pass
- No hardcoded secrets detected

### Canary Gate

- All alpha gates pass
- Unit test suite passes (min 60% coverage)
- No critical lint violations
- Integration tests pass in CI

### Beta Gate

- All canary gates pass
- Unit test coverage >= 80%
- API documentation complete
- Changelog entry present for this version
- No open P0/P1 issues in the tracker

### RC Gate

- All beta gates pass
- End-to-end tests pass
- Security scan clean (no HIGH or CRITICAL CVEs)
- Performance benchmarks within 10% of baseline
- Release notes reviewed and approved

### Prod Gate

- All RC gates pass
- Canary deployment stable for >= 24 hours (for services)
- Stakeholder sign-off recorded
- Rollback plan documented

## Channel Invariants

- A version published to a higher channel cannot be un-published from that channel.
- Each channel publish increments the pre-release number monotonically.
- The same base semantic version (e.g., `1.2.0`) must be used across all channels for a given release train.
- Production releases must never carry a pre-release suffix.
