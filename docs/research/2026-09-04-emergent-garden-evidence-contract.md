# Evidence-grounded action and memory contract: research dossier

Status: proposed documentation only. No runtime API, crate name or release contract is changed.

Work tracking: [AgilePlus #1073](https://github.com/KooshaPari/AgilePlus/issues/1073). Canonical research: [ResearchLedger Wave 3](https://github.com/KooshaPari/ResearchLedger/blob/8c271fd6765b01c6a6a6339d7273199a48e06334/docs/corpora/emergent-garden/research/WAVE-3-COMMENTS-AND-SYNTHESIS.md).

## Audited boundary

Repository revision: `2460a736e734700e752a00314ef9fbdad2cf5aad`.

Read: `AGENTS.md`, `README.md`, `STANDARDS.md`, and `src/domain/events/mod.rs`. The crate remains `agentkit`; the documented architecture is domain/application/adapters/infrastructure with skills, tools, two-tier memory and lifecycle events.

The inspected event module contains `AgentStarted`, `AgentCompleted` and `ToolCalled`. `ToolCalled` records tool name, session, arguments and time; `AgentCompleted` records duration and step count. This module alone does not prove that observed-result facilities are absent from the entire repository. Audit existing ports, execution results and adapters before adding a competing abstraction.

## Research-to-project mapping

Creator clarification C07 supports revisable subgoals rather than rigid exact planning. C11 distinguishes script search from RL. C12 distinguishes a plausible strategy from its real execution. C21 makes historical observation capability explicit. The primary-source review distinguishes generated memory reflections from observations and skill accumulation from model-weight updates (S09, S11).

Our proposed consequence is an evidence boundary, not a new universal agent topology. The source corpus does not prove that more agents help Agentora or that it should become a Minecraft runtime.

## Proposed semantics

Represent these separately, reusing existing types where possible:

- **Proposed:** an intended action with prerequisites and the observation revision used to choose it.
- **Dispatched:** the adapter accepted an attempt identified by a stable action ID.
- **Observed:** a result tied to the action ID, adapter, environment revision and before/after observations.
- **Evaluated:** an acceptance decision from the declared evaluator, not merely the agent's completion message.

A proposal can be rejected or superseded. A dispatch can fail, time out or have an unknown outcome. An observed effect can fail acceptance. These are not interchangeable success states.

Suggested evidence fields are `action_id`, `attempt_id`, `parent_action_id`, `observation_revision`, `environment_revision`, `tool_revision`, `permission_manifest_hash`, `candidate_artifact_hash`, `result_origin`, `evaluator_revision`, `result_reference`, and `terminal_state`. This is a design candidate, not an implemented public Rust API.

## Memory and retrieval

Memory entries should identify origin: direct observation, tool result, external source, agent inference, reflection, or operator assertion. Derived beliefs should retain their supporting entries. A correction can mark dependents stale without rewriting the historical source.

A retrieved skill is a candidate. Before execution, validate its revision, current prerequisites, tool access, authority and applicability. Embedding similarity alone must not grant execution permission.

## Plans and permissions

Allow subgoals to be amended when observations change. Do not let that amendment silently expand filesystem scope, enable code execution, spend budget or redefine the evaluator. Plan revision and authority revision are distinct events.

For self-modifying candidates, retain an evaluator outside candidate-writable scope. Copying code does not isolate shared storage, credentials or physical actions. Record compensation requirements where rollback cannot undo an effect.

## Required negative controls

A bounded follow-on should test stale observations, duplicate/out-of-order result delivery, an unknown tool outcome after timeout, an agent claiming success without a result, a retrieved skill needing forbidden permissions, a reflection mistaken for an observation, and a subgoal amendment that tries to expand authority.

Expected behavior: no observed/evaluated success without the required evidence; retries keep explicit attempt identity; corrections invalidate dependent conclusions; proposals outside authority are rejected; completion counts and durations do not substitute for task correctness.

## Alternatives and rejection conditions

No new type is warranted if existing ports already express these semantics. A wrapper may suffice. A single-agent baseline may outperform a richer coordination system. Strict ordering may reduce responsiveness; measure it rather than assuming every action needs a global lock. Report unknown outcomes instead of fabricating binary success/failure.

## Acceptance before implementation

Map every proposed field to existing code and document gaps with pinned paths. Obtain a reviewed design for additive compatibility. Preserve hexagonal dependencies, feature-gated adapters and the `agentkit` name. Then run repository quality gates and controlled tests in a separate implementation work package.

This draft does not claim Cargo tests, provider integration tests or live coordination benchmarks ran for Agentora. It introduces research documentation only and requests no merge or release.
