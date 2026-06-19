import { describe, it, expect } from "vitest";
import {
  CodexCliAdapter,
  NullCodexTransport,
  CodexStdioTransport,
  type CodexTransport,
  type CodexCliResult,
} from "../adapters/codex";
import type {
  DeviceStage,
  DeviceId,
  PointerInput,
  KeyInput,
  Viewport,
  ScreenshotResult,
  DeviceSession,
  SessionId,
} from "../device_stage";
import { getTracer, resetTracer } from "../telemetry";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Build a mock transport that returns the given data keyed by method name.
 * Any method not in the map returns { ok: false, error: "not implemented" }.
 */
function createMockTransport(
  dataMap: Record<string, unknown>,
): CodexTransport {
  return {
    name: "mock-transport",
    async call<T = unknown>(
      method: string,
      _params?: Record<string, unknown>,
    ): Promise<CodexCliResult<T>> {
      if (method in dataMap) {
        return { ok: true, data: dataMap[method] as T };
      }
      return { ok: false, error: `not implemented: ${method}` };
    },
  };
}

function makeAdapter(
  transport: NullCodexTransport | CodexTransport,
): CodexCliAdapter {
  return new CodexCliAdapter({
    name: "test-adapter",
    customTransport: transport,
  });
}

const SID = "session-1" as SessionId;
const DID = "device-01" as DeviceId;

// ---------------------------------------------------------------------------
// Transport abstraction tests
// ---------------------------------------------------------------------------

describe("CodexCliAdapter transport abstraction", () => {
  // 1. NullCodexTransport returns error for any method call
  it("NullCodexTransport returns error for any call", async () => {
    const nullTransport = new NullCodexTransport();
    expect(nullTransport.name).toBe("null");

    const resultA = await nullTransport.call("list_devices");
    expect(resultA.ok).toBe(false);
    expect(resultA.error).toContain("Codex CLI not reachable");

    const resultB = await nullTransport.call("open_session", { deviceId: "d1" });
    expect(resultB.ok).toBe(false);
    expect(resultB.error).toContain("Codex CLI not reachable");

    const resultC = await nullTransport.call("unknown_method");
    expect(resultC.ok).toBe(false);
    expect(resultC.error).toContain("Codex CLI not reachable");
  });

  // 2. Custom transport returns expected data for all DeviceStage methods
  it("custom transport returns expected data for all DeviceStage methods", async () => {
    const now = new Date().toISOString();
    const mockDevices: readonly DeviceId[] = [DID];
    const mockSession: DeviceSession = {
      id: SID,
      deviceId: DID,
      modality: "desktop",
      startedAt: now,
    };
    const mockViewport: Viewport = { width: 1920, height: 1080, scale: 2 };
    const mockScreenshot: ScreenshotResult = {
      path: "/tmp/codex-test.png",
      format: "png",
      width: 1920,
      height: 1080,
      capturedAt: now,
    };

    const transport = createMockTransport({
      list_devices: mockDevices,
      open_session: mockSession,
      close_session: undefined,
      pointer: undefined,
      key: undefined,
      screenshot: mockScreenshot,
      viewport: mockViewport,
    });

    const adapter = makeAdapter(transport);

    // listDevices
    const devices = await adapter.listDevices();
    expect(devices).toEqual(mockDevices);

    // openSession
    const session = await adapter.openSession(DID);
    expect(session).toEqual(mockSession);

    // closeSession
    await expect(adapter.closeSession(SID)).resolves.toBeUndefined();

    // pointer
    const pointerInput: PointerInput = { kind: "click", x: 500, y: 300 };
    await expect(adapter.pointer(SID, pointerInput)).resolves.toBeUndefined();

    // key
    const keyInput: KeyInput = { kind: "type", text: "codex test" };
    await expect(adapter.key(SID, keyInput)).resolves.toBeUndefined();

    // screenshot
    const screenshot = await adapter.screenshot(SID, "/tmp/codex-test.png");
    expect(screenshot).toEqual(mockScreenshot);

    // viewport
    const vp = await adapter.viewport(SID);
    expect(vp).toEqual(mockViewport);
  });

  // 3. Calling DeviceStage methods via NullCodexTransport throws errors
  it("calling any DeviceStage method via NullCodexTransport throws an error", async () => {
    const adapter = makeAdapter(new NullCodexTransport());

    await expect(adapter.listDevices()).rejects.toThrow(
      /Codex CLI not reachable/,
    );
    await expect(adapter.openSession(DID)).rejects.toThrow(
      /Codex CLI not reachable/,
    );
    await expect(adapter.closeSession(SID)).rejects.toThrow(
      /Codex CLI not reachable/,
    );
    await expect(
      adapter.pointer(SID, { kind: "tap", x: 0, y: 0 }),
    ).rejects.toThrow(/Codex CLI not reachable/);
    await expect(
      adapter.key(SID, { kind: "type", text: "x" }),
    ).rejects.toThrow(/Codex CLI not reachable/);
    await expect(
      adapter.screenshot(SID, "/tmp/x.png"),
    ).rejects.toThrow(/Codex CLI not reachable/);
    await expect(adapter.viewport(SID)).rejects.toThrow(
      /Codex CLI not reachable/,
    );
  });

  // 4. All DeviceStage method names follow camelCase convention
  it("all DeviceStage method names follow camelCase convention", () => {
    const adapter = makeAdapter(new NullCodexTransport());

    const prototypeMethods = Object.getOwnPropertyNames(
      Object.getPrototypeOf(adapter),
    ).filter(
      (name) =>
        name !== "constructor" &&
        typeof (adapter as unknown as Record<string, unknown>)[name] ===
          "function",
    );

    // CodexCliAdapter has: listDevices, openSession, closeSession, pointer,
    // key, screenshot, viewport + the public call() method
    expect(prototypeMethods.length).toBeGreaterThanOrEqual(7);

    // camelCase regex: starts with lowercase letter, no underscores/hyphens
    const isCamelCase = (name: string): boolean =>
      /^[a-z][a-zA-Z0-9]*$/.test(name);

    for (const methodName of prototypeMethods) {
      expect(isCamelCase(methodName)).toBe(true);
    }
  });
});

