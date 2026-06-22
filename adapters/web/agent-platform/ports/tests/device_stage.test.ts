import { describe, it, expect } from "vitest";
import { EidolonStage, NullTransport, McpResult, type EidolonTransport } from "../adapters/eidolon";
import type { DeviceStage } from "../device_stage";

describe("agent-platform DeviceStage (T66)", () => {
  it("EidolonStage.name follows eidolon:<config> convention", () => {
    const s = new EidolonStage({
      name: "primary",
      transport: "stdio",
      endpoint: "/usr/local/bin/eidolon-mcp",
    });
    expect(s.name).toBe("eidolon:primary");
  });

  it("EidolonStage implements DeviceStage", () => {
    const s: DeviceStage = new EidolonStage({
      name: "x",
      transport: "stdio",
      endpoint: "/x",
    });
    expect(s.modality).toBe("mobile");
    expect(s.supportedDeviceKinds).toContain("ios-simulator");
    expect(s.supportedDeviceKinds).toContain("android-emulator");
    expect(s.supportedDeviceKinds).toContain("docker-container");
  });

  it("EidolonStage.call fails via NullTransport when no server configured", async () => {
    const s = new EidolonStage({
      name: "x",
      transport: "custom",
      customTransport: new NullTransport(),
    });
    await expect(s.call("list_devices")).rejects.toThrow(/Eidolon not reachable/);
  });

  it("EidolonStage with custom transport returns expected data", async () => {
    const devices = ["device-1", "device-2"];
    const mockTransport = new (class implements EidolonTransport {
      readonly name = "mock";
      async call<T = unknown>(
        _method: string,
        _params?: Record<string, unknown>,
      ): Promise<McpResult<T>> {
        return { ok: true, data: devices as unknown as T };
      }
    })();

    const s = new EidolonStage({
      name: "mock",
      transport: "custom",
      customTransport: mockTransport,
    });

    const result = await s.listDevices();
    expect(result).toEqual(devices);
  });

  it("EidolonStage is interface-compatible (satisfies DeviceStage)", () => {
    const s: DeviceStage = new EidolonStage({
      name: "x",
      transport: "stdio",
      endpoint: "/x",
    });
    expect(typeof s.listDevices).toBe("function");
    expect(typeof s.openSession).toBe("function");
    expect(typeof s.closeSession).toBe("function");
    expect(typeof s.pointer).toBe("function");
    expect(typeof s.key).toBe("function");
    expect(typeof s.screenshot).toBe("function");
    expect(typeof s.viewport).toBe("function");
  });
});
