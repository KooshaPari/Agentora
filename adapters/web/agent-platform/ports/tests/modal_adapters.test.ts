import { describe, it, expect } from "vitest";
import {
  DesktopStageAdapter,
  nullDesktopStage,
  DesktopStage,
  NullDesktopTransport,
  MacOsDesktopTransport,
  LinuxDesktopTransport,
  type DesktopStageConfig,
} from "../adapters/desktop";
import { NullTransport } from "../adapters/eidolon";
import type { EidolonTransport, McpResult } from "../adapters/eidolon";
import {
  MobileDeviceStage,
  NullMobileTransport,
  AdbTransport,
  McpMobileTransport,
  type MobileTransport,
  type MobileMcpResult,
} from "../adapters/mobile";
import {
  SandboxStage,
  NullSandboxTransport,
  EidolonSandboxTransport,
  type SandboxTransport,
  type SandboxMcpResult,
} from "../adapters/sandbox";
import {
  BrowserStage,
  NullBrowserTransport,
  PlaywrightMcpTransport,
  PuppeteerMcpTransport,
  type BrowserTransport,
  type BrowserMcpResult,
} from "../adapters/browser";
import type {
  DeviceStage,
  DeviceId,
  SessionId,
  PointerInput,
  KeyInput,
  Viewport,
  ScreenshotResult,
  DeviceSession,
} from "../device_stage";

// ---------------------------------------------------------------------------
// Shared fixture data
// ---------------------------------------------------------------------------

const SID = "session-1" as SessionId;
const DID = "device-1" as DeviceId;
const NOW = new Date().toISOString();

const MOCK_DEVICES: readonly DeviceId[] = [DID];
const MOCK_SESSION: DeviceSession = {
  id: SID,
  deviceId: DID,
  modality: "desktop",
  startedAt: NOW,
};
const MOCK_VIEWPORT: Viewport = { width: 1920, height: 1080, scale: 1 };
const MOCK_SCREENSHOT: ScreenshotResult = {
  path: "/tmp/test.png",
  format: "png",
  width: 1920,
  height: 1080,
  capturedAt: NOW,
};

// ---------------------------------------------------------------------------
// Helpers — mock transport factories for each modality
// ---------------------------------------------------------------------------

function createMockDesktopTransport(dataMap: Record<string, unknown>): EidolonTransport {
  return {
    name: "mock-desktop",
    async call<T>(method: string, _params?: Record<string, unknown>): Promise<McpResult<T>> {
      if (method in dataMap) return { ok: true, data: dataMap[method] as T };
      return { ok: false, error: `not implemented: ${method}` };
    },
  };
}

function createMockMobileTransport(dataMap: Record<string, unknown>): MobileTransport {
  return {
    name: "mock-mobile",
    async call<T>(method: string, _params?: Record<string, unknown>): Promise<MobileMcpResult<T>> {
      if (method in dataMap) return { ok: true, data: dataMap[method] as T };
      return { ok: false, error: `not implemented: ${method}` };
    },
  };
}

function createMockSandboxTransport(dataMap: Record<string, unknown>): SandboxTransport {
  return {
    name: "mock-sandbox",
    async call<T>(method: string, _params?: Record<string, unknown>): Promise<SandboxMcpResult<T>> {
      if (method in dataMap) return { ok: true, data: dataMap[method] as T };
      return { ok: false, error: `not implemented: ${method}` };
    },
  };
}

function createMockBrowserTransport(dataMap: Record<string, unknown>): BrowserTransport {
  return {
    name: "mock-browser",
    async call<T>(method: string, _params?: Record<string, unknown>): Promise<BrowserMcpResult<T>> {
      if (method in dataMap) return { ok: true, data: dataMap[method] as T };
      return { ok: false, error: `not implemented: ${method}` };
    },
  };
}

// ---------------------------------------------------------------------------
// 1. Null transport returns error for any call — all 4 adapters
// ---------------------------------------------------------------------------

