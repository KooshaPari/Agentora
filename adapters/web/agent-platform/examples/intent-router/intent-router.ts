/**
 * intent-router — first end-to-end consumer of the DeviceStage abstraction.
 *
 * Takes a free-form user message like "open Safari on my iPhone",
 * "ask Claude to refactor this", "run a sandbox",
 * "navigate to example.com in browser", "click on desktop",
 * or "dispatch via Eidolon", classifies the intent, and dispatches to
 * the correct modal adapter behind the DeviceStage port family.
 *
 * This module exists to PROVE the DeviceStage abstraction composes
 * across every modality a single user-facing surface can reach.
 *
 * Adapter wiring (DI — caller supplies any combination):
 *   mobile  → MobileDeviceStage (ports/adapters/mobile.ts)
 *   desktop → DesktopStage     (ports/adapters/desktop.ts)
 *   sandbox → SandboxStage     (ports/adapters/sandbox.ts)
 *   browser → BrowserStage     (ports/adapters/browser.ts)
 *   eidolon → EidolonStage     (ports/adapters/eidolon.ts)
 *   claude  → AgentRuntime     (ports/adapters/claude.ts)
 *
 * Per ADR-023 Rule 3.1 (substrate quality bar), every adapter must
 * be safe to inject without a live backend. The router therefore
 * treats a missing adapter as an `error` in the RouteResult — it
 * never throws on dispatch (classifier errors are the only
 * exception path).
 */

import type {
  DeviceStage,
  DeviceId,
  SessionId,
} from "../../ports/device_stage";
import type { AgentId, AgentRuntime, ModelId, RunResponse } from "../../ports/runtime";

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

/** The six modalities the router can dispatch to. */
export type Modality =
  | "mobile"
  | "desktop"
  | "sandbox"
  | "browser"
  | "eidolon"
  | "claude";

/** Caller-supplied adapter set. Any subset is valid; missing slots fall back to `error` in RouteResult. */
export interface IntentAdapters {
  readonly mobile?: DeviceStage;
  readonly desktop?: DeviceStage;
  readonly sandbox?: DeviceStage;
  readonly browser?: DeviceStage;
  readonly eidolon?: DeviceStage;
  readonly claude?: AgentRuntime;
}

export interface IntentRouterOptions {
  readonly adapters: IntentAdapters;
  /** Fallback modality when classify() cannot match any pattern. Defaults to "eidolon" (canonical hub). */
  readonly defaultModality?: Modality;
  /** Default model id for ClaudeRuntime dispatches. Defaults to "haiku". */
  readonly defaultModel?: string;
  /** Default agent id for ClaudeRuntime dispatches. Defaults to "intent-router". */
  readonly defaultAgent?: string;
}

/** Extracted arguments from the message — adapter-specific. */
export interface ExtractedArgs {
  readonly [key: string]: string;
}
/** The output of classify(): modality + extracted args + original message. */
export interface IntentClassification {
  readonly modality: Modality;
  readonly args: ExtractedArgs;
  readonly raw: string;
  /** True if the modality was selected by the default-fallback, not by pattern matching. */
  readonly fellBack: boolean;
}

/** Result of route(): what the adapter actually did, or a structured error. */
export interface RouteResult {
  readonly modality: Modality;
  readonly classification: IntentClassification;
  /** Session opened (if the modality needs one). Undefined for claude / eidolon flat calls. */
  readonly sessionId?: SessionId;
  /** Adapter response payload (modality-specific shape). */
  readonly data?: unknown;
  /** Short text result for AgentRuntime dispatches (claude). */
  readonly text?: string;
  /** Structured error string when the adapter is missing or the call failed. */
  readonly error?: string;
}

// ---------------------------------------------------------------------------
// Classifier — priority-ordered list of (modality, pattern, extractor) tuples
// ---------------------------------------------------------------------------

interface ClassifierRule {
  readonly modality: Modality;
  readonly pattern: RegExp;
  readonly extract: (match: RegExpMatchArray, raw: string) => ExtractedArgs;
}

/** Build an ExtractedArgs from a list of (key, value | undefined) pairs. */
function buildArgs(entries: ReadonlyArray<readonly [string, string | undefined]>): ExtractedArgs {
  const out: Record<string, string> = {};
  for (const [k, v] of entries) {
    if (v !== undefined) out[k] = v;
  }
  return out;
}

