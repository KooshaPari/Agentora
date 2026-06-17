# CLAUDE.md - AI Context for phenotype-governance

## Repository Overview

**Name:** phenotype-governance
**Type:** Governance & Compliance Framework
**AI Attribution:** AI-Generated with Human Review

## Purpose

phenotype-governance provides governance, compliance, and quality enforcement
mechanisms across the entire Phenotype organization ecosystem.

## Key Concepts

- **Policy Enforcement:** Automated governance rules via CI/CD
- **Quality Gates:** Pre-commit and pre-merge validation checks
- **Traceability:** End-to-end FR tracking from spec to implementation
- **Compliance:** Security, licensing, and organizational standards

## Architecture

### Components
- Policy Engine: Rules evaluation and enforcement
- Audit Logger: Compliance tracking and reporting
- Integration Layer: GitHub, CI/CD, and external tool integrations

### Data Flow
1. Developer commit → Policy check → Pass/Fail
2. PR creation → Quality gate → Merge approval
3. Release trigger → Compliance scan → Deploy decision

## Development Guidelines

### Code Style
- TypeScript preferred for new code
- All changes must reference FR-XXX-NNN
- Include tests with governance validation

### FR Traceability
- Use @pytest.mark.traces_to() for Python tests
- Use #[trace_to()] for Rust tests
- Use tracesTo() for TypeScript/Go tests

## Testing

### Test Framework
- Vitest for TypeScript tests
- pytest for Python tests

### Running Tests
```bash
# Run all tests
npm test

# Run with governance check
python3 validate_governance.py
```

## Dependencies

- @phenotype/tstreqt: Traceability for tests
- phenotype-validation: Shared validation logic
- GitHub Actions: CI/CD integration

## Related Repositories

- AgilePlus: Central governance definitions
- phenotype-validation: Validation framework
- phenotype-cli-core: CLI tooling

## AI Development Notes

- AI-generated code must pass governance validation
- All changes tracked in .phenotype/ai-traceability.yaml
- See AGENTS.md for specific agent rules

Last Updated: 2026-04-04
