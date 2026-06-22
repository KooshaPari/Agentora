/**
 * T66: agent-platform hexagonal port — DeviceStage.
 *
 * Mirrors Eidolon's VirtualStage trait family (MobileStage, DesktopStage,
 * SandboxStage, BrowserStage). Domain code depends on this trait, not on
 * Eidolon / mobile-mcp / mobile-cli / PlayCua directly.
 *
 * Per ADR-023 (app-effort governance), the agent-platform interface domain
 * is the single coordination point between the agent runtime and any
 * device modality. Implementations are swappable via the Adapter pattern.
 */

export type DeviceId = string & { readonly __brand: "DeviceId" };
export type SessionId = string & { readonly __brand: "SessionId" };
export type StageId = string & { readonly __brand: "StageId" };

export type Modality = "mobile" | "desktop" | "sandbox" | "browser" | "vm" | "container";

export interface PointerInput {
  readonly kind: "tap" | "click" | "swipe";
  readonly x: number;
  readonly y: number;
  readonly x2?: number;
  readonly y2?: number;
  readonly durationMs?: number;
}

export interface KeyInput {
  readonly kind: "type" | "press";
  readonly text?: string;
  readonly key?: string;
}

export interface Viewport {
  readonly width: number;
  readonly height: number;
  readonly scale: number;
}

export interface ScreenshotResult {
  readonly path: string;
  readonly format: "png" | "jpg" | "jpeg";
  readonly width: number;
  readonly height: number;
  readonly capturedAt: string; // ISO 8601
}

export interface DeviceSession {
  readonly id: SessionId;
  readonly deviceId: DeviceId;
  readonly modality: Modality;
  readonly startedAt: string;
}

/**
 * DeviceStage is the abstract interface every modality adapter must
 * satisfy. This is the single trait the agent runtime uses; concrete
 * adapters (Eidolon, PlayCua, mobile-mcp) are injected by composition.
 */
export interface DeviceStage {
  readonly name: string;
  readonly modality: Modality;
  readonly supportedDeviceKinds: readonly string[];

  listDevices(): Promise<readonly DeviceId[]>;
  openSession(deviceId: DeviceId): Promise<DeviceSession>;
  closeSession(sessionId: SessionId): Promise<void>;

  pointer(sessionId: SessionId, input: PointerInput): Promise<void>;
  key(sessionId: SessionId, input: KeyInput): Promise<void>;
  screenshot(sessionId: SessionId, outputPath: string): Promise<ScreenshotResult>;
  viewport(sessionId: SessionId): Promise<Viewport>;

  /** Stage-port hook: route a domain-specific call through the implementation. */
  call<T = unknown>(method: string, params?: unknown): Promise<T>;
}