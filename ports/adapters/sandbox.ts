/**
 * T66.x adapter: SandboxAdapter.
 *
 * Manages ephemeral sandbox / container environments. Delegates to Eidolon's
 * SandboxStage via MCP when available (the canonical "heavy-lifting" path),
 * and provides a NullSandboxTransport fallback for environments where no
 * sandbox orchestration is configured.
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

export interface SandboxMcpResult<T = unknown> {
  ok: boolean;
  data?: T;
  error?: string;
}

export interface SandboxTransport {
  readonly name: string;
  call<T = unknown>(method: string, params?: Record<string, unknown>): Promise<SandboxMcpResult<T>>;
}

// ---------------------------------------------------------------------------
// Eidolon Sandbox transport — delegates to the Eidolon MCP server
// ---------------------------------------------------------------------------

/**
 * Delegates sandbox operations to Eidolon's SandboxStage via the MCP
 * protocol (HTTP/SSE). This is the primary "heavy-lifting" transport for
 * ephemeral sandbox environments — VM, Docker, Firecracker, gVisor.
 *
 * Endpoint convention: <eidolon-url>/sandbox/call
 */
export class EidolonSandboxTransport implements SandboxTransport {
  readonly name: string;
  private readonly endpoint: string;

  constructor(name: string, endpoint: string) {
    this.name = `eidolon-sandbox:${name}`;
    this.endpoint = endpoint.replace(/\/+$/, "");
  }

  async call<T = unknown>(
    method: string,
    params?: Record<string, unknown>,
  ): Promise<SandboxMcpResult<T>> {
    try {
      const response = await fetch(`${this.endpoint}/sandbox/call`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ method, params }),
      });

      if (!response.ok) {
        return {
          ok: false,
          error: `Eidolon Sandbox returned HTTP ${response.status}: ${response.statusText}`,
        };
      }

      const data = (await response.json()) as T;
      return { ok: true, data };
    } catch (err) {
      return {
        ok: false,
        error: err instanceof Error ? err.message : String(err),
      };
    }
  }
}

// ---------------------------------------------------------------------------
// Null transport — safe fallback when no sandbox tooling is configured.
// ---------------------------------------------------------------------------

export class NullSandboxTransport implements SandboxTransport {
  readonly name = "null-sandbox";

  async call<T = unknown>(
    _method: string,
    _params?: Record<string, unknown>,
  ): Promise<SandboxMcpResult<T>> {
    return { ok: false, error: "Sandbox tooling not available: no transport configured" };
  }
}

// ---------------------------------------------------------------------------
// SandboxStage config
// ---------------------------------------------------------------------------

export interface SandboxStageConfig {
  readonly name: string;
  readonly type: "eidolon-mcp" | "custom";
  readonly endpoint?: string; // Eidolon MCP server URL
  readonly customTransport?: SandboxTransport;
}

// ---------------------------------------------------------------------------
// SandboxStage adapter
// ---------------------------------------------------------------------------

export class SandboxStage implements DeviceStage {
  readonly name: string;
  readonly modality = "sandbox" as const;
  readonly supportedDeviceKinds: readonly string[] = [
    "docker-container",
    "firecracker-microvm",
    "gvisor-sandbox",
    "linux-vm",
  ];

  private readonly transport: SandboxTransport;

  constructor(private readonly config: SandboxStageConfig) {
    this.name = `sandbox:${config.name}`;
    this.transport = config.customTransport ?? this.initTransport(config);
  }

  private initTransport(config: SandboxStageConfig): SandboxTransport {
    switch (config.type) {
      case "eidolon-mcp":
        return new EidolonSandboxTransport(config.name, config.endpoint ?? "http://localhost:3100");
      default:
        return new NullSandboxTransport();
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

  async screenshot(sessionId: SessionId, outputPath: string): Promise<ScreenshotResult> {
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

  async call<T = unknown>(method: string, params?: unknown): Promise<T> {
    const mcpResult = await this.transport.call<T>(
      method,
      params as Record<string, unknown> | undefined,
    );

    if (!mcpResult.ok) {
      throw new Error(
        `SandboxStage.call("${method}") failed via ${this.transport.name}: ${mcpResult.error ?? "unknown error"}`,
      );
    }

    return mcpResult.data as T;
  }
}
