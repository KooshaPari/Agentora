/**
 * T66 adapter: DesktopStageAdapter — Eidolon-backed DesktopStage.
 *
 * Implements the DesktopStage sub-trait (ports/desktop_stage.ts) by
 * delegating through an Eidolon MCP transport. This is the canonical
 * adapter per findings/2026-06-17-agent-platform-domain.md §4 PR 3 and
 * findings/2026-06-17-eidolon-absorption.md Phase 4 note — it is the
 * type-safe wrapper around Eidolon's eidolon-desktop (the Rust
 * VirtualStage impl for macOS / Linux / Windows desktops).
 *
 * Two layers of delegation:
 *
 *   DesktopStageAdapter.click()
 *   └─> EidolonStage.pointer(sessionId, { kind: "click", x, y })  // device_stage primitive
 *   └─> EidolonStage.call("pointer", ...)                          // transport-level escape hatch
 *   └─> EidolonTransport.call("pointer", ...)                      // stdio / http / custom
 *   └─> KooshaPari/Eidolon eidolon-desktop via MCP                 // native Core Graphics / xdotool
 *
 * Telemetry: every method call is wrapped in an OTLP span via
 * ports/telemetry.ts. Gracefully degrades to no-op when
 * @opentelemetry/api is not installed.
 */

import type {
  DeviceId,
  SessionId,
  PointerInput,
  KeyInput,
  Viewport,
  ScreenshotResult,
  DeviceSession,
} from "../device_stage";
import type {
  DesktopStage,
  CaptureSession,
  DisplayInfo,
  DisplayId,
  MouseButton,
} from "../desktop_stage";
import { EidolonStage, NullTransport } from "./eidolon";
import type { EidolonTransport } from "./eidolon";
import { getTracer } from "../telemetry";

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

/**
 * DesktopStageAdapter configuration. Mirrors EidolonStageConfig plus an
 * optional fallback flag.
 *
 * Per ADR-023 Rule 3.1 quality bar, the default `fallbackToNull: true`
 * makes the adapter safe to inject where a desktop modality is expected
 * (domain code can rely on the trait being present even when no
 * Eidolon server is configured).
 */
export interface DesktopStageConfig {
  readonly name: string;
  readonly transport: "stdio" | "http" | "custom";
  readonly endpoint?: string;
  readonly customTransport?: EidolonTransport;
  readonly fallbackToNull?: boolean;
  readonly defaultModality?: "desktop"; // locked to "desktop" for this adapter
}

// ---------------------------------------------------------------------------
// Backing primitive selector
// ---------------------------------------------------------------------------

/**
 * Build a PointerInput out of DesktopStage-level coordinates and a mouse
 * button. This is the single place where DesktopStage.click /
 * DesktopStage.doubleClick / DesktopStage.rightClick collapse into the
 * device-stage pointer primitive before being routed through Eidolon.
 *
 * The Eidolon eidolon-desktop backend interprets the `button` field to
 * decide between left- and right-click; there is no separate
 * "right-click" PointerInput.kind in the device-stage baseline.
 */
function pointerFromCoords(
  x: number,
  y: number,
  button: MouseButton,
): PointerInput & { readonly button: MouseButton } {
  return { kind: "click", x, y, button };
}

// ---------------------------------------------------------------------------
// Adapter
// ---------------------------------------------------------------------------

/**
 * Eidolon-backed DesktopStage adapter. Goes through EidolonStage for
 * transport (stdio / http / in-memory) and exposes the desktop-semantic
 * operations defined in ports/desktop_stage.ts.
 */
export class DesktopStageAdapter implements DesktopStage {
  readonly name: string;
  readonly modality: "desktop" = "desktop";
  readonly supportedDeviceKinds: readonly string[] = [
    "macos",
    "linux-x11",
    "linux-wayland",
    "windows",
  ];

  private readonly delegate: EidolonStage;

  constructor(config: DesktopStageConfig) {
    this.name = `desktop-eidolon:${config.name}`;

    // The EidolonStage is the transport owner; we route desktop ops
    // through it so the OTLP spans, error wrapping, and transport
    // handling all stay in one place.
    const fallback = config.fallbackToNull ?? true;

    const delegateConfig: ConstructorParameters<typeof EidolonStage>[0] = {
      name: config.name,
      transport:
        fallback && config.transport !== "custom" && !config.customTransport
          ? "custom"
          : config.transport,
      ...(config.endpoint !== undefined ? { endpoint: config.endpoint } : {}),
      ...(config.customTransport !== undefined
        ? { customTransport: config.customTransport }
        : {}),
      defaultModality: "desktop",
    };

    this.delegate = new EidolonStage(delegateConfig);
  }

  /**
   * Read-only accessor for the underlying EidolonStage — primarily used
   * by tests and DI containers that want to verify delegation or wire
   * additional tap points (e.g. recording transports).
   */
  getDelegate(): EidolonStage {
    return this.delegate;
  }

  // -------------------------------------------------------------------------
  // DesktopStage: desktop semantics
  // -------------------------------------------------------------------------