describe("Null transport — all 4 adapters", () => {
  it("NullDesktopTransport returns error for any call", async () => {
    const t = new NullDesktopTransport();
    expect(t.name).toBe("null-desktop");

    const r1 = await t.call("list_devices");
    expect(r1.ok).toBe(false);
    expect(r1.error).toContain("Desktop tooling not available");

    const r2 = await t.call("open_session", { deviceId: "d1" });
    expect(r2.ok).toBe(false);
    expect(r2.error).toContain("Desktop tooling not available");

    const r3 = await t.call("no_such_method");
    expect(r3.ok).toBe(false);
    expect(r3.error).toContain("Desktop tooling not available");
  });

  it("NullMobileTransport returns error for any call", async () => {
    const t = new NullMobileTransport();
    expect(t.name).toBe("null-mobile");

    const r = await t.call("list_devices");
    expect(r.ok).toBe(false);
    expect(r.error).toContain("Mobile tooling not available");
  });

  it("NullSandboxTransport returns error for any call", async () => {
    const t = new NullSandboxTransport();
    expect(t.name).toBe("null-sandbox");

    const r = await t.call("list_devices");
    expect(r.ok).toBe(false);
    expect(r.error).toContain("Sandbox tooling not available");
  });

  it("NullBrowserTransport returns error for any call", async () => {
    const t = new NullBrowserTransport();
    expect(t.name).toBe("null-browser");

    const r = await t.call("list_devices");
    expect(r.ok).toBe(false);
    expect(r.error).toContain("Browser tooling not available");
  });
});

// ---------------------------------------------------------------------------
// 2. Null transport throws when used through DeviceStage methods
// ---------------------------------------------------------------------------

describe("Null transport throws through DeviceStage — all 4 adapters", () => {
  it("NullDesktopTransport throws on every DesktopStage method", async () => {
    const stage = new DesktopStage({ name: "test", type: "custom", customTransport: new NullDesktopTransport() });

    await expect(stage.listDevices()).rejects.toThrow(/Desktop tooling not available/);
    await expect(stage.openSession(DID)).rejects.toThrow(/Desktop tooling not available/);
    await expect(stage.closeSession(SID)).rejects.toThrow(/Desktop tooling not available/);
    await expect(stage.pointer(SID, { kind: "tap", x: 0, y: 0 })).rejects.toThrow(
      /Desktop tooling not available/,
    );
    await expect(stage.key(SID, { kind: "type", text: "x" })).rejects.toThrow(
      /Desktop tooling not available/,
    );
    await expect(stage.screenshot(SID, "/tmp/x.png")).rejects.toThrow(
      /Desktop tooling not available/,
    );
    await expect(stage.viewport(SID)).rejects.toThrow(/Desktop tooling not available/);
  });

  it("NullMobileTransport throws on MobileDeviceStage methods", async () => {
    const stage = new MobileDeviceStage({ name: "test", type: "custom", customTransport: new NullMobileTransport() });

    await expect(stage.listDevices()).rejects.toThrow(/Mobile tooling not available/);
    await expect(stage.openSession(DID)).rejects.toThrow(/Mobile tooling not available/);
    await expect(stage.pointer(SID, { kind: "tap", x: 0, y: 0 })).rejects.toThrow(
      /Mobile tooling not available/,
    );
    await expect(stage.key(SID, { kind: "type", text: "x" })).rejects.toThrow(
      /Mobile tooling not available/,
    );
  });

  it("NullSandboxTransport throws on SandboxStage methods", async () => {
    const stage = new SandboxStage({ name: "test", type: "custom", customTransport: new NullSandboxTransport() });

    await expect(stage.listDevices()).rejects.toThrow(/Sandbox tooling not available/);
    await expect(stage.openSession(DID)).rejects.toThrow(/Sandbox tooling not available/);
    await expect(stage.screenshot(SID, "/tmp/x.png")).rejects.toThrow(
      /Sandbox tooling not available/,
    );
  });

  it("NullBrowserTransport throws on BrowserStage methods", async () => {
    const stage = new BrowserStage({ name: "test", type: "custom", customTransport: new NullBrowserTransport() });

    await expect(stage.listDevices()).rejects.toThrow(/Browser tooling not available/);
    await expect(stage.openSession(DID)).rejects.toThrow(/Browser tooling not available/);
    await expect(stage.pointer(SID, { kind: "click", x: 50, y: 75 })).rejects.toThrow(
      /Browser tooling not available/,
    );
  });
});

