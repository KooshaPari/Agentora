/**
 * T16.4 adapter: EidolonStage.
 *
 * Delegates to KooshaPari/Eidolon via MCP stdio transport (recommended) or
 * HTTP/SSE. The agent runtime never sees the transport — only the trait
 * surface. This is the canonical adapter per findings/2026-06-17-eidolon-absorption.md.
 *
 * Eidolon's VirtualStage is the unified abstraction for mobile, desktop,
 * and sandbox; we expose it as a single DeviceStage whose `modality` is
 * resolved at session-open time.
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
import { getTracer } from "../telemetry";

// ---------------------------------------------------------------------------
// Transport abstractions
// ---------------------------------------------------------------------------

/**
 * Transport-agnostic result from an Eidolon MCP operation.
 */
export interface McpResult<T = unknown> {
  ok: boolean;
  data?: T;
  error?: string;
}

/**
 * Transport interface — allows swapping stdio / HTTP / in-memory.
 */
export interface EidolonTransport {
  readonly name: string;
  call<T = unknown>(method: string, params?: Record<string, unknown>): Promise<McpResult<T>>;
}

// ---------------------------------------------------------------------------
// EidolonStage config
// ---------------------------------------------------------------------------
export interface EidolonStageConfig {
  readonly name: string;
  readonly transport: "stdio" | "http" | "custom";
  readonly endpoint?: string; // path to eidolon-mcp binary or http URL
  readonly customTransport?: EidolonTransport;
  readonly defaultModality?: "mobile" | "desktop" | "sandbox";
}

// ---------------------------------------------------------------------------
// MCP stdio transport — spawns an Eidolon MCP server and communicates
// via JSON-RPC over stdin/stdout.
// ---------------------------------------------------------------------------

export class McpStdioTransport implements EidolonTransport {
  readonly name: string;
  private readonly binaryPath: string;

  constructor(name: string, binaryPath: string) {
    this.name = `stdio:${name}`;
    this.binaryPath = binaryPath;
  }

  async call<T = unknown>(
    method: string,
    params?: Record<string, unknown>,
  ): Promise<McpResult<T>> {
    // Placeholder: real implementation would spawn child_process and
    // communicate via JSON-RPC. For now use a fetch-based mock that
    // can be replaced when the actual Eidolon MCP server contract is stable.
    //
    // Real impl would look like:
    //   const child = spawn(this.binaryPath, [], { stdio: ["pipe", "pipe", "inherit"] });
    //   child.stdin.write(JSON.stringify({ jsonrpc: "2.0", id: 1, method: "tools/call", params: { name: method, arguments: params } }) + "\n");
    //   const response = JSON.parse(await once(child.stdout, "data"));
    //   child.kill();
    //   return { ok: true, data: response.result };
    //
    // For now, make an HTTP request to a local Eidolon MCP server.
    try {
      const response = await fetch(`${this.binaryPath}/call`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ method, params }),
      });
      if (!response.ok) {
        return { ok: false, error: `Eidolon MCP server returned ${response.status}` };
      }
      const data = (await response.json()) as T;
      return { ok: true, data };
    } catch (error) {
      return {
        ok: false,
        error: error instanceof Error ? error.message : String(error),
      };
    }
  }
}

// ---------------------------------------------------------------------------
// HTTP transport — connects to a running Eidolon MCP server via HTTP.
// ---------------------------------------------------------------------------

export class McpHttpTransport implements EidolonTransport {
  readonly name: string;
  private readonly baseUrl: string;

  constructor(name: string, baseUrl: string) {
    this.name = `http:${name}`;
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  async call<T = unknown>(
    method: string,
    params?: Record<string, unknown>,
  ): Promise<McpResult<T>> {
    try {
      const response = await fetch(`${this.baseUrl}/call`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ method, params }),
      });
      if (!response.ok) {
        return { ok: false, error: `HTTP ${response.status}: ${response.statusText}` };
      }
      const data = (await response.json()) as T;
      return { ok: true, data };
    } catch (error) {
      return {
        ok: false,
        error: error instanceof Error ? error.message : String(error),
      };
    }
  }
}

