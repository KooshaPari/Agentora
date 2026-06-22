/**
 * T66.x adapter: BrowserAdapter.
 *
 * Manages web browser automation — delegates to Playwright / Puppeteer via
 * a local or remote MCP server when available, and provides a null-returning
 * fallback (NullBrowserTransport) for environments without browser automation
 * tooling.
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

export interface BrowserMcpResult<T = unknown> {
  ok: boolean;
  data?: T;
  error?: string;
}

export interface BrowserTransport {
  readonly name: string;
  call<T = unknown>(method: string, params?: Record<string, unknown>): Promise<BrowserMcpResult<T>>;
}

// ---------------------------------------------------------------------------
// Playwright MCP transport — delegates to a Playwright MCP server
// ---------------------------------------------------------------------------

/**
 * Browser automation via Playwright MCP server. The MCP server exposes
 * Playwright's Page and BrowserContext APIs as named tools / resources.
 *
 * Endpoint convention: <playwright-mcp-url>/call
 */
export class PlaywrightMcpTransport implements BrowserTransport {
  readonly name: string;
  private readonly endpoint: string;

  constructor(name: string, endpoint: string) {
    this.name = `playwright:${name}`;
    this.endpoint = endpoint.replace(/\/+$/, "");
  }

  async call<T = unknown>(
    method: string,
    params?: Record<string, unknown>,
  ): Promise<BrowserMcpResult<T>> {
    try {
      const response = await fetch(`${this.endpoint}/call`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ method, params }),
      });

      if (!response.ok) {
        return {
          ok: false,
          error: `Playwright MCP returned HTTP ${response.status}: ${response.statusText}`,
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
// Puppeteer MCP transport — delegates to a Puppeteer MCP server
// ---------------------------------------------------------------------------

/**
 * Browser automation via Puppeteer MCP server. Same interface as the
 * Playwright transport; the MCP server maps Puppeteer's Browser / Page
 * into the same tool surface.
 *
 * Endpoint convention: <puppeteer-mcp-url>/call
 */
export class PuppeteerMcpTransport implements BrowserTransport {
  readonly name: string;
  private readonly endpoint: string;

  constructor(name: string, endpoint: string) {
    this.name = `puppeteer:${name}`;
    this.endpoint = endpoint.replace(/\/+$/, "");
  }

  async call<T = unknown>(
    method: string,
    params?: Record<string, unknown>,
  ): Promise<BrowserMcpResult<T>> {
    try {
      const response = await fetch(`${this.endpoint}/call`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ method, params }),
      });

      if (!response.ok) {
        return {
          ok: false,
          error: `Puppeteer MCP returned HTTP ${response.status}: ${response.statusText}`,
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
// Null transport — safe fallback when no browser tooling is configured.
// ---------------------------------------------------------------------------

export class NullBrowserTransport implements BrowserTransport {
  readonly name = "null-browser";

  async call<T = unknown>(
    _method: string,
    _params?: Record<string, unknown>,
  ): Promise<BrowserMcpResult<T>> {
    return { ok: false, error: "Browser tooling not available: no transport configured" };
  }
}

// ---------------------------------------------------------------------------
// BrowserStage config
// ---------------------------------------------------------------------------

export interface BrowserStageConfig {
  readonly name: string;
  readonly type: "playwright-mcp" | "puppeteer-mcp" | "custom";
  readonly endpoint?: string; // MCP server URL
  readonly customTransport?: BrowserTransport;
}

// ---------------------------------------------------------------------------
// BrowserStage adapter
// ---------------------------------------------------------------------------

export class BrowserStage implements DeviceStage {
  readonly name: string;
  readonly modality = "browser" as const;
  readonly supportedDeviceKinds: readonly string[] = [
    "chromium",
    "firefox",
    "webkit",
    "chrome-headless",
  ];

  private readonly transport: BrowserTransport;

  constructor(private readonly config: BrowserStageConfig) {
    this.name = `browser:${config.name}`;
    this.transport = config.customTransport ?? this.initTransport(config);
  }

  private initTransport(config: BrowserStageConfig): BrowserTransport {
    switch (config.type) {
      case "playwright-mcp":
        return new PlaywrightMcpTransport(config.name, config.endpoint ?? "http://localhost:3500");
      case "puppeteer-mcp":
        return new PuppeteerMcpTransport(config.name, config.endpoint ?? "http://localhost:3600");
      default:
        return new NullBrowserTransport();
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
        `BrowserStage.call("${method}") failed via ${this.transport.name}: ${mcpResult.error ?? "unknown error"}`,
      );
    }

    return mcpResult.data as T;
  }
}