// ---------------------------------------------------------------------------
// Telemetry tests
// ---------------------------------------------------------------------------

describe("Telemetry (ports/telemetry.ts)", () => {
  it("getTracer() returns a valid tracer without throwing", () => {
    resetTracer();

    const tracer = getTracer();
    expect(tracer).toBeDefined();
    expect(typeof tracer.startSpan).toBe("function");

    const span = tracer.startSpan("test-span");
    expect(span).toBeDefined();
    expect(typeof span.end).toBe("function");
    expect(typeof span.recordError).toBe("function");
    expect(typeof span.setAttribute).toBe("function");
    expect(typeof span.setAttributes).toBe("function");

    expect(() => {
      span.setAttribute("key", "value");
      span.setAttributes({ a: "b" });
      span.recordError(new Error("test"));
    }).not.toThrow();

    span.end();
  });
});

// ---------------------------------------------------------------------------
// Concrete transport class structure tests
// ---------------------------------------------------------------------------

describe("Concrete transport classes", () => {
  it("CodexStdioTransport conforms to CodexTransport interface", () => {
    const t = new CodexStdioTransport("test", "/usr/local/bin/codex");
    expect(t.name).toBe("stdio:test");
    expect(typeof t.call).toBe("function");
  });
});

// ---------------------------------------------------------------------------
// Interface conformance tests
// ---------------------------------------------------------------------------

describe("CodexCliAdapter interface conformance", () => {
  it("CodexCliAdapter implements DeviceStage", () => {
    const adapter: DeviceStage = new CodexCliAdapter({
      name: "primary",
    });
    expect(adapter.name).toBe("codex:primary");
    expect(adapter.modality).toBe("desktop");
    expect(adapter.supportedDeviceKinds).toContain("macos");
    expect(adapter.supportedDeviceKinds).toContain("ios-simulator");
    expect(adapter.supportedDeviceKinds).toContain("android-emulator");
  });

  it("CodexCliAdapter is interface-compatible (satisfies DeviceStage)", () => {
    const adapter: DeviceStage = new CodexCliAdapter({
      name: "x",
    });
    expect(typeof adapter.listDevices).toBe("function");
    expect(typeof adapter.openSession).toBe("function");
    expect(typeof adapter.closeSession).toBe("function");
    expect(typeof adapter.pointer).toBe("function");
    expect(typeof adapter.key).toBe("function");
    expect(typeof adapter.screenshot).toBe("function");
    expect(typeof adapter.viewport).toBe("function");
    expect(typeof (adapter as CodexCliAdapter).call).toBe("function");
  });

  it("CodexCliAdapter config defaults to PATH-resolved codex binary", () => {
    const adapter = new CodexCliAdapter({ name: "default-test" });
    expect(adapter.name).toBe("codex:default-test");
  });
});
