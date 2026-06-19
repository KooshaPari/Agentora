import { describe, it, expect } from "vitest";
import { ClaudeRuntime } from "../adapters/claude";
describe("ClaudeRuntime", () => {
  it("ClaudeRuntime.name", () => { expect(new ClaudeRuntime().name).toBe("claude"); });
  it("ClaudeRuntime.exec returns response", async () => {
    const r = await new ClaudeRuntime().exec({ agent: "a" as any, model: "haiku" as any, prompt: "hi" });
    expect(r.finishReason).toBe("stop");
  });
  it("AgentRuntime is interface-compatible", async () => {
    const r: import("../runtime").AgentRuntime = new ClaudeRuntime();
    expect(r.supportedModels).toContain("haiku");
  });
});
