/**
 * T66.4 adapter: CodexCliAdapter.
 *
 * Delegates device operations to the `codex` CLI via child_process.
 * This is the 3rd DeviceStage adapter (alongside forge.ts and eidolon.ts),
 * completing the minimum-3-adapters requirement per the agent-platform spec.
 *
 * The Codex CLI is a local binary that manages device modalities (iOS simulator,
 * Android emulator, desktop X11/Wayland, Windows). We communicate by spawning
 * subprocesses with structured arguments and parsing JSON output.
 *
 * Telemetry: each method call is wrapped in an OTLP span via ports/telemetry.ts.
 * Gracefully degrades to no-op when @opentelemetry/api is not installed.
 */

import type {
  DeviceStage,
  DeviceId,
  SessionId,
  PointerInput,
  KeyInput,
  Viewport,
  ScreenshotResult,
  DeviceSession,
} from "../device_stage";
import { execFile } from "node:child_process";
import { getTracer } from "../telemetry";

// ---------------------------------------------------------------------------
// Transport abstractions
// ---------------------------------------------------------------------------

/**
 * Structured result from a Codex CLI operation.
 */
export interface CodexCliResult<T = unknown> {
  ok: boolean;
  data?: T;
  error?: string;
  exitCode?: number;
}

/**
 * Transport interface — allows swapping stdio / in-memory / mock.
 */
export interface CodexTransport {
  readonly name: string;
  call<T = unknown>(
    method: string,
    params?: Record<string, unknown>,
  ): Promise<CodexCliResult<T>>;
}

// ---------------------------------------------------------------------------
// Stdio transport — spawns `codex` CLI and parses JSON from stdout.
// ---------------------------------------------------------------------------

/**
 * Map of DeviceStage method names to `codex` CLI subcommand trees.
 *
 * The Codex CLI uses a `codex <noun> <verb> [args...] --json` convention.
 * This mapping converts the internal `snake_case` method name (eidolon/MCP
 * convention) to the CLI subcommand path.
 */
function methodToCliArgs(
  method: string,
  params?: Record<string, unknown>,
): string[] {
  const m = method.replace(/-/g, "_");

  if (m === "list_devices") return ["devices", "list", "--json"];
  if (m === "open_session")
    return ["session", "open", String(params?.deviceId ?? ""), "--json"];
  if (m === "close_session")
    return ["session", "close", String(params?.sessionId ?? ""), "--json"];

  if (m === "pointer") {
    const args = [
      "input",
      "pointer",
      "--kind",
      String(params?.kind ?? "tap"),
      "--x",
      String(params?.x ?? 0),
      "--y",
      String(params?.y ?? 0),
      "--json",
    ];
    if (params?.x2 !== undefined) args.push("--x2", String(params.x2));
    if (params?.y2 !== undefined) args.push("--y2", String(params.y2));
    if (params?.durationMs !== undefined)
      args.push("--duration", String(params.durationMs));
    return args;
  }

  if (m === "key") {
    const args = [
      "input",
      "key",
      "--kind",
      String(params?.kind ?? "type"),
      "--json",
    ];
    if (params?.text) args.push("--text", String(params.text));
    if (params?.key) args.push("--key", String(params.key));
    return args;
  }

  if (m === "screenshot") {
    const args = [
      "session",
      "capture",
      String(params?.sessionId ?? ""),
      "--json",
    ];
    if (params?.outputPath) args.push("--output", String(params.outputPath));
    return args;
  }

  if (m === "viewport")
    return ["session", "viewport", String(params?.sessionId ?? ""), "--json"];

  // Fallback: pass method name as a single subcommand
  return [m, "--json"];
}

export class CodexStdioTransport implements CodexTransport {
  readonly name: string;
  private readonly binaryPath: string;

  constructor(name: string, binaryPath = "codex") {
    this.name = `stdio:${name}`;
    this.binaryPath = binaryPath;
  }

