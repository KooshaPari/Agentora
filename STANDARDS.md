# Development Standards

## xDD Methodologies Applied

### Development
- **TDD**: Write failing tests before implementation
- **BDD**: Define behavior with Gherkin
- **DDD**: Map to domain concepts
- **ATDD**: Define acceptance criteria first
- **SDD**: Write detailed specifications

### Design Principles
- **SOLID**: Single responsibility, Open/closed, Liskov, Interface segregation, Dependency inversion
- **DRY**: Don't repeat yourself
- **KISS**: Keep it simple
- **YAGNI**: You aren't gonna need it

### Architecture
- **Clean Architecture**: Dependencies point inward
- **Hexagonal**: Ports and adapters isolation
- **CQRS**: Separate read/write operations

## Code Quality Gates

| Gate | Threshold | Tool |
|------|-----------|------|
| Test Coverage | 80% | tarpaulin |
| Linting | Pass | rustfmt, clippy |
| Security | 0 CVEs | cargo audit |

## Commit Convention

```
<type>(<scope>): <subject>

Types: feat, fix, docs, style, refactor, test, chore
```

## PR Requirements

- [ ] Tests pass
- [ ] Clippy passes
- [ ] rustfmt applied
- [ ] Coverage threshold met
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
