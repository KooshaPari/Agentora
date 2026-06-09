import { describe, it, expect } from "vitest";
import { ForgeRuntime } from "../adapters/forge";
import { CodexRuntime } from "../adapters/codex";
describe("agent-platform ports", () => {
  it("ForgeRuntime.name", () => { expect(new ForgeRuntime().name).toBe("forge"); });
  it("CodexRuntime.name", () => { expect(new CodexRuntime().name).toBe("codex"); });
  it("ForgeRuntime.exec returns response", async () => {
    const r = await new ForgeRuntime().exec({ agent: "a" as any, model: "haiku" as any, prompt: "hi" });
    expect(r.finishReason).toBe("stop");
  });
  it("CodexRuntime.exec returns response", async () => {
    const r = await new CodexRuntime().exec({ agent: "a" as any, model: "gpt-4o" as any, prompt: "hi" });
    expect(r.tokensUsed).toBeGreaterThan(0);
  });
  it("AgentRuntime is interface-compatible", async () => {
    const r: import("../runtime").AgentRuntime = new ForgeRuntime();
    expect(r.supportedModels).toContain("haiku");
  });
});