  async call<T = unknown>(
    method: string,
    params?: Record<string, unknown>,
  ): Promise<CodexCliResult<T>> {
    const args = methodToCliArgs(method, params);

    return new Promise<CodexCliResult<T>>((resolve) => {
      const child = execFile(
        this.binaryPath,
        args,
        { timeout: 30_000, maxBuffer: 10 * 1024 * 1024 },
        (error, stdout, stderr) => {
          if (error) {
            // ENOENT means the binary doesn't exist at all
            if ((error as NodeJS.ErrnoException).code === "ENOENT") {
              resolve({
                ok: false,
                error: `Codex CLI binary not found: ${this.binaryPath}`,
                exitCode: -1,
              });
              return;
            }
            resolve({
              ok: false,
              error: error.message,
              exitCode: error.code ?? 1,
            });
            return;
          }

          // Some commands (close_session, key, pointer) return empty stdout
          if (!stdout || stdout.trim().length === 0) {
            resolve({ ok: true, data: undefined as unknown as T, exitCode: 0 });
            return;
          }

          try {
            const data = JSON.parse(stdout) as T;
            resolve({ ok: true, data, exitCode: 0 });
          } catch {
            // Non-JSON output — return raw string
            resolve({
              ok: true,
              data: stdout.trim() as unknown as T,
              exitCode: 0,
            });
          }
        },
      );

      // Write stdin if params contain a payload
      if (
        params?.stdinPayload !== undefined &&
        child.stdin
      ) {
        child.stdin.write(JSON.stringify(params.stdinPayload));
        child.stdin.end();
      }
    });
  }
}

// ---------------------------------------------------------------------------
// Null transport — safe fallback when no Codex CLI is configured.
// ---------------------------------------------------------------------------

export class NullCodexTransport implements CodexTransport {
  readonly name = "null";

  async call<T = unknown>(
    _method: string,
    _params?: Record<string, unknown>,
  ): Promise<CodexCliResult<T>> {
    return {
      ok: false,
      error: "Codex CLI not reachable: no transport configured",
      exitCode: -1,
    };
  }
}

// ---------------------------------------------------------------------------
// CodexCliAdapter config
// ---------------------------------------------------------------------------

export interface CodexCliAdapterConfig {
  readonly name: string;
  /** Path to the `codex` binary. Defaults to `"codex"` (PATH lookup). */
  readonly binaryPath?: string;
  /** Inject a custom transport (for testing). */
  readonly customTransport?: CodexTransport;
}

// ---------------------------------------------------------------------------
// CodexCliAdapter — DeviceStage implementation
// ---------------------------------------------------------------------------

export class CodexCliAdapter implements DeviceStage {
  readonly name: string;
  readonly modality: "mobile" | "desktop" | "sandbox" | "browser" | "vm" | "container" =
    "desktop";
  readonly supportedDeviceKinds: readonly string[] = [
    "macos",
    "linux-x11",
    "linux-wayland",
    "windows",
    "ios-simulator",
    "android-emulator",
    "vm",
  ];

  private readonly transport: CodexTransport;

  constructor(private readonly config: CodexCliAdapterConfig) {
    this.name = `codex:${config.name}`;
    this.transport =
      config.customTransport ??
      new CodexStdioTransport(config.name, config.binaryPath);
  }

  // -----------------------------------------------------------------------
  // Internal bridge — routes to transport, throws on failure.
  // -----------------------------------------------------------------------

  private async callTransport<T = unknown>(
    method: string,
    params?: Record<string, unknown>,
  ): Promise<T> {
    const result = await this.transport.call<T>(method, params);

    if (!result.ok) {
      throw new Error(
        `CodexCliAdapter.call("${method}") failed via ${this.transport.name}: ${result.error ?? "unknown error"}`,
      );
    }

    return result.data as T;
  }

  // -----------------------------------------------------------------------
  // DeviceStage methods
  // -----------------------------------------------------------------------

  async listDevices(): Promise<readonly DeviceId[]> {
    const span = getTracer().startSpan("device-stage.listDevices", {
      attributes: {
        "device.modality": this.modality,
        "device.transport": this.transport.name,
      },
    });
    try {
      return await this.callTransport<readonly DeviceId[]>("list_devices");
    } catch (error) {
      span.recordError(
        error instanceof Error ? error : new Error(String(error)),
      );
      throw error;
    } finally {
      span.end();
    }
  }