// ---------------------------------------------------------------------------
// 3. Modality defaults are correct for each adapter
// ---------------------------------------------------------------------------

describe("Modality defaults", () => {
  it("DesktopStage defaults to 'desktop' modality", () => {
    const s = new DesktopStage({ name: "t", type: "custom", customTransport: new NullDesktopTransport() });
    expect(s.modality).toBe("desktop");
  });

  it("MobileDeviceStage defaults to 'mobile' modality", () => {
    const s = new MobileDeviceStage({ name: "t", type: "custom", customTransport: new NullMobileTransport() });
    expect(s.modality).toBe("mobile");
  });

  it("SandboxStage defaults to 'sandbox' modality", () => {
    const s = new SandboxStage({ name: "t", type: "custom", customTransport: new NullSandboxTransport() });
    expect(s.modality).toBe("sandbox");
  });

  it("BrowserStage defaults to 'browser' modality", () => {
    const s = new BrowserStage({ name: "t", type: "custom", customTransport: new NullBrowserTransport() });
    expect(s.modality).toBe("browser");
  });
});

// ---------------------------------------------------------------------------
// 4. Name conventions follow <modality>:<config-name> pattern
// ---------------------------------------------------------------------------

describe("Name conventions", () => {
  it("DesktopStage name format", () => {
    const s = new DesktopStage({ name: "my-mac", type: "custom", customTransport: new NullDesktopTransport() });
    expect(s.name).toBe("desktop:my-mac");
  });

  it("MobileDeviceStage name format", () => {
    const s = new MobileDeviceStage({ name: "pixel-7", type: "custom", customTransport: new NullMobileTransport() });
    expect(s.name).toBe("mobile:pixel-7");
  });

  it("SandboxStage name format", () => {
    const s = new SandboxStage({ name: "ephemeral-vm", type: "custom", customTransport: new NullSandboxTransport() });
    expect(s.name).toBe("sandbox:ephemeral-vm");
  });

  it("BrowserStage name format", () => {
    const s = new BrowserStage({ name: "chrome-test", type: "custom", customTransport: new NullBrowserTransport() });
    expect(s.name).toBe("browser:chrome-test");
  });
});

// ---------------------------------------------------------------------------
// 5. Custom transport returns expected data for all DeviceStage methods
//    (sampled on DesktopStage as the canonical adapter; the pattern is
//     identical across all 4 adapters)
// ---------------------------------------------------------------------------

describe("Custom transport — DesktopStage full round-trip", () => {
  const transport = createMockDesktopTransport({
    list_devices: MOCK_DEVICES,
    open_session: MOCK_SESSION,
    close_session: undefined,
    pointer: undefined,
    key: undefined,
    screenshot: MOCK_SCREENSHOT,
    viewport: MOCK_VIEWPORT,
  });

  const stage = new DesktopStage({ name: "roundtrip", type: "custom", customTransport: transport });

  it("listDevices returns mock data", async () => {
    const devices = await stage.listDevices();
    expect(devices).toEqual(MOCK_DEVICES);
  });

  it("openSession returns mock session", async () => {
    const session = await stage.openSession(DID);
    expect(session).toEqual(MOCK_SESSION);
  });

  it("closeSession resolves", async () => {
    await expect(stage.closeSession(SID)).resolves.toBeUndefined();
  });

  it("pointer resolves", async () => {
    const input: PointerInput = { kind: "click", x: 100, y: 200 };
    await expect(stage.pointer(SID, input)).resolves.toBeUndefined();
  });

  it("key resolves", async () => {
    const input: KeyInput = { kind: "type", text: "hello" };
    await expect(stage.key(SID, input)).resolves.toBeUndefined();
  });

  it("screenshot returns mock screenshot", async () => {
    const result = await stage.screenshot(SID, "/tmp/test.png");
    expect(result).toEqual(MOCK_SCREENSHOT);
  });

  it("viewport returns mock viewport", async () => {
    const vp = await stage.viewport(SID);
    expect(vp).toEqual(MOCK_VIEWPORT);
  });
});

