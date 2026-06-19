import { describe, it, expect } from "vitest";
import {
  DesktopStageAdapter,
  nullDesktopStage,
  type DesktopStageConfig,
} from "../adapters/desktop";
import { NullTransport } from "../adapters/eidolon";
import type { EidolonTransport, McpResult } from "../adapters/eidolon";
import type {
  DesktopStage,
  CaptureSession,
  DisplayInfo,
  DisplayId,
  MouseButton,
} from "../desktop_stage";
import type {
  DeviceStage,
  DeviceId,
  SessionId,
  PointerInput,
} from "../device_stage";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Build an EidolonTransport that returns the given data keyed by MCP method
 * name. Any method not in the map returns { ok: false, error: "not impl" }.
 * Mirrors the mock pattern from eidolon_stage.test.ts so the desktop
 * adapter can be driven identically.
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

/**
 * Recording transport — captures every call so the test can assert on
 * what methods were issued and with what params (no return value).
 */
function createRecordingTransport(): {
  transport: EidolonTransport;
  calls: Array<{ method: string; params?: Record<string, unknown> }>;
} {
  const calls: Array<{ method: string; params?: Record<string, unknown> }> = [];
  const transport: EidolonTransport = {
    name: "recording",
    async call<T = unknown>(
      method: string,
      params?: Record<string, unknown>,
    ): Promise<McpResult<T>> {
      calls.push({ method, params });
      return { ok: true, data: undefined as T };
    },
  };
  return { transport, calls };
}

const SID = "session-1" as SessionId;
const DID = "device-1" as DeviceId;

const mockCapture: CaptureSession = {
  id: "cap-1",
  sessionId: SID,
  startedAt: "2026-06-18T00:00:00.000Z",
  outputPath: "/tmp/capture.mp4",
  format: "mp4",
};

const mockDisplay: DisplayInfo = {
  id: "display-0" as DisplayId,
  width: 2560,
  height: 1440,
  scale: 2,
  originX: 0,
  originY: 0,
  isPrimary: true,
};

function adapterWith(transport: EidolonTransport): DesktopStageAdapter {
  return new DesktopStageAdapter({
    name: "test-desktop",
    transport: "custom",
    customTransport: transport,
    fallbackToNull: false,
  });
}

// ---------------------------------------------------------------------------
// Suite 1 — name + modality + structural compatibility
// ---------------------------------------------------------------------------

describe("DesktopStageAdapter (T66) — name + modality + structural contract", () => {
  it("follows desktop-eidolon:<config> naming convention", () => {
    const a = new DesktopStageAdapter({
      name: "primary",
      transport: "stdio",
      endpoint: "/usr/local/bin/eidolon-mcp",
    });
    expect(a.name).toBe("desktop-eidolon:primary");
  });

  it("locks modality to desktop and lists desktop device kinds", () => {
    const a = new DesktopStageAdapter({
      name: "x",
      transport: "stdio",
      endpoint: "/x",
    });
    expect(a.modality).toBe("desktop");
    expect(a.supportedDeviceKinds).toContain("macos");
    expect(a.supportedDeviceKinds).toContain("linux-x11");
    expect(a.supportedDeviceKinds).toContain("windows");
  });

  it("satisfies DesktopStage structurally (sub-trait of DeviceStage)", () => {
    const a: DesktopStage = adapterWith(createMockTransport({}));
    const ds: DeviceStage = a;
    expect(typeof a.click).toBe("function");
    expect(typeof a.doubleClick).toBe("function");
    expect(typeof a.rightClick).toBe("function");
    expect(typeof a.keyTap).toBe("function");
    expect(typeof a.keyCombo).toBe("function");
    expect(typeof a.startCaptures).toBe("function");
    expect(typeof a.getActiveDisplay).toBe("function");
    // desktop-stage inherits the device-stage baseline
    expect(typeof ds.pointer).toBe("function");
    expect(typeof ds.screenshot).toBe("function");
    expect(typeof ds.viewport).toBe("function");
    expect(typeof ds.listDevices).toBe("function");
    expect(typeof ds.openSession).toBe("function");
    expect(typeof ds.closeSession).toBe("function");
  });
});

// ---------------------------------------------------------------------------
// Suite 2 — desktop semantics delegate through EidolonStage / Eidolon transport
// ---------------------------------------------------------------------------

describe("DesktopStageAdapter — desktop semantics delegate to Eidolon transport", () => {
  it("click() issues a single pointer via the Eidolon transport (left button by default)", async () => {
    const { transport, calls } = createRecordingTransport();
    const a = adapterWith(transport);
    await a.click(SID, 100, 250);

    expect(calls).toHaveLength(1);
    expect(calls[0].method).toBe("pointer");
    expect(calls[0].params?.kind).toBe("click");
    expect(calls[0].params?.x).toBe(100);
    expect(calls[0].params?.y).toBe(250);
    expect(calls[0].params?.button).toBe("left");
  });

  it("rightClick() forwards the right button semantic", async () => {
    const { transport, calls } = createRecordingTransport();
    const a = adapterWith(transport);
    await a.rightClick(SID, 50, 75);

    expect(calls).toHaveLength(1);
    expect(calls[0].method).toBe("pointer");
    expect(calls[0].params?.kind).toBe("click");
    expect(calls[0].params?.button).toBe("right");
  });

  it("doubleClick() issues two clicks back-to-back", async () => {
    const { transport, calls } = createRecordingTransport();
    const a = adapterWith(transport);
    await a.doubleClick(SID, 10, 20);

    expect(calls).toHaveLength(2);
    expect(calls[0].method).toBe("pointer");
    expect(calls[1].method).toBe("pointer");
    expect(calls[0].params?.button).toBe("left");
    expect(calls[1].params?.button).toBe("left");
  });

  it("keyTap() routes a single key press with no modifiers via the Eidolon key primitive", async () => {
    const { transport, calls } = createRecordingTransport();
    const a = adapterWith(transport);
    await a.keyTap(SID, "Enter");

    expect(calls).toHaveLength(1);
    expect(calls[0].method).toBe("key");
    expect(calls[0].params?.kind).toBe("press");
    expect(calls[0].params?.key).toBe("Enter");
    // No modifiers — single-tap semantics
    expect(calls[0].params?.modifiers).toBeUndefined();
  });

  it("keyCombo() carries the modifiers array plus the terminal key", async () => {
    const { transport, calls } = createRecordingTransport();
    const a = adapterWith(transport);
    await a.keyCombo(SID, ["cmd", "shift"], "p");

    expect(calls).toHaveLength(1);
    expect(calls[0].method).toBe("key");
    expect(calls[0].params?.kind).toBe("press");
    expect(calls[0].params?.key).toBe("p");
    expect(calls[0].params?.modifiers).toEqual(["cmd", "shift"]);
  });
});

