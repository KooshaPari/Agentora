/**
 * test.ts — vitest cases for the intent-router example.
 *
 * One test per modality (6 total). Each test wires a real DeviceStage
 * adapter (e.g. MobileDeviceStage, BrowserStage) against a
 * recording-mock transport, runs the router, and asserts that:
 *
 *   1. classify() returns the correct modality + extracted args
 *   2. dispatch() actually invokes the right adapter methods
 *   3. sessions are opened and closed properly
 *   4. error paths (missing adapter) are structured, not thrown
 *
 * The mocks are intentionally non-throwing: a Null-transport-based
 * adapter would throw on every call, and we want to verify the
 * router *composes* the trait family — not the transport behaviour.
 */

import { describe, it, expect } from "vitest";

import {
  IntentRouter,
  type IntentAdapters,
  type RouteResult,
} from "./intent-router";

import {
  MobileDeviceStage,
  NullMobileTransport,
  type MobileTransport,
  type MobileMcpResult,
} from "../../ports/adapters/mobile";
import {
  DesktopStage,
  NullDesktopTransport,
  type DesktopTransport,
  type DesktopMcpResult,
} from "../../ports/adapters/desktop";
import {
  SandboxStage,
  NullSandboxTransport,
  type SandboxTransport,
  type SandboxMcpResult,
} from "../../ports/adapters/sandbox";
import {
  BrowserStage,
  NullBrowserTransport,
  type BrowserTransport,
  type BrowserMcpResult,
} from "../../ports/adapters/browser";
import {
  EidolonStage,
  NullTransport,
  type EidolonTransport,
  type McpResult,
} from "../../ports/adapters/eidolon";
import { ClaudeRuntime } from "../../ports/adapters/claude";

import type {
  DeviceId,
  DeviceSession,
  SessionId,
} from "../../ports/device_stage";

// ---------------------------------------------------------------------------
// Shared recording-mock infrastructure
// ---------------------------------------------------------------------------

interface CallRecord {
  readonly method: string;
  readonly params?: Record<string, unknown>;
}

/**
 * Build a recording mock transport for any of the 5 DeviceStage flavors
 * + the Eidolon transport. Each call appends to `calls`; the
 * caller can also supply a static `dataMap` for methods that need to
 * return shaped data (e.g. open_session -> DeviceSession).
 */
function makeRecordingMock<TParams, TResult>(opts: {
  readonly name: string;
  readonly dataMap?: Record<string, unknown>;
}): { transport: { readonly name: string; call: (m: string, p?: TParams) => Promise<TResult> }; calls: CallRecord[] } {
  const calls: CallRecord[] = [];
  const transport = {
    name: opts.name,
    async call(method: string, params?: TParams): Promise<TResult> {
      calls.push({ method, params: params as unknown as Record<string, unknown> });
      if (opts.dataMap && method in opts.dataMap) {
        return { ok: true, data: opts.dataMap[method] } as unknown as TResult;
      }
      return { ok: true, data: undefined } as unknown as TResult;
    },
  };
  return { transport, calls };
}

const SESSION_ID = "sess-mock-1" as SessionId;
const DEVICE_ID = "dev-mock-1" as DeviceId;
const MOCK_SESSION: DeviceSession = {
  id: SESSION_ID,
  deviceId: DEVICE_ID,
  modality: "mobile",
  startedAt: new Date().toISOString(),
};
const MOCK_DESKTOP_SESSION: DeviceSession = {
  id: SESSION_ID,
  deviceId: DEVICE_ID,
  modality: "desktop",
  startedAt: new Date().toISOString(),
};
const MOCK_SANDBOX_SESSION: DeviceSession = {
  id: SESSION_ID,
  deviceId: DEVICE_ID,
  modality: "sandbox",
  startedAt: new Date().toISOString(),
};
const MOCK_BROWSER_SESSION: DeviceSession = {
  id: SESSION_ID,
  deviceId: DEVICE_ID,
  modality: "browser",
  startedAt: new Date().toISOString(),
};

// ---------------------------------------------------------------------------
// 1. mobile — "open Safari on my iPhone"
// ---------------------------------------------------------------------------

