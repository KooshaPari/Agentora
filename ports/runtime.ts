/**
 * T65: agent-platform hexagonal port — Runtime.
 *
 * 3 adapters: ForgeRuntime, CodexRuntime, ClaudeRuntime.
 * Domain code depends on this trait, not on forge/codex/claude directly.
 */
export type AgentId = string & { readonly __brand: "AgentId" };
export type ModelId = string & { readonly __brand: "ModelId" };
export type TokenStream = AsyncIterable<string>;
export interface RunRequest {
  readonly agent: AgentId;
  readonly model: ModelId;
  readonly prompt: string;
  readonly tools?: readonly string[];
  readonly maxTokens?: number;
}
export interface RunResponse { readonly text: string; readonly tokensUsed: number; readonly finishReason: "stop" | "length" | "error"; readonly modelId: ModelId; }
export interface AgentRuntime {
  readonly name: string;
  readonly supportedModels: readonly ModelId[];
  exec(req: RunRequest): Promise<RunResponse>;
  stream(req: RunRequest): TokenStream;
  cancel(id: string): Promise<void>;
}
