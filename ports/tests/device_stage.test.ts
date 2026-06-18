import { describe, it, expect } from "vitest";
import { EidolonStage } from "../adapters/eidolon";
import type { DeviceStage } from "../device_stage";

describe("agent-platform DeviceStage (T66)", () => {
  it("EidolonStage.name follows eidolon:<config> convention", () => {
    const s = new EidolonStage({ name: "primary", transport: "stdio", endpoint: "/usr/local/bin/eidolon-mcp" });
    expect(s.name).toBe("eidolon:primary");
  });

  it("EidolonStage implements DeviceStage", () => {
    const s: DeviceStage = new EidolonStage({ name: "x", transport: "stdio", endpoint: "/x" });
    expect(s.modality).toBe("mobile");
    expect(s.supportedDeviceKinds).toContain("ios-simulator");
    expect(s.supportedDeviceKinds).toContain("android-emulator");
    expect(s.supportedDeviceKinds).toContain("docker-container");
  });

  it("EidolonStage.call throws until transport is wired (Phase 3 stub)", async () => {
    const s = new EidolonStage({ name: "x", transport: "stdio", endpoint: "/x" });
    await expect(s.call("s1" as any, "list_devices")).rejects.toThrow(/transport not yet wired/);
  });

  it("DeviceStage is interface-compatible (EidolonStage satisfies)", () => {
    const s: DeviceStage = new EidolonStage({ name: "x", transport: "stdio", endpoint: "/x" });
    expect(typeof s.listDevices).toBe("function");
    expect(typeof s.openSession).toBe("function");
    expect(typeof s.closeSession).toBe("function");
    expect(typeof s.pointer).toBe("function");
    expect(typeof s.key).toBe("function");
    expect(typeof s.screenshot).toBe("function");
    expect(typeof s.viewport).toBe("function");
  });
});