describe("intent-router — mobile", () => {
  it("classifies 'open Safari on my iPhone' as mobile and dispatches to MobileDeviceStage", async () => {
    const { transport, calls } = makeRecordingMock<Record<string, unknown>, MobileMcpResult<unknown>>({
      name: "mock-mobile-rec",
      dataMap: { open_session: MOCK_SESSION, launch_app: { launched: true, app: "Safari" } },
    });
    const mockMobile = transport as unknown as MobileTransport;

    const adapters: IntentAdapters = {
      mobile: new MobileDeviceStage({
        name: "iphone-15",
        type: "custom",
        customTransport: mockMobile,
      }),
    };
    const router = new IntentRouter({ adapters });

    const result: RouteResult = await router.route("open Safari on my iPhone");

    // Classifier result
    expect(result.classification.modality).toBe("mobile");
    expect(result.classification.fellBack).toBe(false);
    expect(result.classification.args.app?.toLowerCase()).toBe("safari");
    expect(result.classification.args.device?.toLowerCase()).toContain("iphone");

    // Dispatch result
    expect(result.modality).toBe("mobile");
    expect(result.error).toBeUndefined();
    expect(result.sessionId).toBe(SESSION_ID);
    expect((result.data as { launched: boolean }).launched).toBe(true);

    // Transport received the right call sequence
    const methods = calls.map((c) => c.method);
    expect(methods).toEqual(["open_session", "launch_app", "close_session"]);

    // open_session was called with the right deviceId
    const openCall = calls.find((c) => c.method === "open_session");
    expect(openCall?.params?.deviceId).toBe("iphone");
  });

  it("classifies 'on my phone' as mobile", () => {
    const router = new IntentRouter({ adapters: {} });
    const c = router.classify("tap on something on my phone");
    expect(c.modality).toBe("mobile");
  });
});

// ---------------------------------------------------------------------------
// 2. claude — "ask Claude to refactor this"
// ---------------------------------------------------------------------------

describe("intent-router — claude", () => {
  it("classifies 'ask Claude to refactor this' as claude and dispatches to ClaudeRuntime", async () => {
    const adapters: IntentAdapters = { claude: new ClaudeRuntime() };
    const router = new IntentRouter({ adapters, defaultModel: "haiku" });

    const result = await router.route("ask Claude to refactor this file");

    // Classifier result
    expect(result.classification.modality).toBe("claude");
    expect(result.classification.fellBack).toBe(false);
    expect(result.classification.args.prompt).toBe("refactor this file");

    // Dispatch result — ClaudeRuntime echoes the prompt in the text
    expect(result.modality).toBe("claude");
    expect(result.text).toContain("refactor this file");
    expect(result.text).toContain("[claude:haiku]");
    expect(result.error).toBeUndefined();
  });

  it("classifies 'via claude' as claude", () => {
    const router = new IntentRouter({ adapters: {} });
    const c = router.classify("explain this regex via claude");
    expect(c.modality).toBe("claude");
  });
});

// ---------------------------------------------------------------------------
// 3. sandbox — "run a sandbox"
// ---------------------------------------------------------------------------

describe("intent-router — sandbox", () => {
  it("classifies 'run a sandbox' as sandbox and dispatches to SandboxStage", async () => {
    const { transport, calls } = makeRecordingMock<Record<string, unknown>, SandboxMcpResult<unknown>>({
      name: "mock-sandbox-rec",
      dataMap: { open_session: MOCK_SANDBOX_SESSION, run_command: { stdout: "ok", exitCode: 0 } },
    });
    const mockSandbox = transport as unknown as SandboxTransport;

    const adapters: IntentAdapters = {
      sandbox: new SandboxStage({
        name: "ephemeral-vm",
        type: "custom",
        customTransport: mockSandbox,
      }),
    };
    const router = new IntentRouter({ adapters });

    const result = await router.route("run a sandbox");

    expect(result.classification.modality).toBe("sandbox");
    expect(result.classification.fellBack).toBe(false);

    expect(result.modality).toBe("sandbox");
    expect(result.error).toBeUndefined();
    expect(result.sessionId).toBe(SESSION_ID);
    expect((result.data as { exitCode: number }).exitCode).toBe(0);

    const methods = calls.map((c) => c.method);
    expect(methods).toEqual(["open_session", "run_command", "close_session"]);
  });

  it("classifies 'firecracker' as sandbox", () => {
    const router = new IntentRouter({ adapters: {} });
    const c = router.classify("spin up a firecracker microvm");
    expect(c.modality).toBe("sandbox");
  });
});

// ---------------------------------------------------------------------------
// 4. browser — "navigate to example.com in browser"
// ---------------------------------------------------------------------------

