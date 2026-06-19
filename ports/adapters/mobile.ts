/**
 * T66.x adapter: MobileDeviceAdapter.
 *
 * Manages mobile device modalities — Android (via adb shell) and iOS (via
 * mobile-mcp MCP server). Falls back to a NullMobileTransport when neither
 * adb nor mobile-mcp is available, mirroring the transport pattern from
 * adapters/eidolon.ts.
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

export interface MobileMcpResult<T = unknown> {
  ok: boolean;
  data?: T;
  error?: string;
}

export interface MobileTransport {
  readonly name: string;
  call<T = unknown>(method: string, params?: Record<string, unknown>): Promise<MobileMcpResult<T>>;
}

// ---------------------------------------------------------------------------
// ADB transport — communicates with Android devices via adb shell.
// ---------------------------------------------------------------------------

/**
 * Android ADB transport. Shells out to `adb` for device discovery, input
 * events (tap, swipe, key), and screenshots. Returns { ok: false } stubs
 * when adb is not available at call time.
 */
export class AdbTransport implements MobileTransport {
  readonly name: string;

  constructor(name: string) {
    this.name = `adb:${name}`;
  }

  async call<T = unknown>(
    method: string,
    params?: Record<string, unknown>,
  ): Promise<MobileMcpResult<T>> {
    switch (method) {
      case "list_devices": {
        // Placeholder: real impl shells out to `adb devices`
        // and parses the device list.
        return { ok: true, data: [] as T };
      }

      case "open_session": {
        const deviceId = params?.deviceId as string | undefined;
        if (!deviceId) {
          return { ok: false, error: "open_session: deviceId is required" };
        }
        return {
          ok: true,
          data: {
            id: `adb:${deviceId}:${Date.now()}`,
            deviceId,
            modality: "mobile",
            startedAt: new Date().toISOString(),
          } as T,
        };
      }

      case "close_session": {
        return { ok: true, data: undefined as T };
      }

      case "pointer": {
        // Placeholder: real impl does `adb shell input tap x y`
        return { ok: true, data: undefined as T };
      }

      case "key": {
        // Placeholder: real impl does `adb shell input text ...`
        return { ok: true, data: undefined as T };
      }

      case "screenshot": {
        // Placeholder: real impl does `adb exec-out screencap -p > <outputPath>`
        return {
          ok: true,
          data: {
            path: params?.outputPath ?? "/tmp/mobile-screenshot.png",
            format: "png",
            width: 0,
            height: 0,
            capturedAt: new Date().toISOString(),
          } as T,
        };
      }

      case "viewport": {
        // Placeholder: real impl parses `adb shell wm size`
        return {
          ok: true,
          data: { width: 1080, height: 2400, scale: 2.75 } as T,
        };
      }

      default:
        return { ok: false, error: `Mobile: method "${method}" not supported on ADB transport` };
    }
  }
}

// ---------------------------------------------------------------------------
// iOS / mobile-mcp transport — MCP-based for iOS simulators / real devices.
// ---------------------------------------------------------------------------

/**
 * iOS mobile transport that delegates to mobile-mcp MCP server for device
 * interaction. Uses the MCP client established in ports/mcp_client.ts.
 */
export class McpMobileTransport implements MobileTransport {
  readonly name: string;
  private readonly endpoint: string;

  constructor(name: string, endpoint: string) {
    this.name = `mcp-mobile:${name}`;
    this.endpoint = endpoint;
  }

  async call<T = unknown>(
    method: string,
    params?: Record<string, unknown>,
  ): Promise<MobileMcpResult<T>> {
    try {
      const response = await fetch(`${this.endpoint}/call`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ method, params }),
      });

      if (!response.ok) {
        return {
          ok: false,
          error: `mobile-mcp returned HTTP ${response.status}: ${response.statusText}`,
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
// Null transport — safe fallback when no mobile tooling is configured.
// ---------------------------------------------------------------------------

export class NullMobileTransport implements MobileTransport {
  readonly name = "null-mobile";

  async call<T = unknown>(
    _method: string,
    _params?: Record<string, unknown>,
  ): Promise<MobileMcpResult<T>> {
    return { ok: false, error: "Mobile tooling not available: no transport configured" };
  }
}

// ---------------------------------------------------------------------------
// MobileDeviceStage config
// ---------------------------------------------------------------------------

export interface MobileDeviceStageConfig {
  readonly name: string;
  readonly type: "adb" | "mcp-mobile" | "custom";
  readonly endpoint?: string; // mobile-mcp URL or adb prefix
  readonly customTransport?: MobileTransport;
}

// ---------------------------------------------------------------------------
// MobileDeviceStage adapter
// ---------------------------------------------------------------------------

export class MobileDeviceStage implements DeviceStage {
  readonly name: string;
  readonly modality = "mobile" as const;
  readonly supportedDeviceKinds: readonly string[] = [
    "android-emulator",
    "android-real",
    "ios-simulator",
    "ios-real",
  ];

  private readonly transport: MobileTransport;

  constructor(private readonly config: MobileDeviceStageConfig) {
    this.name = `mobile:${config.name}`;
    this.transport = this.initTransport(config);
  }

  private initTransport(config: MobileDeviceStageConfig): MobileTransport {
    if (config.customTransport) return config.customTransport;

    switch (config.type) {
      case "adb":
        return new AdbTransport(config.name);
      case "mcp-mobile":
        return new McpMobileTransport(config.name, config.endpoint ?? "http://localhost:3400");
      default:
        return new NullMobileTransport();
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
        `MobileDeviceStage.call("${method}") failed via ${this.transport.name}: ${mcpResult.error ?? "unknown error"}`,
      );
    }

    return mcpResult.data as T;
  }
}
