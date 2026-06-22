import { describe, it, expect } from "vitest";
import { ForgeRuntime } from "../adapters/forge";
describe("agent-platform ports", () => {
  it("ForgeRuntime.name", () => { expect(new ForgeRuntime().name).toBe("forge"); });
  it("ForgeRuntime.exec returns response", async () => {
    const r = await new ForgeRuntime().exec({ agent: "a" as any, model: "haiku" as any, prompt: "hi" });
    expect(r.finishReason).toBe("stop");
  });
  it("AgentRuntime is interface-compatible", async () => {
    const r: import("../runtime").AgentRuntime = new ForgeRuntime();
    expect(r.supportedModels).toContain("haiku");
  });
});