describe("intent-router — browser", () => {
  it("classifies 'navigate to example.com in browser' as browser and dispatches to BrowserStage", async () => {
    const { transport, calls } = makeRecordingMock<Record<string, unknown>, BrowserMcpResult<unknown>>({
      name: "mock-browser-rec",
      dataMap: { open_session: MOCK_BROWSER_SESSION, navigate: { loaded: true, url: "example.com" } },
    });
    const mockBrowser = transport as unknown as BrowserTransport;

    const adapters: IntentAdapters = {
      browser: new BrowserStage({
        name: "chromium",
        type: "custom",
        customTransport: mockBrowser,
      }),
    };
    const router = new IntentRouter({ adapters });

    const result = await router.route("navigate to example.com in browser");

    expect(result.classification.modality).toBe("browser");
    expect(result.classification.fellBack).toBe(false);
    expect(result.classification.args.url).toBe("example.com");

    expect(result.modality).toBe("browser");
    expect(result.error).toBeUndefined();
    expect(result.sessionId).toBe(SESSION_ID);
    expect((result.data as { loaded: boolean }).loaded).toBe(true);

    const methods = calls.map((c) => c.method);
    expect(methods).toEqual(["open_session", "navigate", "close_session"]);

    // navigate was called with the right URL
    const navCall = calls.find((c) => c.method === "navigate");
    expect(navCall?.params?.url).toBe("example.com");
  });

  it("classifies a bare URL as browser", () => {
    const router = new IntentRouter({ adapters: {} });
    const c = router.classify("open https://example.org/path");
    expect(c.modality).toBe("browser");
    expect(c.args.url).toBe("https://example.org/path");
  });
});

// ---------------------------------------------------------------------------
// 5. desktop — "click on desktop"
// ---------------------------------------------------------------------------

describe("intent-router — desktop", () => {
  it("classifies 'click on desktop' as desktop and dispatches to DesktopStage", async () => {
    const { transport, calls } = makeRecordingMock<Record<string, unknown>, DesktopMcpResult<unknown>>({
      name: "mock-desktop-rec",
      dataMap: { open_session: MOCK_DESKTOP_SESSION },
    });
    const mockDesktop = transport as unknown as DesktopTransport;

    const adapters: IntentAdapters = {
      desktop: new DesktopStage({
        name: "macos-stage",
        type: "custom",
        customTransport: mockDesktop,
      }),
    };
    const router = new IntentRouter({ adapters });

    const result = await router.route("click on desktop");

    expect(result.classification.modality).toBe("desktop");
    expect(result.classification.fellBack).toBe(false);

    expect(result.modality).toBe("desktop");
    expect(result.error).toBeUndefined();
    expect(result.sessionId).toBe(SESSION_ID);
    expect((result.data as { clicked: { x: number; y: number } }).clicked).toEqual({ x: 0, y: 0 });

    const methods = calls.map((c) => c.method);
    expect(methods).toEqual(["open_session", "pointer", "close_session"]);

    // pointer was issued with kind=click
    const ptrCall = calls.find((c) => c.method === "pointer");
    expect(ptrCall?.params?.kind).toBe("click");
  });

  it("classifies 'on my mac' as desktop", () => {
    const router = new IntentRouter({ adapters: {} });
    const c = router.classify("click there on my mac");
    expect(c.modality).toBe("desktop");
  });
});

// ---------------------------------------------------------------------------
// 6. eidolon — "dispatch via Eidolon"
// ---------------------------------------------------------------------------

describe("intent-router — eidolon", () => {
  it("classifies 'dispatch via Eidolon' as eidolon and dispatches to EidolonStage", async () => {
    const { transport, calls } = makeRecordingMock<Record<string, unknown>, McpResult<unknown>>({
      name: "mock-eidolon-rec",
      dataMap: { ping: { pong: true, ts: 1700000000 } },
    });
    const mockEidolon = transport as unknown as EidolonTransport;

    const adapters: IntentAdapters = {
      eidolon: new EidolonStage({
        name: "eidolon-mcp",
        transport: "custom",
        customTransport: mockEidolon,
        defaultModality: "desktop",
      }),
    };
    const router = new IntentRouter({ adapters });

    const result = await router.route("dispatch via Eidolon");

    expect(result.classification.modality).toBe("eidolon");
    expect(result.classification.fellBack).toBe(false);
    expect(result.classification.args.method).toBe("ping");

    expect(result.modality).toBe("eidolon");
    expect(result.error).toBeUndefined();
    expect((result.data as { pong: boolean }).pong).toBe(true);

    // Eidolon is the canonical hub — single .call() no session
    const methods = calls.map((c) => c.method);
    expect(methods).toEqual(["ping"]);
  });

  it("classifies 'via eidolon' as eidolon and lets the caller override the method", () => {
    const router = new IntentRouter({ adapters: {} });
    const c = router.classify("via eidolon method=custom_method");
    expect(c.modality).toBe("eidolon");
    expect(c.args.method).toBe("custom_method");
  });
});