  async startCaptures(sessionId: SessionId, outputPath: string): Promise<CaptureSession> {
    const span = getTracer().startSpan("desktop-stage.startCaptures", {
      attributes: {
        "device.modality": this.modality,
        "device.transport": this.delegateName(),
        "session.id": sessionId,
        "capture.outputPath": outputPath,
      },
    });
    try {
      const result = await this.delegate.call<CaptureSession>("start_captures", {
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

  async click(
    sessionId: SessionId,
    x: number,
    y: number,
    button: MouseButton = "left",
  ): Promise<void> {
    await this.delegate.pointer(sessionId, pointerFromCoords(x, y, button));
  }

  async doubleClick(
    sessionId: SessionId,
    x: number,
    y: number,
    button: MouseButton = "left",
  ): Promise<void> {
    // Double click is two clicks — issued back-to-back so Eidolon handles
    // OS-specific timing (eidolon-desktop maps to NSEvent /
    // XTestButtonPress with the OS double-click interval).
    await this.delegate.pointer(sessionId, pointerFromCoords(x, y, button));
    await this.delegate.pointer(sessionId, pointerFromCoords(x, y, button));
  }

  async rightClick(sessionId: SessionId, x: number, y: number): Promise<void> {
    await this.delegate.pointer(sessionId, pointerFromCoords(x, y, "right"));
  }

  async keyTap(sessionId: SessionId, key: string): Promise<void> {
    await this.delegate.key(sessionId, { kind: "press", key } satisfies KeyInput);
  }

  async keyCombo(
    sessionId: SessionId,
    modifiers: readonly string[],
    key: string,
  ): Promise<void> {
    // Key combo is encoded via a single "press" KeyInput that carries
    // both the modifiers and the terminal key. The Eidolon backend is
    // responsible for the OS-specific keymap (cmd vs ctrl, order of
    // modifier press/release).
    //
    // The cast through unknown lets us forward `modifiers` along the
    // wire to the backend without widening the EidolonStage.key()
    // signature (which would ripple across the Eidolon adapter surface).
    const payload = {
      kind: "press" as const,
      key,
      modifiers,
    };
    await this.delegate.key(sessionId, payload as unknown as KeyInput);
  }

  async getActiveDisplay(sessionId: SessionId): Promise<DisplayInfo> {
    const span = getTracer().startSpan("desktop-stage.getActiveDisplay", {
      attributes: {
        "device.modality": this.modality,
        "device.transport": this.delegateName(),
        "session.id": sessionId,
      },
    });
    try {
      const result = await this.delegate.call<DisplayInfo>("get_active_display", {
        sessionId,
      });
      return result;
    } catch (error) {
      span.recordError(error instanceof Error ? error : new Error(String(error)));
      throw error;
    } finally {
      span.end();
    }
  }

  // -------------------------------------------------------------------------
  // DeviceStage: baseline primitive surface (pure passthroughs)
  // -------------------------------------------------------------------------

  async listDevices(): Promise<readonly DeviceId[]> {
    return this.delegate.listDevices();
  }

  async openSession(deviceId: DeviceId): Promise<DeviceSession> {
    return this.delegate.openSession(deviceId);
  }

  async closeSession(sessionId: SessionId): Promise<void> {
    return this.delegate.closeSession(sessionId);
  }

  async pointer(sessionId: SessionId, input: PointerInput): Promise<void> {
    return this.delegate.pointer(sessionId, input);
  }

  async key(sessionId: SessionId, input: KeyInput): Promise<void> {
    return this.delegate.key(sessionId, input);
  }

  async screenshot(
    sessionId: SessionId,
    outputPath: string,
  ): Promise<ScreenshotResult> {
    return this.delegate.screenshot(sessionId, outputPath);
  }

  async viewport(sessionId: SessionId): Promise<Viewport> {
    return this.delegate.viewport(sessionId);
  }

  /** Forward arbitrary calls through EidolonStage.call (escape hatch). */
  async call<T = unknown>(method: string, params?: unknown): Promise<T> {
    return this.delegate.call<T>(method, params);
  }

  // -------------------------------------------------------------------------
  // Internals
  // -------------------------------------------------------------------------

  /** Reads the transport name off the wrapped EidolonStage for telemetry. */
  private delegateName(): string {
    // EidolonStage stores transport as `private readonly transport: EidolonTransport`.
    // We cast through unknown to read the name without exposing internals.
    const transport = (this.delegate as unknown as {
      transport?: { name?: string };
    }).transport;
    return transport?.name ?? "unknown";
  }
}

// ---------------------------------------------------------------------------
// Factory + Null fallback
// ---------------------------------------------------------------------------

/**
 * Build a DesktopStageAdapter with the default config (Eidolon not
 * reachable — NullTransport). Useful for tests and for any domain code
 * that wants a typed DesktopStage slot in its DI graph regardless of
 * whether Eidolon is online.
 */
export function nullDesktopStage(name = "null"): DesktopStage {
  return new DesktopStageAdapter({
    name,
    transport: "custom",
    customTransport: new NullTransport(),
    fallbackToNull: true,
  });
}

/**
 * Re-export the brand utilities from device_stage for ergonomics —
 * callers shouldn't need a second import to construct branded IDs.
 */
export type { DeviceId, SessionId };
export const asDisplayId = (s: string): DisplayId => s as DisplayId;