// ---------------------------------------------------------------------------
// Null transport — safe fallback when no Eidolon server is configured.
// Every call returns { ok: false, error: "Eidolon not reachable" }.
// ---------------------------------------------------------------------------

export class NullTransport implements EidolonTransport {
  readonly name = "null";

  async call<T = unknown>(
    _method: string,
    _params?: Record<string, unknown>,
  ): Promise<McpResult<T>> {
    return { ok: false, error: "Eidolon not reachable: no transport configured" };
  }
}

// ---------------------------------------------------------------------------
// EidolonStage adapter
// ---------------------------------------------------------------------------

export class EidolonStage implements DeviceStage {
  readonly name: string;
  readonly modality: "mobile" | "desktop" | "sandbox" = "mobile";
  readonly supportedDeviceKinds: readonly string[] = [
    "ios-simulator",
    "ios-real",
    "android-emulator",
    "android-real",
    "macos",
    "linux-x11",
    "linux-vm",
    "docker-container",
  ];

  private readonly transport: EidolonTransport;

  constructor(private readonly config: EidolonStageConfig) {
    this.name = `eidolon:${config.name}`;
    this.modality = config.defaultModality ?? "mobile";
    this.transport = this.initTransport(config);
  }

  private initTransport(config: EidolonStageConfig): EidolonTransport {
    if (config.customTransport) return config.customTransport;

    switch (config.transport) {
      case "stdio":
        return new McpStdioTransport(config.name, config.endpoint ?? "eidolon-mcp");
      case "http":
        return new McpHttpTransport(config.name, config.endpoint ?? "http://localhost:3100");
      default:
        return new NullTransport();
    }
  }

  async listDevices(): Promise<readonly DeviceId[]> {
    const span = getTracer().startSpan("device-stage.listDevices", {
      attributes: { "device.modality": this.modality, "device.transport": this.transport.name },
    });
    try {
      const result = await this.call<readonly DeviceId[]>("list_devices");
      return result;
    } catch (error) {
      span.recordError(error instanceof Error ? error : new Error(String(error)));
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
      const result = await this.call<DeviceSession>("open_session", { deviceId });
      return result;
    } catch (error) {
      span.recordError(error instanceof Error ? error : new Error(String(error)));
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
      await this.call<void>("close_session", { sessionId });
    } catch (error) {
      span.recordError(error instanceof Error ? error : new Error(String(error)));
      throw error;
    } finally {
      span.end();
    }
  }

  async pointer(sessionId: SessionId, input: PointerInput): Promise<void> {
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
      await this.call<void>("pointer", { sessionId, ...input });
    } catch (error) {
      span.recordError(error instanceof Error ? error : new Error(String(error)));
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
      await this.call<void>("key", { sessionId, ...input });
    } catch (error) {
      span.recordError(error instanceof Error ? error : new Error(String(error)));
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
      const result = await this.call<ScreenshotResult>("screenshot", {
        sessionId,
        outputPath,
      });
      return result;
    } catch (error) {
      span.recordError(error instanceof Error ? error : new Error(String(error)));
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
      const result = await this.call<Viewport>("viewport", { sessionId });
      return result;
    } catch (error) {
      span.recordError(error instanceof Error ? error : new Error(String(error)));
      throw error;
    } finally {
      span.end();
    }
  }

  /**
   * Route a method+params tuple through the configured transport.
   * Each call is traced with the transport name.
   */
  async call<T = unknown>(method: string, params?: unknown): Promise<T> {
    const mcpResult = await this.transport.call<T>(
      method,
      params as Record<string, unknown> | undefined,
    );

    if (!mcpResult.ok) {
      throw new Error(
        `EidolonStage.call("${method}") failed via ${this.transport.name}: ${mcpResult.error ?? "unknown error"}`,
      );
    }

    return mcpResult.data as T;
  }
}