// ---------------------------------------------------------------------------
// Suite 3 — desktop escape hatches (start_captures / get_active_display)
// ---------------------------------------------------------------------------

describe("DesktopStageAdapter — desktop escape hatches", () => {
  it("startCaptures() returns the CaptureSession handle from the backend", async () => {
    // The mock returns mockCapture unconditionally regardless of args —
    // assert against the canonical mock shape (id / format / outputPath).
    const t = createMockTransport({ start_captures: mockCapture });
    const a = adapterWith(t);

    const cap = await a.startCaptures(SID, "/tmp/capture.mp4");
    expect(cap).toEqual(mockCapture);
    expect(cap.id).toBe("cap-1");
    expect(cap.format).toBe("mp4");
    expect(cap.outputPath).toBe("/tmp/capture.mp4");
  });

  it("getActiveDisplay() returns primary DisplayInfo from the backend", async () => {
    const t = createMockTransport({ get_active_display: mockDisplay });
    const a = adapterWith(t);

    const display = await a.getActiveDisplay(SID);
    expect(display).toEqual(mockDisplay);
    expect(display.isPrimary).toBe(true);
    expect(display.width).toBe(2560);
  });
});

// ---------------------------------------------------------------------------
// Suite 4 — failure modes (NullTransport and missing methods)
// ---------------------------------------------------------------------------

describe("DesktopStageAdapter — failure modes", () => {
  it("all desktop ops fail via NullTransport when no Eidolon server is reachable", async () => {
    const a = adapterWith(new NullTransport());

    await expect(a.click(SID, 0, 0)).rejects.toThrow(/Eidolon not reachable/);
    await expect(a.doubleClick(SID, 0, 0)).rejects.toThrow(/Eidolon not reachable/);
    await expect(a.rightClick(SID, 0, 0)).rejects.toThrow(/Eidolon not reachable/);
    await expect(a.keyTap(SID, "a")).rejects.toThrow(/Eidolon not reachable/);
    await expect(a.keyCombo(SID, ["ctrl"], "c")).rejects.toThrow(/Eidolon not reachable/);
    await expect(a.startCaptures(SID, "/tmp/out.mp4")).rejects.toThrow(
      /Eidolon not reachable/,
    );
    await expect(a.getActiveDisplay(SID)).rejects.toThrow(/Eidolon not reachable/);
  });

  it("click rejects when the mock transport does not implement the pointer method", async () => {
    const t = createMockTransport({}); // no methods registered
    const a = adapterWith(t);

    // The call goes pointer(sessionId, ...) -> EidolonStage.call("pointer", ...)
    // -> transport.call("pointer", ...) which returns { ok: false }. The
    // adapter throws inside EidolonStage.call.
    await expect(a.click(SID, 1, 1)).rejects.toThrow();
  });
});

// ---------------------------------------------------------------------------
// Suite 5 — default factory (nullDesktopStage) + brand ergonomics
// ---------------------------------------------------------------------------

describe("DesktopStageAdapter — null factory + brand ergonomics", () => {
  it("nullDesktopStage() returns a reachable DesktopStage instance with default name", () => {
    const a = nullDesktopStage();
    expect(a.name).toBe("desktop-eidolon:null");
    expect(a.modality).toBe("desktop");
    expect(a).toBeDefined();
  });

  it("null factory accepts a custom name argument", () => {
    const a = nullDesktopStage("offline-desktop");
    expect(a.name).toBe("desktop-eidolon:offline-desktop");
  });

  it("MouseButton literal types enumerate left/right/middle", () => {
    const buttons: MouseButton[] = ["left", "right", "middle"];
    expect(buttons).toHaveLength(3);
    expect(buttons).toContain("left");
    expect(buttons).toContain("right");
    expect(buttons).toContain("middle");
  });

  it("PointerInput (desktop baseline) remains type-compatible with the adapter path", () => {
    const input: PointerInput = { kind: "click", x: 0, y: 0 };
    expect(input.kind).toBe("click");
    expect(input.x).toBe(0);
  });

  it("DesktopStageConfig accepts all 3 transport modes", () => {
    // Compile-time-only check; ensures the config surface is honest.
    const configs: DesktopStageConfig[] = [
      { name: "stdio-stage", transport: "stdio", endpoint: "/bin/eidolon-mcp" },
      { name: "http-stage", transport: "http", endpoint: "http://localhost:3100" },
      {
        name: "custom-stage",
        transport: "custom",
        customTransport: new NullTransport(),
      },
    ];
    expect(configs).toHaveLength(3);
  });
});
