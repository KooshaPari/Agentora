import type { AgentRuntime, RunRequest, RunResponse } from "../runtime";
export class CodexRuntime implements AgentRuntime {
  readonly name = "codex";
  readonly supportedModels = ["gpt-4o", "gpt-4o-mini", "o1"] as const;
  async exec(req: RunRequest): Promise<RunResponse> { return { text: `[codex:${req.model}] ${req.prompt}`, tokensUsed: 8, finishReason: "stop", modelId: req.model }; }
  async *stream(req: RunRequest): AsyncIterable<string> { yield (await this.exec(req)).text; }
  async cancel(_id: string): Promise<void> {}
}
