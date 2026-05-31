# Functional Requirements — PhenoAgent

Traces to: PRD.md epics E1–E8.
ID format: FR-PHENOAGENT-{NNN}.

---

## Agent Runtime

**FR-PHENOAGENT-001**: The system SHALL provide an async runtime for executing autonomous agent workflows with task scheduling and state management.
Traces to: E1.1

**FR-PHENOAGENT-002**: The system SHALL support agent lifecycle hooks: init, before_step, after_step, on_error, shutdown.
Traces to: E1.2

**FR-PHENOAGENT-003**: The system SHALL persist agent state to durable storage and support resumption from checkpoints.
Traces to: E1.3

---

## Skill & Tool Registration

**FR-PHENOAGENT-004**: The system SHALL expose a [Skill] trait for registering reusable capabilities (tools, integrations) with metadata and versioning.
Traces to: E2.1

**FR-PHENOAGENT-005**: The system SHALL support MCP resource exposure for skills to enable Claude/LLM invocation.
Traces to: E2.2

---

## Decision & Reasoning

**FR-PHENOAGENT-006**: The system SHALL log agent decision trees and reasoning traces for auditability and debugging.
Traces to: E3.1

**FR-PHENOAGENT-007**: The system SHALL support policy-driven agent behavior constraints via optional guard conditions.
Traces to: E3.2

---

## Trace & Test Guidance

All tests MUST reference a Functional Requirement (FR):

```rust
// Traces to: FR-PHENOAGENT-NNN
#[test]
fn test_agent_lifecycle() { ... }
```