// ---------------------------------------------------------------------------
// 6. All DeviceStage method names follow camelCase convention
// ---------------------------------------------------------------------------

describe("Method naming — camelCase convention", () => {
  const isCamelCase = (name: string): boolean => /^[a-z][a-zA-Z0-9]*$/.test(name);

  function checkPrototypeMethods(stage: DeviceStage, label: string): void {
    const methods = Object.getOwnPropertyNames(Object.getPrototypeOf(stage)).filter(
      (n) => n !== "constructor" && typeof (stage as unknown as Record<string, unknown>)[n] === "function",
    );
    expect(methods.length).toBeGreaterThanOrEqual(7);
    for (const m of methods) {
      expect(isCamelCase(m)).toBe(true);
    }
  }

  it("DesktopStage", () => {
    checkPrototypeMethods(
      new DesktopStage({ name: "t", type: "custom", customTransport: new NullDesktopTransport() }),
      "DesktopStage",
    );
  });

  it("MobileDeviceStage", () => {
    checkPrototypeMethods(
      new MobileDeviceStage({ name: "t", type: "custom", customTransport: new NullMobileTransport() }),
      "MobileDeviceStage",
    );
  });

  it("SandboxStage", () => {
    checkPrototypeMethods(
      new SandboxStage({ name: "t", type: "custom", customTransport: new NullSandboxTransport() }),
      "SandboxStage",
    );
  });

  it("BrowserStage", () => {
    checkPrototypeMethods(
      new BrowserStage({ name: "t", type: "custom", customTransport: new NullBrowserTransport() }),
      "BrowserStage",
    );
  });
});

// ---------------------------------------------------------------------------
// 7. Concrete transport classes conform to their interfaces
// ---------------------------------------------------------------------------

describe("Concrete transport classes", () => {
  it("MacOsDesktopTransport conforms to DesktopTransport", () => {
    const t = new MacOsDesktopTransport("test");
    expect(t.name).toBe("macos:test");
    expect(typeof t.call).toBe("function");
  });

  it("LinuxDesktopTransport conforms to DesktopTransport", () => {
    const t = new LinuxDesktopTransport("test");
    expect(t.name).toBe("linux:test");
    expect(typeof t.call).toBe("function");
  });

  it("AdbTransport conforms to MobileTransport", () => {
    const t = new AdbTransport("test");
    expect(t.name).toBe("adb:test");
    expect(typeof t.call).toBe("function");
  });

  it("McpMobileTransport conforms to MobileTransport", () => {
    const t = new McpMobileTransport("test", "http://localhost:3400");
    expect(t.name).toBe("mcp-mobile:test");
    expect(typeof t.call).toBe("function");
  });

  it("EidolonSandboxTransport conforms to SandboxTransport", () => {
    const t = new EidolonSandboxTransport("test", "http://localhost:3100");
    expect(t.name).toBe("eidolon-sandbox:test");
    expect(typeof t.call).toBe("function");
  });

  it("PlaywrightMcpTransport conforms to BrowserTransport", () => {
    const t = new PlaywrightMcpTransport("test", "http://localhost:3500");
    expect(t.name).toBe("playwright:test");
    expect(typeof t.call).toBe("function");
  });

  it("PuppeteerMcpTransport conforms to BrowserTransport", () => {
    const t = new PuppeteerMcpTransport("test", "http://localhost:3600");
    expect(t.name).toBe("puppeteer:test");
    expect(typeof t.call).toBe("function");
  });
});

