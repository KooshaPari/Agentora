# agentkit Path to Sidekick Collection

**Date:** 2026-04-25  
**Status:** Pre-Sidekick (Immature)  
**Reference:** [Wave 68 Sidekick Candidates Audit](../../docs/org-audit-2026-04/wave68_sidekick_candidates_audit.md)

---

## Current Assessment

| Metric | Status | Target |
|--------|--------|--------|
| **LOC (Source)** | 1,035 | Stable |
| **Test Coverage** | <1% (3 tests) | 60%+ |
| **Production Readiness** | Low | High |
| **Cross-Repo Adopters** | 0 | 2+ |
| **Feature Registry** | Planned | FR-AGK-* IDs |

---

## Sidekick Qualification Criteria

agentkit qualifies for Sidekick Collection when ALL of:

1. **Test Coverage ≥60%**
   - Current: 3 tests, ~1% coverage
   - Needed: ~600+ LOC of tests (unit + integration)
   - Strategy: Add domain (agents, skills, tools), adapter (llm, memory), integration tests

2. **2+ Adopter Repositories**
   - Current: 0 consumers in Phenotype org
   - Targets: agileplus-agents, thegent-dispatch, or custom agent projects
   - Validation: Cargo.toml/package.json dependency + production usage

3. **Feature Registry (FR-AGK-NNN)**
   - Current: No FRs defined
   - Required: Functional requirements doc mapping features → tests
   - Examples: FR-AGK-001 (skill system), FR-AGK-002 (memory), FR-AGK-003 (event bus)

4. **Adapter Maturity**
   - Current: Stubs (llm/, memory/ are placeholders)
   - Needed: OpenAI adapter complete, Redis memory adapter working, SQLite migration layer solid
   - Validation: 3+ working adapter implementations with tests

---

## Next 5 Work Packages (Roadmap)

### WP-1: Test Harness Setup (Est. 2-3h)
- Create test framework (criterion for benchmarking, proptest for property tests)
- Mock adapters for unit testing (MockLLMPort, MockMemoryPort)
- CI integration (GitHub Actions test runner with coverage reports)
- **Exit Criteria:** Coverage 15%+, CI tests passing, benchmark baseline

### WP-2: Domain Tests (Est. 4-5h)
- Test agents/ module (agent creation, lifecycle, state transitions)
- Test skills/ module (skill registration, tool binding, execution)
- Test tools/ module (schema validation, invocation)
- Test memory/ module (ring buffer, persistence)
- **Exit Criteria:** Domain coverage 40%+, all happy-path tests green

### WP-3: Adapter Tests (Est. 3-4h)
- OpenAI LLM adapter tests (completion, streaming, error handling)
- SQLite memory adapter tests (CRUD, querying, schema)
- Event bus tests (publish/subscribe, replay)
- **Exit Criteria:** Adapter coverage 50%+, integration tests passing

### WP-4: Integration Tests & Documentation (Est. 3-4h)
- E2E test: agent creation → skill execution → memory persistence
- API contract tests (JSON schemas for input/output)
- Update README with tested examples (copy from tests/)
- Add docs/ARCHITECTURE.md with module overview
- **Exit Criteria:** Coverage 60%+, functional examples executable

### WP-5: Feature Registry & Adoption Path (Est. 2-3h)
- Create FUNCTIONAL_REQUIREMENTS.md with FR-AGK-NNN IDs
- Create docs/ADOPTION_GUIDE.md for integrating agentkit into other projects
- Propose agentkit as dependency to agileplus-agents or thegent-dispatch
- Update org portfolio entry (agentkit.kooshapari.com)
- **Exit Criteria:** FRs defined, adoption doc ready, 1st adopter integration started

---

## Timeline Estimate

**Aggressive parallel execution:** ~10-15 hours wall clock (2-3 days single agent, 1 day with 2 agents)

- WP-1, WP-2 can run in parallel (test harness + domain tests)
- WP-3 depends on WP-1 (needs mocks)
- WP-4 depends on WP-2 + WP-3
- WP-5 can start after WP-2 (FRs map to existing modules)

**Sidekick Readiness Checkpoint:** After WP-4 completes + 1 adopter integration begins

---

## Success Metrics

On completion:
- ✅ 60%+ test coverage (passing CI)
- ✅ 2 adopter repos consuming agentkit via Cargo.toml
- ✅ 10+ FR-AGK-* items with full traceability (test → requirement)
- ✅ Architecture doc + adoption guide + working examples
- ✅ Zero lint warnings, security audit passing (trufflehog + semgrep)

---

## Call to Action

**Next agent:** Pick up WP-1 (test harness), establish coverage baseline, run CI locally, then queue WP-2 and WP-3 in parallel. Aggressive timeline gets agentkit to Sidekick-ready by end of week.
