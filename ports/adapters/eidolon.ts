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

/**
 * T66 adapter: EidolonStage.
 *
 * Delegates to KooshaPari/Eidolon via MCP stdio transport (recommended) or
 * HTTP/SSE. The agent runtime never sees the transport — only the trait
 * surface. This is the canonical adapter per findings/2026-06-17-eidolon-absorption.md.
 *
 * Eidolon's VirtualStage is the unified abstraction for mobile, desktop,
 * and sandbox; we expose it as a single DeviceStage whose `modality` is
 * resolved at session-open time.
 */
export interface EidolonStageConfig {
  readonly name: string;
  readonly transport: "stdio" | "http";
  readonly endpoint: string; // path to eidolon-mcp binary or http URL
  readonly defaultModality?: "mobile" | "desktop" | "sandbox";
}

export class EidolonStage implements DeviceStage {
  readonly name: string;
  readonly modality: "mobile" | "desktop" | "sandbox" = "mobile"; // default; resolved per session
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

  constructor(private readonly config: EidolonStageConfig) {
    this.name = `eidolon:${config.name}`;
  }

  async listDevices(): Promise<readonly DeviceId[]> {
    return this.call<readonly DeviceId[]>("list_devices");
  }

  async openSession(deviceId: DeviceId): Promise<DeviceSession> {
    return this.call<DeviceSession>("open_session", { deviceId });
  }

  async closeSession(sessionId: SessionId): Promise<void> {
    await this.call<void>("close_session", { sessionId });
  }

  async pointer(sessionId: SessionId, input: PointerInput): Promise<void> {
    await this.call<void>("pointer", { sessionId, ...input });
  }

  async key(sessionId: SessionId, input: KeyInput): Promise<void> {
    await this.call<void>("key", { sessionId, ...input });
  }

  async screenshot(sessionId: SessionId, outputPath: string): Promise<ScreenshotResult> {
    return this.call<ScreenshotResult>("screenshot", { sessionId, outputPath });
  }

  async viewport(sessionId: SessionId): Promise<Viewport> {
    return this.call<Viewport>("viewport", { sessionId });
  }

  async call<T = unknown>(sessionId: SessionId, method: string, params?: unknown): Promise<T> {
    // Routing is delegated to the Eidolon MCP transport; the adapter is
    // intentionally thin so that test doubles can stand in without dragging
    // in the Eidolon runtime.
    void sessionId;
    void method;
    void params;
    throw new Error("EidolonStage.call: transport not yet wired (Phase 3 stub).");
  }
}