// ---------------------------------------------------------------------------
// 7. structured-error path — adapter missing for the classified modality
// ---------------------------------------------------------------------------

describe("intent-router — missing adapter error path", () => {
  it("returns { error } (does not throw) when the classified modality has no adapter", async () => {
    // No mobile adapter wired, but message is mobile-flavoured
    const router = new IntentRouter({ adapters: {} });
    const result = await router.route("open Maps on my iPhone");

    expect(result.modality).toBe("mobile");
    expect(result.error).toContain("no adapter configured");
    expect(result.error).toContain("mobile");
  });

  it("falls back to defaultModality when no classifier matches", async () => {
    const { transport, calls } = makeRecordingMock<Record<string, unknown>, McpResult<unknown>>({
      name: "mock-eidolon-fallback",
    });
    const mockEidolon = transport as unknown as EidolonTransport;

    const adapters: IntentAdapters = {
      eidolon: new EidolonStage({
        name: "eidolon-fallback",
        transport: "custom",
        customTransport: mockEidolon,
        defaultModality: "mobile",
      }),
    };
    // Default = eidolon, message is gibberish — should hit the fallback path
    const router = new IntentRouter({ adapters, defaultModality: "eidolon" });
    const result = await router.route("just do the thing");

    expect(result.classification.fellBack).toBe(true);
    expect(result.classification.modality).toBe("eidolon");
    expect(result.error).toBeUndefined();
    expect(calls.length).toBe(1);
  });
});

// ---------------------------------------------------------------------------
// 8. priority — claude beats eidolon beats mobile beats browser on overlap
// ---------------------------------------------------------------------------

describe("intent-router — classifier priority", () => {
  it("claude wins over mobile/eidolon when 'claude' keyword is present", () => {
    const router = new IntentRouter({ adapters: {} });
    // 'via' alone matches neither; 'claude' matches first
    const c = router.classify("have claude run on my iPhone via the eidolon hub");
    expect(c.modality).toBe("claude");
  });

  it("eidolon wins over mobile when 'via eidolon' is present", () => {
    const router = new IntentRouter({ adapters: {} });
    const c = router.classify("dispatch via eidolon from my iPhone");
    expect(c.modality).toBe("eidolon");
  });

  it("mobile wins over browser when iPhone is present (apps beat URLs)", () => {
    const router = new IntentRouter({ adapters: {} });
    // 'open Safari on my iPhone' — first matching classifier is mobile
    const c = router.classify("open Safari on my iPhone");
    expect(c.modality).toBe("mobile");
  });
});

// ---------------------------------------------------------------------------
// 9. Null-transport safety — adapters with no real backend compose cleanly
// ---------------------------------------------------------------------------

describe("intent-router — Null-transport composability", () => {
  it("router with Null-backed adapters rejects classify() output with a structured error, never throws", async () => {
    const adapters: IntentAdapters = {
      mobile: new MobileDeviceStage({ name: "n", type: "custom", customTransport: new NullMobileTransport() }),
      desktop: new DesktopStage({ name: "n", type: "custom", customTransport: new NullDesktopTransport() }),
      sandbox: new SandboxStage({ name: "n", type: "custom", customTransport: new NullSandboxTransport() }),
      browser: new BrowserStage({ name: "n", type: "custom", customTransport: new NullBrowserTransport() }),
      eidolon: new EidolonStage({ name: "n", transport: "custom", customTransport: new NullTransport() }),
      claude: new ClaudeRuntime(),
    };
    const router = new IntentRouter({ adapters });

    // 5 modalities: each adapter (except Claude) throws a "tooling not
    // available" error. The router should propagate that as a thrown
    // error from .route() — verifying the trait family composes behind
    // the router's single surface.
    await expect(router.route("open Safari on my iPhone")).rejects.toThrow(/Mobile tooling not available/);
    await expect(router.route("click on desktop")).rejects.toThrow(/Desktop tooling not available/);
    await expect(router.route("run a sandbox")).rejects.toThrow(/Sandbox tooling not available/);
    await expect(router.route("navigate to example.com in browser")).rejects.toThrow(/Browser tooling not available/);
    await expect(router.route("dispatch via Eidolon")).rejects.toThrow(/Eidolon not reachable/);
  });
});
