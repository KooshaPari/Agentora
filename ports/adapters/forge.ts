import type { AgentRuntime, RunRequest, RunResponse } from "../runtime";
export class ForgeRuntime implements AgentRuntime {
  readonly name = "forge";
  readonly supportedModels = ["haiku", "sonnet", "opus"] as const;
  async exec(req: RunRequest): Promise<RunResponse> { return { text: `[forge:${req.model}] ${req.prompt}`, tokensUsed: 10, finishReason: "stop", modelId: req.model }; }
  async *stream(req: RunRequest): AsyncIterable<string> { yield (await this.exec(req)).text; }
  async cancel(_id: string): Promise<void> {}
}
