import { describe, it, expect } from "vitest";
import {
  EidolonStage,
  NullTransport,
  McpStdioTransport,
  McpHttpTransport,
  type EidolonTransport,
  type McpResult,
} from "../adapters/eidolon";
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
 * Build a mock transport that returns the given data keyed by MCP method name.
 * Any method not in the map returns { ok: false, error: "not implemented" }.
 */
function createMockTransport(
  dataMap: Record<string, unknown>,
): EidolonTransport {
  return {
    name: "mock-transport",
    async call<T = unknown>(
      method: string,
      _params?: Record<string, unknown>,
    ): Promise<McpResult<T>> {
      if (method in dataMap) {
        return { ok: true, data: dataMap[method] as T };
      }
      return { ok: false, error: `not implemented: ${method}` };
    },
  };
}

function makeStage(
  transport: NullTransport | EidolonTransport,
): EidolonStage {
  return new EidolonStage({
    name: "test-stage",
    transport: "custom",
    customTransport: transport,
  });
}

const SID = "session-1" as SessionId;
const DID = "device-1" as DeviceId;

// ---------------------------------------------------------------------------
// Transport abstraction tests
// ---------------------------------------------------------------------------

describe("EidolonStage transport abstraction", () => {
  // 1. NullTransport returns error for any method call
  it("NullTransport returns error for any call", async () => {
    const nullTransport = new NullTransport();
    expect(nullTransport.name).toBe("null");

    const resultA = await nullTransport.call("list_devices");
    expect(resultA.ok).toBe(false);
    expect(resultA.error).toContain("Eidolon not reachable");

    const resultB = await nullTransport.call("open_session", { deviceId: "d1" });
    expect(resultB.ok).toBe(false);
    expect(resultB.error).toContain("Eidolon not reachable");

    const resultC = await nullTransport.call("unknown_method_r2d2");
    expect(resultC.ok).toBe(false);
    expect(resultC.error).toContain("Eidolon not reachable");
  });

  // 2. Custom transport returns expected data for each DeviceStage method
  it("custom transport returns expected data for all DeviceStage methods", async () => {
    const now = new Date().toISOString();
    const mockDevices: readonly DeviceId[] = [DID];
    const mockSession: DeviceSession = {
      id: SID,
      deviceId: DID,
      modality: "mobile",
      startedAt: now,
    };
    const mockViewport: Viewport = { width: 390, height: 844, scale: 3 };
    const mockScreenshot: ScreenshotResult = {
      path: "/tmp/test.png",
      format: "png",
      width: 390,
      height: 844,
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

    const stage = makeStage(transport);

    // listDevices
    const devices = await stage.listDevices();
    expect(devices).toEqual(mockDevices);

    // openSession
    const session = await stage.openSession(DID);
    expect(session).toEqual(mockSession);

    // closeSession
    await expect(stage.closeSession(SID)).resolves.toBeUndefined();

    // pointer
    const pointerInput: PointerInput = { kind: "tap", x: 100, y: 200 };
    await expect(stage.pointer(SID, pointerInput)).resolves.toBeUndefined();

    // key
    const keyInput: KeyInput = { kind: "type", text: "hello" };
    await expect(stage.key(SID, keyInput)).resolves.toBeUndefined();

    // screenshot
    const screenshot = await stage.screenshot(SID, "/tmp/test.png");
    expect(screenshot).toEqual(mockScreenshot);

    // viewport
    const vp = await stage.viewport(SID);
    expect(vp).toEqual(mockViewport);
  });

  // 3. Calling DeviceStage methods without a real transport throws
  it("calling any DeviceStage method via NullTransport throws an error", async () => {
    const stage = makeStage(new NullTransport());

    await expect(stage.listDevices()).rejects.toThrow(/Eidolon not reachable/);
    await expect(stage.openSession(DID)).rejects.toThrow(/Eidolon not reachable/);
    await expect(stage.closeSession(SID)).rejects.toThrow(/Eidolon not reachable/);
    await expect(
      stage.pointer(SID, { kind: "tap", x: 0, y: 0 }),
    ).rejects.toThrow(/Eidolon not reachable/);
    await expect(
      stage.key(SID, { kind: "type", text: "x" }),
    ).rejects.toThrow(/Eidolon not reachable/);
    await expect(
      stage.screenshot(SID, "/tmp/x.png"),
    ).rejects.toThrow(/Eidolon not reachable/);
    await expect(stage.viewport(SID)).rejects.toThrow(/Eidolon not reachable/);
  });

  // 4. All 7 DeviceStage method names follow camelCase convention
  it("all DeviceStage method names follow camelCase convention", () => {
    const stage = makeStage(new NullTransport());

    const prototypeMethods = Object.getOwnPropertyNames(
      Object.getPrototypeOf(stage),
    ).filter(
      (name) =>
        name !== "constructor" &&
        typeof (stage as unknown as Record<string, unknown>)[name] === "function",
    );

    // EidolonStage has: listDevices, openSession, closeSession, pointer,
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
    // Reset singleton so we exercise the fallback path
    resetTracer();

    const tracer = getTracer();
    expect(tracer).toBeDefined();
    expect(typeof tracer.startSpan).toBe("function");

    // Verify the tracer can create a span without throwing
    const span = tracer.startSpan("test-span");
    expect(span).toBeDefined();
    expect(typeof span.end).toBe("function");
    expect(typeof span.recordError).toBe("function");
    expect(typeof span.setAttribute).toBe("function");
    expect(typeof span.setAttributes).toBe("function");

    // Verify no-op behaviour (should not throw)
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
  it("McpStdioTransport conforms to EidolonTransport interface", () => {
    const t = new McpStdioTransport("test", "/usr/local/bin/eidolon-mcp");
    expect(t.name).toBe("stdio:test");
    expect(typeof t.call).toBe("function");
  });

  it("McpHttpTransport conforms to EidolonTransport interface", () => {
    const t = new McpHttpTransport("test", "http://localhost:3100");
    expect(t.name).toBe("http:test");
    expect(typeof t.call).toBe("function");
  });
});
