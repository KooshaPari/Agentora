# AGENTS.md - Agent Rules for phenotype-governance

## Agent Roles

### Primary Agents

| Agent | Responsibility | Allowed Operations |
|-------|---------------|-------------------|
| FORGE | Code implementation | Write, Patch, Shell |
| AGENT | Task execution | Shell, Search, Read |
| MUSE | Documentation | Write, Read |

## Governance Rules

### Mandatory Checks

1. **FR Traceability**
   - All tests MUST reference FR-XXX-NNN
   - Use: tracesTo() / @traces_to() / #[trace_to()]

2. **AI Attribution**
   - .phenotype/ai-traceability.yaml MUST exist
   - Updated on every AI-generated change

3. **CI/CD Compliance**
   - .github/workflows/traceability.yml MUST pass
   - No merges with drift > 90%

4. **Policy Enforcement**
   - All governance code must have tests
   - Minimum 90% coverage for governance logic

### Prohibited Actions

- ❌ Disable governance checks without ADR
- ❌ Bypass validation on merge
- ❌ Remove audit logging

## File Operations

### Allowed Patterns

- Read → Patch (sequential)
- Write (new files only)
- Shell (non-destructive)

## Repository-Specific Rules

### Governance Code

- All policy changes need security review
- Audit logs are append-only
- Compliance reports must be reproducible

## Validation

Run before any commit:
```bash
python3 validate_governance.py
```

Must pass all checks before PR.

Last Updated: 2026-04-04
