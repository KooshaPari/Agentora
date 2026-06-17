# Development Standards

## xDD Methodologies Applied

### Development
- **TDD**: Write failing tests before implementation
- **BDD**: Define behavior with Gherkin scenarios
- **DDD**: Map to domain concepts
- **ATDD**: Define acceptance criteria first
- **SDD**: Write detailed specifications

### Design Principles
- **SOLID**: Single responsibility, Open/closed, Liskov, Interface segregation, Dependency inversion
- **DRY**: Don't repeat yourself
- **KISS**: Keep it simple
- **YAGNI**: You aren't gonna need it
- **LoD**: Law of Demeter
- **SoC**: Separation of Concerns

### Architecture
- **Clean Architecture**: Dependencies point inward
- **Hexagonal**: Ports and adapters isolation
- **CQRS**: Separate read/write operations
- **Event-Driven**: React to domain events

## Code Quality Gates

| Gate | Threshold | Tool |
|------|-----------|------|
| Test Coverage | 80% | tarpaulin, cargo coverage |
| Linting | Pass | rustfmt, clippy |
| Types | Strict | rustc, miri |
| Security | 0 CVEs | cargo audit, rustsec |
| Mutation | Pass | cargo mutator |

## Commit Convention

```
<type>(<scope>): <subject>

Types: feat, fix, docs, style, refactor, test, chore
Scopes: domain, application, adapters, infra, cli

Examples:
feat(domain): add Command entity
fix(cli): handle empty arguments
docs(adapters): add config loader docs
```

## PR Requirements

- [ ] Tests pass
- [ ] Clippy passes
- [ ] rustfmt applied
- [ ] Coverage threshold met
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] ADR created (if architecture change)

## Architecture Decisions

All significant architecture decisions must be documented in ADR/.
See ADR-001-template.md for the format.