  async openSession(deviceId: DeviceId): Promise<DeviceSession> {
    const span = getTracer().startSpan("device-stage.openSession", {
      attributes: {
        "device.modality": this.modality,
        "device.transport": this.transport.name,
        "device.id": deviceId,
      },
    });
    try {
      const result = await this.callTransport<DeviceSession>("open_session", {
        deviceId,
      });
      return result;
    } catch (error) {
      span.recordError(
        error instanceof Error ? error : new Error(String(error)),
      );
      throw error;
    } finally {
      span.end();
    }
  }

  async closeSession(sessionId: SessionId): Promise<void> {
    const span = getTracer().startSpan("device-stage.closeSession", {
      attributes: {
        "device.modality": this.modality,
        "device.transport": this.transport.name,
        "session.id": sessionId,
      },
    });
    try {
      await this.callTransport<void>("close_session", { sessionId });
    } catch (error) {
      span.recordError(
        error instanceof Error ? error : new Error(String(error)),
      );
      throw error;
    } finally {
      span.end();
    }
  }

  async pointer(
    sessionId: SessionId,
    input: PointerInput,
  ): Promise<void> {
    const span = getTracer().startSpan("device-stage.pointer", {
      attributes: {
        "device.modality": this.modality,
        "device.transport": this.transport.name,
        "pointer.kind": input.kind,
        "pointer.x": input.x,
        "pointer.y": input.y,
      },
    });
    try {
      await this.callTransport<void>("pointer", { sessionId, ...input });
    } catch (error) {
      span.recordError(
        error instanceof Error ? error : new Error(String(error)),
      );
      throw error;
    } finally {
      span.end();
    }
  }

  async key(sessionId: SessionId, input: KeyInput): Promise<void> {
    const span = getTracer().startSpan("device-stage.key", {
      attributes: {
        "device.modality": this.modality,
        "device.transport": this.transport.name,
        "key.kind": input.kind,
      },
    });
    try {
      await this.callTransport<void>("key", { sessionId, ...input });
    } catch (error) {
      span.recordError(
        error instanceof Error ? error : new Error(String(error)),
      );
      throw error;
    } finally {
      span.end();
    }
  }

  async screenshot(
    sessionId: SessionId,
    outputPath: string,
  ): Promise<ScreenshotResult> {
    const span = getTracer().startSpan("device-stage.screenshot", {
      attributes: {
        "device.modality": this.modality,
        "device.transport": this.transport.name,
        "screenshot.path": outputPath,
      },
    });
    try {
      const result = await this.callTransport<ScreenshotResult>("screenshot", {
        sessionId,
        outputPath,
      });
      return result;
    } catch (error) {
      span.recordError(
        error instanceof Error ? error : new Error(String(error)),
      );
      throw error;
    } finally {
      span.end();
    }
  }

  async viewport(sessionId: SessionId): Promise<Viewport> {
    const span = getTracer().startSpan("device-stage.viewport", {
      attributes: {
        "device.modality": this.modality,
        "device.transport": this.transport.name,
      },
    });
    try {
      const result = await this.callTransport<Viewport>("viewport", { sessionId });
      return result;
    } catch (error) {
      span.recordError(
        error instanceof Error ? error : new Error(String(error)),
      );
      throw error;
    } finally {
      span.end();
    }
  }

  /**
   * Stage-port hook: route a domain-specific call through the transport.
   * Each call is traced with the transport name.
   */
  async call<T = unknown>(method: string, params?: unknown): Promise<T> {
    const result = await this.transport.call<T>(
      method,
      params as Record<string, unknown> | undefined,
    );

    if (!result.ok) {
      throw new Error(
        `CodexCliAdapter.call("${method}") failed via ${this.transport.name}: ${result.error ?? "unknown error"}`,
      );
    }

    return result.data as T;
  }
}
