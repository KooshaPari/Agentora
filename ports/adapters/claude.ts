import type { AgentRuntime, ModelId, RunRequest, RunResponse } from "../runtime";
export class ClaudeRuntime implements AgentRuntime {
  readonly name = "claude";
  readonly supportedModels = ["haiku", "sonnet", "opus"] as unknown as readonly ModelId[];
  async exec(req: RunRequest): Promise<RunResponse> { return { text: `[claude:${req.model}] ${req.prompt}`, tokensUsed: 10, finishReason: "stop", modelId: req.model }; }
  async *stream(req: RunRequest): AsyncIterable<string> { yield (await this.exec(req)).text; }
  async cancel(_id: string): Promise<void> {}
}