// ---------------------------------------------------------------------------
// 8. Default transport fallback when no customTransport is provided
// ---------------------------------------------------------------------------

describe("Default transport fallback", () => {
  it("DesktopStage defaults to NullDesktopTransport without customTransport", async () => {
    const stage = new DesktopStage({ name: "t", type: "macos-native" });
    await expect(stage.listDevices()).rejects.toThrow(/Desktop tooling not available/);
  });

  it("MobileDeviceStage defaults to NullMobileTransport with unknown type", async () => {
    // @ts-expect-error — testing runtime fallback for unrecognised type
    const stage = new MobileDeviceStage({ name: "t", type: "bogus" });
    await expect(stage.listDevices()).rejects.toThrow(/Mobile tooling not available/);
  });

  it("SandboxStage defaults to NullSandboxTransport without customTransport", async () => {
    const stage = new SandboxStage({ name: "t", type: "custom" });
    await expect(stage.listDevices()).rejects.toThrow(/Sandbox tooling not available/);
  });

  it("BrowserStage defaults to NullBrowserTransport without customTransport", async () => {
    const stage = new BrowserStage({ name: "t", type: "custom" });
    await expect(stage.listDevices()).rejects.toThrow(/Browser tooling not available/);
  });
});

// ---------------------------------------------------------------------------
// 9. supportedDeviceKinds are unique per adapter
// ---------------------------------------------------------------------------

describe("supportedDeviceKinds", () => {
  it("DesktopStage has macOS and Linux kinds", () => {
    const s = new DesktopStage({ name: "t", type: "custom", customTransport: new NullDesktopTransport() });
    expect(s.supportedDeviceKinds).toContain("macos");
    expect(s.supportedDeviceKinds).toContain("linux-x11");
  });

  it("MobileDeviceStage has Android and iOS kinds", () => {
    const s = new MobileDeviceStage({ name: "t", type: "custom", customTransport: new NullMobileTransport() });
    expect(s.supportedDeviceKinds).toContain("android-emulator");
    expect(s.supportedDeviceKinds).toContain("ios-real");
  });

  it("SandboxStage has container and VM kinds", () => {
    const s = new SandboxStage({ name: "t", type: "custom", customTransport: new NullSandboxTransport() });
    expect(s.supportedDeviceKinds).toContain("docker-container");
    expect(s.supportedDeviceKinds).toContain("firecracker-microvm");
  });

  it("BrowserStage has browser engine kinds", () => {
    const s = new BrowserStage({ name: "t", type: "custom", customTransport: new NullBrowserTransport() });
    expect(s.supportedDeviceKinds).toContain("chromium");
    expect(s.supportedDeviceKinds).toContain("firefox");
    expect(s.supportedDeviceKinds).toContain("webkit");
  });
});

// ---------------------------------------------------------------------------
// 10. ADB transport produces valid session IDs
// ---------------------------------------------------------------------------

describe("ADB transport session generation", () => {
  it("AdbTransport.open_session returns a session with correct modality", async () => {
    const t = new AdbTransport("pixel");

    const result = await t.call<DeviceSession>("open_session", { deviceId: "emulator-5554" });
    expect(result.ok).toBe(true);
    expect(result.data).toBeDefined();
    expect(result.data!.modality).toBe("mobile");
    expect(result.data!.deviceId).toBe("emulator-5554");
    expect(result.data!.id).toMatch(/^adb:emulator-5554:/);
  });

  it("AdbTransport.open_session rejects missing deviceId", async () => {
    const t = new AdbTransport("pixel");
    const result = await t.call("open_session", {});
    expect(result.ok).toBe(false);
    expect(result.error).toContain("deviceId is required");
  });
});