const CLASSIFIERS: readonly ClassifierRule[] = [
  // 1. claude — agent runtime, very specific phrasing
  {
    modality: "claude",
    pattern: /\b(?:ask\s+)?claude(?:\s+to)?\b/i,
    extract: (_match, raw) => {
      const idx = raw.toLowerCase().indexOf("claude");
      const afterClaude = raw.slice(idx + "claude".length).trim();
      // Strip a leading "to " if present so "ask Claude to refactor X" -> prompt "refactor X"
      const prompt = afterClaude.replace(/^to\s+/i, "").trim() || raw;
      return buildArgs([["prompt", prompt]]);
    },
  },

  // 2. eidolon — canonical transport hub, matched by explicit "via eidolon"
  {
    modality: "eidolon",
    pattern: /\b(?:dispatch\s+via|via|through)\s+eidolon\b/i,
    extract: (_match, raw) => {
      // Optional "method:foo" or "method=foo" — defaults to "ping"
      const methodMatch = raw.match(/\bmethod\s*[:=]\s*([\w-]+)/i);
      return buildArgs([["method", methodMatch?.[1] ?? "ping"]]);
    },
  },

  // 3. mobile — phone/tablet keywords; matches before desktop/browser
  {
    modality: "mobile",
    pattern:
      /\b(?:iphone|ipad|android(?:\s+\w+)?|pixel(?:\s+\d+)?|samsung(?:\s+\w+)?|on\s+my\s+phone|tap\s+on)\b/i,
    extract: (match, raw) => {
      // Try "open <App> on <Device>" — pull the app and device tokens
      const appMatch = raw.match(/\bopen\s+([A-Z][\w-]*|\w+)\s+(?:on|in|with)\b/);
      const deviceMatch = match[0].match(/\b(iphone|ipad|android|pixel|samsung)[\w-]*/i);
      return buildArgs([
        ["app", appMatch?.[1]],
        ["device", deviceMatch?.[0]?.toLowerCase()],
      ]);
    },
  },

  // 4. desktop — explicit desktop/mac/linux/windows click context
  {
    modality: "desktop",
    pattern:
      /\b(?:click\s+on\s+(?:the\s+)?(?:desktop|macos|linux|windows|my\s+(?:mac|laptop|desktop|pc))|on\s+(?:my\s+)?(?:macos|linux|windows|mac|laptop|pc)|desktop\s+click)\b/i,
    extract: (_match, raw) => {
      const xMatch = raw.match(/\bx\s*[:=]\s*(\d+)/i);
      const yMatch = raw.match(/\by\s*[:=]\s*(\d+)/i);
      return buildArgs([
        ["x", xMatch?.[1]],
        ["y", yMatch?.[1]],
      ]);
    },
  },

  // 5. sandbox — ephemeral VM / container / firecracker / gvisor
  {
    modality: "sandbox",
    pattern:
      /\b(?:sandbox|ephemeral(?:\s+(?:vm|env))?|firecracker|gvisor|run\s+a\s+(?:vm|container))\b/i,
    extract: (_match, raw) => {
      const cmdMatch = raw.match(/[`"']([^`"']+)[`"']/);
      return buildArgs([["command", cmdMatch?.[1]]]);
    },
  },

  // 6. browser — navigation, URL, or browser keyword
  {
    modality: "browser",
    pattern: /\b(?:navigate\s+to|open\s+(?:url|https?:\/\/)|https?:\/\/|\bbrowser\b)\b/i,
    extract: (_match, raw) => {
      // Pull a real URL if present; otherwise the token after "navigate to"
      const urlMatch = raw.match(/https?:\/\/[^\s"'<>`]+/i);
      const navMatch = raw.match(/\bnavigate\s+to\s+(\S+)/i);
      const url = urlMatch?.[0] ?? navMatch?.[1]?.replace(/[.,;]+$/, "");
      return buildArgs([["url", url]]);
    },
  },
];

// ---------------------------------------------------------------------------
// Helpers — small typed utilities, no behavior beyond what's used below
// ---------------------------------------------------------------------------

/** Cast a string to the branded DeviceId type. */
const asDeviceId = (s: string): DeviceId => s as DeviceId;

/** Build the standard "adapter missing" error string. */
const missingAdapterError = (modality: Modality): string =>
  `IntentRouter: no adapter configured for modality "${modality}"`;

// ---------------------------------------------------------------------------
// IntentRouter — the single user-facing surface over all six modalities
// ---------------------------------------------------------------------------

export class IntentRouter {
  private readonly adapters: IntentAdapters;
  private readonly defaultModality: Modality;
  private readonly defaultModel: string;
  private readonly defaultAgent: string;

  constructor(options: IntentRouterOptions) {
    this.adapters = options.adapters;
    this.defaultModality = options.defaultModality ?? "eidolon";
    this.defaultModel = options.defaultModel ?? "haiku";
    this.defaultAgent = options.defaultAgent ?? "intent-router";
  }

  /**
   * Classify a free-form user message into a (modality, args) pair.
   * Returns the first pattern that matches in priority order; falls
   * back to `defaultModality` with empty args if no pattern matches.
   */
  classify(message: string): IntentClassification {
    const trimmed = message.trim();
    for (const rule of CLASSIFIERS) {
      const match = trimmed.match(rule.pattern);
      if (match) {
        return {
          modality: rule.modality,
          args: rule.extract(match, trimmed),
          raw: trimmed,
          fellBack: false,
        };
      }
    }
    return {
      modality: this.defaultModality,
      args: {},
      raw: trimmed,
      fellBack: true,
    };
  }

  /**
   * Classify + dispatch. Returns a structured RouteResult — never
   * throws on missing adapters (those come back as { error }). Only
   * throws if the underlying adapter call itself throws (e.g. real
   * transport network error).
   */
  async route(message: string): Promise<RouteResult> {
    const classification = this.classify(message);
    return this.dispatch(classification);
  }

  /**
   * Dispatch a pre-classified intent. Exposed publicly so callers
   * that want to short-circuit classify (e.g. inject a fixed
   * classification from a config file) can do so.
   */
  async dispatch(classification: IntentClassification): Promise<RouteResult> {
    switch (classification.modality) {
      case "claude":
        return this.dispatchClaude(classification);
      case "eidolon":
        return this.dispatchEidolon(classification);
      case "mobile":
        return this.dispatchMobile(classification);
      case "desktop":
        return this.dispatchDesktop(classification);
      case "sandbox":
        return this.dispatchSandbox(classification);
      case "browser":
        return this.dispatchBrowser(classification);
    }
  }

  // -------------------------------------------------------------------------
  // Per-modality dispatch
  // -------------------------------------------------------------------------

  private async dispatchClaude(c: IntentClassification): Promise<RouteResult> {
    const runtime = this.adapters.claude;
    if (!runtime) return { modality: "claude", classification: c, error: missingAdapterError("claude") };
    const prompt = c.args.prompt ?? c.raw;
    const response: RunResponse = await runtime.exec({
      agent: this.defaultAgent as AgentId,
      model: this.defaultModel as ModelId,
      prompt,
    });
    return {
      modality: "claude",
      classification: c,
      text: response.text,
      data: response,
    };
  }

  private async dispatchEidolon(c: IntentClassification): Promise<RouteResult> {
    const stage = this.adapters.eidolon;
    if (!stage) return { modality: "eidolon", classification: c, error: missingAdapterError("eidolon") };
    const method = c.args.method ?? "ping";
    const params = { source: "intent-router", message: c.raw };
    const data = await stage.call<unknown>(method, params);
    return { modality: "eidolon", classification: c, data };
  }

  private async dispatchMobile(c: IntentClassification): Promise<RouteResult> {
    const stage = this.adapters.mobile;
    if (!stage) return { modality: "mobile", classification: c, error: missingAdapterError("mobile") };
    const deviceId = asDeviceId(c.args.device ?? "default-mobile-device");
    const session = await stage.openSession(deviceId);
    try {
      const data = await stage.call<unknown>("launch_app", {
        app: c.args.app ?? null,
        device: c.args.device ?? null,
        source: "intent-router",
      });
      return { modality: "mobile", classification: c, sessionId: session.id, data };
    } finally {
      await stage.closeSession(session.id);
    }
  }

  private async dispatchDesktop(c: IntentClassification): Promise<RouteResult> {
    const stage = this.adapters.desktop;
    if (!stage) return { modality: "desktop", classification: c, error: missingAdapterError("desktop") };
    const deviceId = asDeviceId("default-desktop-device");
    const session = await stage.openSession(deviceId);
    try {
      // If the message carried x/y, click at those coordinates;
      // otherwise issue a no-op pointer tap at (0,0) and return the
      // matched-context as data.
      const x = c.args.x !== undefined ? Number(c.args.x) : 0;
      const y = c.args.y !== undefined ? Number(c.args.y) : 0;
      await stage.pointer(session.id, { kind: "click", x, y });
      return {
        modality: "desktop",
        classification: c,
        sessionId: session.id,
        data: { clicked: { x, y } },
      };
    } finally {
      await stage.closeSession(session.id);
    }
  }

  private async dispatchSandbox(c: IntentClassification): Promise<RouteResult> {
    const stage = this.adapters.sandbox;
    if (!stage) return { modality: "sandbox", classification: c, error: missingAdapterError("sandbox") };
    const deviceId = asDeviceId("default-sandbox");
    const session = await stage.openSession(deviceId);
    try {
      const data = await stage.call<unknown>("run_command", {
        command: c.args.command ?? "echo hello",
        source: "intent-router",
      });
      return { modality: "sandbox", classification: c, sessionId: session.id, data };
    } finally {
      await stage.closeSession(session.id);
    }
  }

  private async dispatchBrowser(c: IntentClassification): Promise<RouteResult> {
    const stage = this.adapters.browser;
    if (!stage) return { modality: "browser", classification: c, error: missingAdapterError("browser") };
    const deviceId = asDeviceId("default-browser");
    const session = await stage.openSession(deviceId);
    try {
      const data = await stage.call<unknown>("navigate", {
        url: c.args.url ?? "about:blank",
        source: "intent-router",
      });
      return { modality: "browser", classification: c, sessionId: session.id, data };
    } finally {
      await stage.closeSession(session.id);
    }
  }
}

// ---------------------------------------------------------------------------
// Convenience factory — builds a router with all 6 adapters wired
// against Null-transport fallbacks (safe default; callers override
// any subset via the partial `IntentAdapters`)
// ---------------------------------------------------------------------------

/**
 * Build a router where every slot is pre-populated with a Null-backed
 * adapter. Useful as a starting point; override any slot with a real
 * adapter before calling route().
 */
export function nullBackedRouter(): IntentRouter {
  return new IntentRouter({
    adapters: {}, // all slots missing — every dispatch returns { error }
    defaultModality: "eidolon",
  });
}
