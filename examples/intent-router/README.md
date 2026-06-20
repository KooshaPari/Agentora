# intent-router example

First end-to-end consumer of the `agent-platform` `DeviceStage` abstraction. Takes a free-form user message, classifies it, and dispatches to the correct modal adapter behind a single user-facing surface.

This is the proof-of-concept that the trait family (`mobile`, `desktop`, `sandbox`, `browser`, `eidolon`) plus the agent-runtime port (`claude`) all compose behind one entry point. Per ADR-023 (app-effort governance), this is the recommended pattern for any app-level consumer that wants to drive multiple device modalities — depend on the trait family in `ports/`, not on the concrete backends.

## What it does

Given a string like one of the following, the router classifies the intent and dispatches to the right adapter:

| User message | Classified modality | Adapter invoked |
| --- | --- | --- |
| `open Safari on my iPhone` | `mobile` | `MobileDeviceStage.openSession(...)` + `.call("launch_app", { app, device })` |
| `ask Claude to refactor this` | `claude` | `ClaudeRuntime.exec({ prompt, model, agent })` |
| `run a sandbox` | `sandbox` | `SandboxStage.openSession(...)` + `.call("run_command", { command })` |
| `navigate to example.com in browser` | `browser` | `BrowserStage.openSession(...)` + `.call("navigate", { url })` |
| `click on desktop` | `desktop` | `DesktopStage.openSession(...)` + `.pointer(...)` |
| `dispatch via Eidolon` | `eidolon` | `EidolonStage.call("ping", { source, message })` |
| *(anything that matches no pattern)* | `defaultModality` (defaults to `eidolon`) | The default adapter slot |

## Files in this directory

| File | Purpose |
| --- | --- |
| `intent-router.ts` | The router — `IntentRouter` class, classifier, per-modality dispatch, public types |
| `test.ts` | Vitest suite — 9 test groups / 14 individual `it()` blocks |
| `package.json` | Independent package descriptor (no deps — inherits the parent's `node_modules`) |
| `tsconfig.json` | TypeScript config for `tsc --noEmit` on the example only |
| `README.md` | This file |

## How to use

### 1. As a library

```ts
import { IntentRouter, type IntentAdapters } from "agent-platform/examples/intent-router/intent-router";
import { MobileDeviceStage } from "agent-platform/ports/adapters/mobile";
import { ClaudeRuntime } from "agent-platform/ports/adapters/claude";

const adapters: IntentAdapters = {
  mobile: new MobileDeviceStage({ name: "iphone", type: "adb" }),
  claude: new ClaudeRuntime(),
};

const router = new IntentRouter({ adapters });
const result = await router.route("ask Claude to refactor this file");
console.log(result.text); // [claude:haiku] refactor this file
```

The adapter set is partial — any modality without a wired adapter returns a structured `{ error }` from `route()` instead of throwing, so the consumer can decide what to do (fall through, ask for clarification, etc.).

### 2. As a CLI

```sh
# From this directory:
npx tsx ./intent-router.ts "open Safari on my iPhone"
```

Wrap it in a CLI binary of your choosing — the public API is `new IntentRouter({ adapters }).route(message)`.

## How the classifier works

The classifier is a priority-ordered list of `(modality, pattern, extract)` tuples. The first pattern that matches wins; the extractor pulls modality-specific args (e.g. the app name from `"open Safari on iPhone"`, the URL from `"navigate to example.com"`). If no pattern matches, the router falls back to `defaultModality` with `fellBack: true` in the result.

| Priority | Modality | Pattern (simplified) |
| --- | --- | --- |
| 1 | `claude` | `/\b(?:ask\s+)?claude(?:\s+to)?\b/i` |
| 2 | `eidolon` | `/\b(?:dispatch\s+via\|via\|through)\s+eidolon\b/i` |
| 3 | `mobile` | `/\b(?:iphone\|ipad\|android\|...)\b/i` |
| 4 | `desktop` | `/\b(?:click\s+on\s+(?:the\s+)?(?:desktop\|macos\|linux\|windows)\|...)\b/i` |
| 5 | `sandbox` | `/\b(?:sandbox\|ephemeral(?:\s+(?:vm\|env))?\|firecracker\|...)\b/i` |
| 6 | `browser` | `/\b(?:navigate\s+to\|open\s+(?:url\|https?:\/\/)\|https?:\/\/)\b/i` |

## Running the tests

```sh
# From this directory:
npx vitest run test.ts

# From the repo root:
npx vitest run examples/intent-router/test.ts
```

The test suite covers:

- One test per modality (mobile / claude / sandbox / browser / desktop / eidolon) — verifies classification + dispatch + transport call sequence
- Missing-adapter error path (returns `{ error }` instead of throwing)
- Fallback-to-defaultModality path
- Classifier priority (claude > eidolon > mobile > browser on overlapping text)
- Null-transport composability (all 5 null-backed adapters wired in — router still classifies correctly, underlying transport errors propagate as expected)

## Type checking

```sh
# From this directory:
npx tsc --noEmit
```

The local `tsconfig.json` extends the strict mode settings of the repo root and includes only `*.ts` in this directory.

## Why this example matters

This is the **first** non-test consumer of the `DeviceStage` trait family. Before this example, every `DeviceStage` adapter was used only by its own unit test. After this example, the trait family is proven to compose behind a single user-facing surface — the next app-level consumer (Civis, per ADR-023) can wire its UI directly to `IntentRouter` instead of re-implementing per-modality switch statements.

Per ADR-023 Rule 3.1 (substrate quality bar), the trait is the only thing domain code should depend on. This example shows what that looks like in practice.

## Extending

To add a new modality:

1. Add a new `Modality` literal in `intent-router.ts` (e.g. `"watch"`).
2. Add a slot to `IntentAdapters`.
3. Add a classifier rule in the priority-ordered `CLASSIFIERS` array.
4. Add a `dispatchXxx()` private method.
5. Switch the `dispatch()` method over the new modality.
6. Add a test group in `test.ts`.
7. Update this README.

The router intentionally doesn't try to be a full NLP. The classifier is regex-based and a slot for "real" intent classification (LLM-based, or a small classification model) lives behind `defaultModality` — point it at Claude for any message the regexes don't match.
